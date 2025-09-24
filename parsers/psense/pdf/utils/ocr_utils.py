from __future__ import annotations
import re
import unicodedata
from typing import Dict, Any, List
import logging
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
try:
    import pytesseract  # type: ignore
    HAS_TESS = True
except Exception:
    HAS_TESS = False

try:
    from paddleocr import PaddleOCR  # type: ignore
    HAS_PADDLE = True
except Exception:
    HAS_PADDLE = False
from multiprocessing import Process, Queue, Pool
from functools import partial
import fitz  # PyMuPDF
from parsers.psense.pdf.utils.text_correction_utils import TextCorrectionUtils

logger = logging.getLogger(__name__)

DEFAULT_PYTESS_CONFIG = (
    "--oem 1 --psm 4 -c preserve_interword_spaces=1 "
    "-c tessedit_char_blacklist="
)


class OCRUtils:
    """Unified OCR Processor with Tesseract and PaddleOCR Fallback, DPI Adaptation, Preprocessing, and Timeout."""

    def __init__(self, cfg: Dict[str, Any]):
        """
        Initialize OCR utilities with configuration.

        Args:
            cfg: Configuration dictionary with keys like 'language', 'dpi_list', 'preprocessing', 'timeout',
                 'conf_threshold', 'fallback_engine'.
        """
        self.cfg = cfg
        self.tess_lang = cfg.get("language", "eng")
        self.dpi_list = cfg.get("dpi_list", [72, 300, 600])
        self.pre_cfg = cfg.get("preprocessing", {})
        self.timeout = cfg.get("timeout", 60)
        self.conf_threshold = cfg.get("conf_threshold", 50.0)
        # PaddleOCR is not initialized here to avoid pickling issues; handled in static methods

    def run_ocr(self, page: fitz.Page) -> str:
        """
        Run OCR on a single page with multiple DPI attempts and timeout control.

        Args:
            page: A fitz.Page object to process.

        Returns:
            Extracted text string.
        """
        if not isinstance(page, fitz.Page):
            raise ValueError("The 'page' must be a valid fitz.Page object")

        for dpi in self.dpi_list:
            logger.info(f"Trying OCR at DPI {dpi}")
            queue = Queue()
            try:
                pix = page.get_pixmap(dpi=dpi, alpha=False)
                logger.info(
                    f"Pixmap created at DPI {dpi}: width={pix.width}, height={pix.height}, samples={len(pix.samples)}")
            except Exception as e:
                logger.error(f"Error extracting pixmap at DPI {dpi}: {e}")
                continue

            img_data = pix.samples
            width, height = pix.width, pix.height
            if not img_data or len(img_data) != width * height * 3:
                logger.error(f"Invalid image data at DPI {dpi}: length={len(img_data)}")
                continue

            ocr_func = partial(
                OCRUtils.run_ocr_static,
                img_data=img_data,
                width=width,
                height=height,
                lang=self.tess_lang,
                psm=self.cfg.get("psm", 3),
                preprocessing=self.pre_cfg,
                conf_threshold=self.conf_threshold,
                use_paddle=self.cfg.get("fallback_engine", "paddle") == "paddle",
                parser_config=self.cfg
            )

            p = Process(target=OCRUtils._ocr_worker, args=(ocr_func, queue))
            p.start()
            p.join(self.timeout)

            if p.is_alive():
                p.terminate()
                logger.warning(f"OCR timed out at DPI {dpi}")
                continue

            if not queue.empty():
                text = queue.get()
                if text and len(text.strip()) >= 50:  # Configurable threshold could be added
                    return text.strip()
                logger.info(f"OCR output too short at DPI {dpi}, trying next DPI...")
        return ""

    def run_ocr_on_pages(self, pages: List[fitz.Page], dpi: int = 300,
                         parser_config: Dict[str, Any] = None) -> List[str]:
        """
        Run OCR on multiple pages in parallel using multiprocessing.Pool.

        Args:
            pages: List of fitz.Page objects to process.
            dpi: DPI to use for all pages (default 300 for efficiency).

        Returns:
            List of extracted text strings.
        """
        if not all(isinstance(page, fitz.Page) for page in pages):
            raise ValueError("All items in 'pages' must be valid fitz.Page objects")

        # Prepare arguments for each page
        tasks = []
        for page in pages:
            try:
                pix = page.get_pixmap(dpi=dpi, alpha=False)
                img_data = pix.samples
                width, height = pix.width, pix.height
                if not img_data or len(img_data) != width * height * 3:
                    logger.error(f"Invalid image data for page at DPI {dpi}")
                    tasks.append(None)
                    continue
                tasks.append((img_data, width, height, self.tess_lang, self.cfg.get("psm", 4),
                              self.pre_cfg, self.conf_threshold, self.cfg.get("fallback_engine", "paddle") == "paddle",
                              parser_config))
            except Exception as e:
                logger.error(f"Error extracting pixmap at DPI {dpi}: {e}")
                tasks.append(None)

        # Process pages in parallel
        with Pool() as pool:
            results = pool.starmap(OCRUtils.run_ocr_static, [task for task in tasks if task is not None])

        # Fill in empty results for failed extractions
        final_results = []
        result_idx = 0
        for task in tasks:
            if task is None:
                final_results.append("")
            else:
                final_results.append(results[result_idx] if result_idx < len(results) else "")
                result_idx += 1
        return final_results

    @staticmethod
    def run_ocr_static(img_data: bytes, width: int, height: int, lang: str, psm: int, preprocessing: Dict[str, Any],
                       conf_threshold: float, use_paddle: bool, parser_config: Dict[str, Any] = None) -> str:
        """
        Static method to run OCR on image data, using Tesseract first, then PaddleOCR if needed.

        Args:
            img_data: Raw image bytes.
            width: Image width.
            height: Image height.
            lang: Language for OCR.
            psm: Tesseract PSM mode.
            preprocessing: Preprocessing options dictionary.
            conf_threshold: Confidence threshold for accepting Tesseract output.
            use_paddle: Whether to use PaddleOCR as fallback.

        Returns:
            Extracted text string.
        """
        try:
            # Step 1: Convert image bytes to Image object
            img = Image.frombytes("RGB", [width, height], img_data)
            img = OCRUtils._apply_preprocessing(img, preprocessing)

            # Step 2: OCR using Tesseract
            config = f"--oem 1 --psm {psm} -c preserve_interword_spaces=1"
            try:
                if not HAS_TESS:
                    raise RuntimeError("pytesseract not available")
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config=config, lang=lang)
                text_list = data.get("text", [])
                conf_list = data.get("conf", [])
            except Exception as e:
                logger.error(f"Tesseract failed with data OCR: {e}")
                data = text_list = conf_list = []

            # Step 3: Calculate average confidence from Tesseract output
            confs = []
            for c in conf_list:
                try:
                    val = float(str(c).replace('-', ''))
                    if val >= 0:
                        confs.append(val)
                except:
                    continue
            avg_conf = sum(confs) / len(confs) if confs else 0
            text = " ".join([t for t in text_list if isinstance(t, str)]).strip()

            logger.debug(f"Tesseract OCR avg_conf={avg_conf:.2f}, len(text)={len(text)}")
            # corrected_text = TextCorrectionUtils.clean_ocr_text(text, parser_config)

            # Step 4: Perform text correction after OCR
            if avg_conf >= conf_threshold and len(text) > 50:
                corrected_text = TextCorrectionUtils.correct_numbers(text)
                if corrected_text:
                    logger.debug(f"Corrected text: {corrected_text}")
                    # Ensure the 'text' is passed correctly
                    return TextCorrectionUtils.clean_ocr_text(corrected_text, parser_config)

            # Step 5: Fallback to image_to_string if Tesseract output is poor
            if not text and HAS_TESS:
                try:
                    text = pytesseract.image_to_string(img, config=config, lang=lang)
                    logger.info(f"Tesseract fallback used (image_to_string), length={len(text)}")
                except Exception as e:
                    logger.error(f"Tesseract image_to_string fallback failed: {e}")
                    text = ""

            # Step 6: Apply text correction if OCR result is good enough
            if len(text) > 50 and avg_conf >= (conf_threshold * 0.7):
                corrected_text = TextCorrectionUtils.correct_numbers(text)
                if corrected_text:
                    logger.debug(f"Corrected text: {corrected_text}")
                    return TextCorrectionUtils.clean_ocr_text(corrected_text, parser_config)

            # Step 7: Fallback: Use PaddleOCR if enabled
            if use_paddle and HAS_PADDLE:
                try:
                    paddle_engine = PaddleOCR(use_angle_cls=True, lang="en")  # lang config may vary
                    img_np = np.array(img)
                    result = paddle_engine.ocr(img_np, cls=True)
                    logger.debug(f"PaddleOCR result parsed: {result}")
                    if result and isinstance(result[0], list):
                        flattened_text = " ".join([det[1][0] for det in result[0]])
                        # Ensure the 'text' is passed correctly
                        return TextCorrectionUtils.clean_ocr_text(flattened_text, parser_config)
                except Exception as e:
                    logger.error(f"PaddleOCR fallback failed: {e}")

        except Exception as e:
            logger.exception(f"OCR static error: {e}")

        return ""  # Return empty string if all attempts fail

    @staticmethod
    def _apply_preprocessing(img: Image.Image, options: Dict[str, Any]) -> Image.Image:
        """Apply preprocessing steps to the image."""
        if options.get("grayscale", True):
            img = img.convert("L")
        if options.get("median_filter", True):
            img = img.filter(ImageFilter.MedianFilter(size=3))
        if "contrast_enhancement" in options:
            factor = options.get("contrast_enhancement", 2.0)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(factor)
        if options.get("adaptive_threshold", True):
            img_cv = np.array(img)
            if len(img_cv.shape) == 3:
                img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
            img_cv = cv2.adaptiveThreshold(img_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
            img = Image.fromarray(img_cv)
        if options.get("deskew", True):
            try:
                img_cv = np.array(img)
                if len(img_cv.shape) == 3:
                    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
                coords = np.column_stack(np.where(img_cv > 0))
                if coords.size > 0:
                    angle = cv2.minAreaRect(coords)[-1]
                    angle = -(90 + angle) if angle < -45 else -angle
                    h, w = img_cv.shape
                    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
                    img_cv = cv2.warpAffine(img_cv, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                    img = Image.fromarray(img_cv)
            except Exception as e:
                logger.warning(f"Deskewing failed: {e}")
        return img

    @staticmethod
    def _ocr_worker(ocr_func, queue):
        """Worker function to run OCR and put result in queue."""
        try:
            text = ocr_func()
            queue.put(text)
        except Exception as e:
            logger.error(f"OCR worker exception: {e}")
            queue.put("")

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Apply text cleaning methods, such as removing unwanted characters, extra spaces, etc.

        Args:
            text: The OCR-extracted text.

        Returns:
            Cleaned text.
        """
        # Example: Clean text by stripping extra spaces and normalizing whitespace
        cleaned_text = " ".join(text.split())  # Normalize spaces and remove extra spaces
        return cleaned_text


def flatten_structured_output(structured_output: dict) -> str:
    lines = []

    for page in structured_output.get("pages", []):
        if isinstance(page, dict):
            if "error" in page:
                continue
            if "text" in page:
                text = page["text"]
                if isinstance(text, str):
                    lines.append(text)
                elif isinstance(text, list):
                    for line in text:
                        if isinstance(line, str):
                            lines.append(line)
                        elif isinstance(line, dict):
                            lines.append(" ".join(str(v) for v in line.values()))
                elif isinstance(text, dict):
                    lines.append(" ".join(str(v) for v in text.values()))

    return "\n".join(lines).strip()
