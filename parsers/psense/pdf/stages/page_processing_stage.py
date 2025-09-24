from __future__ import annotations

import logging
from typing import Dict, Any
import pdfplumber
from PIL import Image
import io
from doc.psense.document.document import Document
from doc.psense.document.chapter import Chapter
from doc.psense.document.section import Section
from doc.psense.document.paragraph import Paragraph
from doc.psense.document.table import Table
from doc.psense.document.image import Image
from .parsing_stage import ParsingStage
from ..utils.page_processing_utils import PageProcessingUtils
from ..utils.text_cleaning_utils import TextCleaningUtils
from ..utils.text_correction_utils import TextCorrectionUtils

logger = logging.getLogger(__name__)


class PageProcessingStage(ParsingStage):
    def __init__(self, parser):
        self.parser = parser
        self.utils = PageProcessingUtils()
        self.text_corrector = TextCorrectionUtils(self.parser.config.get_setting("transformer_correction", {}))

    def should_process_page(self, plumber_page) -> bool:
        config = self.parser.config.get_setting("page_processing", {})
        pages_to_process = config.get("pages_to_process", "all")
        skip_pages = config.get("skip_pages", [])
        page_pattern = config.get("page_pattern", None)
        page_num = plumber_page.page_number
        if page_num in skip_pages:
            return False
        if pages_to_process == "all":
            if page_pattern == "even":
                return page_num % 2 == 0
            elif page_pattern == "odd":
                return page_num % 2 != 0
            return True
        elif isinstance(pages_to_process, list):
            return page_num in pages_to_process
        return False

    def process_page(self, plumber_page, fitz_page, ocr_text: str | None = None) -> Dict[str, Any]:
        page_dict: Dict[str, Any] = {}
        page_num = plumber_page.page_number
        try:
            tables = self.utils.detect_tables(plumber_page)
            table_rects = [t.bbox for t in tables]
            raw_figure_rects = self.utils.detect_figures(fitz_page)
            figure_rects = []
            extracted_images = []
            for rect in raw_figure_rects:
                try:
                    coords = tuple(rect[i] for i in range(4))
                    figure_rects.append(coords)
                    image_index = rect[-1]
                    image = self.extract_image_from_fitz_page(fitz_page, image_index)
                    if image:
                        extracted_images.append(image)
                except Exception as e:
                    logger.warning(f"Page {page_num} - Skipping invalid figure rect: {rect} – {e}")

            logger.info(
                f"Page {page_num} - Found {len(figure_rects)} figures, extracted {len(extracted_images)} images...")

            if ocr_text is not None:
                # Use precomputed OCR text for scanned pages
                raw_text = ocr_text
                page_dict["figures"] = extracted_images
            else:
                # Extract text for non-scanned pages
                words = self.utils.extract_words(plumber_page, table_rects, figure_rects)
                raw_text = " ".join(words)
                page_dict["figures"] = extracted_images

            corrected_text = self.text_corrector.clean(raw_text)
            page_dict["text"] = corrected_text
            logger.info(f"Page {page_num} - Extracted text: {page_dict['text'][:100]}...")

            page_dict["columns"] = self.utils.detect_columns(plumber_page)
            page_dict["blocks"] = self.utils.extract_blocks(plumber_page)
            page_dict["tables"] = [self.utils.extract_table_data(t) for t in tables]
        except Exception as e:
            logger.error(f"Page {page_num} - Error processing: {str(e)}")
            page_dict["error"] = str(e)
        return page_dict

    def process(self, doc: Document) -> Dict[str, Any]:
        pdf = self.parser.pdf_utils.load_pdf(doc.url)
        with pdfplumber.open(doc.url) as plumber:
            chapter = Chapter(title=doc.title, sections=[], number=1, author=doc.author)
            for i in range(pdf.page_count):
                fitz_page = pdf[i]
                plumber_page = plumber.pages[i]
                # Extract text (simplified for demo)
                text = plumber_page.extract_text() or ""
                para = Paragraph(text)
                section = Section(title=f"Page {i+1}", content=[para], level=1)
                # Extract tables (simplified)
                tables = self.parser.table_figure_utils.extract_tables(plumber_page)
                for t in tables:
                    table_obj = Table(data=t["data"], caption=t.get("caption", ""), headers=t.get("headers", []))
                    section.content.append(table_obj)
                # Extract images (simplified)
                images = self.parser.pdf_utils.extract_images(fitz_page)
                for img_path in images:
                    img_obj = Image(file_path=img_path)
                    section.content.append(img_obj)
                chapter.sections.append(section)
            doc.chapters.append(chapter)
        return {}

    @staticmethod
    def extract_image_from_fitz_page(fitz_page, image_index):
        try:
            xref = fitz_page.get_image_xref(image_index)
            image_data = fitz_page.extract_image(xref)
            if image_data is None:
                logger.warning(f"Failed to extract image for xref={xref}")
                return None
            image_bytes = image_data["image"]
            pil_image = Image.open(io.BytesIO(image_bytes))
            pil_image = pil_image.convert("RGB")
            return pil_image
        except Exception as e:
            logger.error(f"Error extracting image: {str(e)}")
            return None


def merge_continuing_paragraphs(result: Dict[str, Any]):
    pages = result["pages"]
    for i in range(len(pages) - 1):
        if pages[i]["text"] and pages[i + 1]["text"]:
            if not pages[i]["text"].strip().endswith("."):
                pages[i]["text"] += " " + pages[i + 1]["text"]
                pages[i + 1]["text"] = ""


def merge_multi_page_lists(result: Dict[str, Any]):
    pages = result["pages"]
    for i in range(len(pages) - 1):
        current_blocks = pages[i]["blocks"]
        next_blocks = pages[i + 1]["blocks"]
        if current_blocks and next_blocks:
            last_block = current_blocks[-1]["text"]
            first_block = next_blocks[0]["text"]
            if last_block.strip().endswith("-") and first_block.strip().startswith("-"):
                current_blocks[-1]["text"] += " " + first_block
                next_blocks.pop(0)


def merge_multi_page_tables(result: Dict[str, Any]):
    pages = result["pages"]
    i = 0
    while i < len(pages) - 1:
        current_tables = pages[i]["tables"]
        next_tables = pages[i + 1]["tables"]
        if current_tables and next_tables:
            last_table = current_tables[-1]
            first_table = next_tables[0]
            if len(last_table["rows"][0]) == len(first_table["rows"][0]):
                current_tables[-1]["rows"].extend(first_table["rows"])
                next_tables.pop(0)
        i += 1
