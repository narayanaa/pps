from __future__ import annotations
import logging
from typing import List, Tuple, Dict, Any
import itertools
import pdfplumber  # type: ignore
import fitz  # type: ignore
from PIL import Image
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

class PageProcessingUtils:
    """Utility methods for page-level processing, including text extraction, layout analysis, and table/figure handling."""

    # ------------------------------------------------------------------
    # Column detection – improved for multi-column layouts
    # ------------------------------------------------------------------
    def detect_columns(self, page: pdfplumber.page.Page) -> int:
        """Detect the number of columns based on word gaps."""
        words = page.extract_words() or []
        if not words:
            return 1
        x_positions = sorted(w["x0"] for w in words)
        gaps = [b - a for a, b in itertools.pairwise(x_positions)]
        large_gaps = [g for g in gaps if g > 50]  # Threshold may need tuning
        return len(large_gaps) + 1

    # ------------------------------------------------------------------
    # Text extraction – exclude tables and figures
    # ------------------------------------------------------------------
    def extract_words(self, page: pdfplumber.page.Page, table_rects: List[Tuple], figure_rects: List[Tuple]) -> List[str]:
        """Extract words in reading order, excluding those within table and figure regions."""
        words = page.extract_words()
        filtered_words = [
            w["text"] for w in words
            if not any(self._point_in_rect((w["x0"], w["top"]), rect) for rect in table_rects + figure_rects)
        ]
        return filtered_words

    # ------------------------------------------------------------------
    # Block extraction – group text lines into paragraphs
    # ------------------------------------------------------------------
    def extract_blocks(self, page: pdfplumber.page.Page) -> List[Dict]:
        """Extract text blocks (e.g., paragraphs) from the page."""
        lines = page.extract_text_lines() or []
        blocks = []
        current_block = []
        for line in lines:
            if not current_block or self._is_same_block(current_block[-1], line):
                current_block.append(line)
            else:
                blocks.append(self._merge_block(current_block))
                current_block = [line]
        if current_block:
            blocks.append(self._merge_block(current_block))
        return blocks

    def _is_same_block(self, prev_line: Dict, current_line: Dict) -> bool:
        """Heuristic to determine if two lines belong to the same block (paragraph)."""
        vertical_gap = current_line["top"] - prev_line["bottom"]
        return vertical_gap < 5  # Adjust threshold as needed

    def _merge_block(self, lines: List[Dict]) -> Dict:
        """Merge multiple lines into a single block (paragraph)."""
        text = " ".join(line["text"] for line in lines)
        bbox = (min(l["x0"] for l in lines), min(l["top"] for l in lines),
                max(l["x1"] for l in lines), max(l["bottom"] for l in lines))
        return {"text": text, "bbox": bbox}

    # ------------------------------------------------------------------
    # Table detection and extraction
    # ------------------------------------------------------------------
    def detect_tables(self, page: pdfplumber.page.Page) -> List[Any]:
        """Detect tables on the page using pdfplumber's built-in method."""
        return page.extract_tables()

    def extract_table_data(self, table: Any) -> Dict[str, Any]:
        """Extract data from a detected table."""
        return {"rows": table}

    # ------------------------------------------------------------------
    # Figure detection and extraction
    # ------------------------------------------------------------------
    def detect_figures(self, page: fitz.Page) -> List[Tuple[float, float, float, float]]:
        """Detects figure bounding boxes robustly, skipping images without drawable areas."""
        figures = []
        for img in page.get_images(full=True):
            try:
                xref = img[0]
                rect = page.get_image_bbox(xref)
                if rect and rect.width > 0 and rect.height > 0:
                    figures.append((rect.x0, rect.y0, rect.x1, rect.y1))
            except Exception as e:
                logger.warning(f"Skipping figure xref={img[0]}: {e}")
        return figures

    def extract_figures(self, page: fitz.Page, rects: list) -> list[str]:
        """Extract figure images from the page as base64-encoded strings."""
        figures = []
        for rect in rects:
            try:
                if isinstance(rect, (tuple, list)) and len(rect) == 4:
                    rect = fitz.Rect(*rect)
                elif hasattr(rect, "x0"):
                    rect = fitz.Rect(rect)

                logger.info("Trying to extract figure at %s", rect)
                pix = page.get_pixmap(clip=rect)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                figures.append(img_str)
            except Exception as e:
                logger.error(f"Failed to extract figure: {str(e)}")
                figures.append(f"Error extracting figure: {str(e)}")
        return figures

    # ------------------------------------------------------------------
    # Scanned page detection
    # ------------------------------------------------------------------
    def is_scanned_page(self, page: fitz.Page) -> bool:
        """Check if the page is scanned by combining text and image coverage."""
        # Extract text, handle case where get_text might not exist
        txt = ""
        if hasattr(page, 'get_text'):
            txt = page.get_text("text").strip()
        else:
            logger.warning("Page object lacks get_text method; assuming no text.")

        # If significant text is present, it’s not scanned
        if len(txt) > 50:
            logger.info(f"Page has {len(txt)} characters; not scanned.")
            return False

        # Check for images
        images = page.get_images(full=True)
        if not images:
            logger.info("No images and minimal text; assuming scanned.")
            return True  # No text and no images: likely scanned or blank

        # Calculate image area, handle failures gracefully
        img_area = 0.0
        for img in images:
            try:
                xref = img[0]
                rect = page.get_image_bbox(xref)
                if rect and rect.width > 0 and rect.height > 0:
                    img_area += rect.width * rect.height
            except Exception as e:
                logger.warning(f"Failed to compute image area for xref={xref}: {e}")
                # If any image fails, assume the page might be scanned
                return True

        # Compare image area to page area
        page_area = page.rect.width * page.rect.height
        is_scanned = img_area > 0.3 * page_area or len(txt) < 50
        logger.info(f"Image area: {img_area}, Page area: {page_area}, Text length: {len(txt)}, Scanned: {is_scanned}")
        return is_scanned

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _point_in_rect(self, point: Tuple[float, float], rect: Tuple[float, float, float, float]) -> bool:
        """Check if a point is within a rectangle."""
        x, y = point
        x0, y0, x1, y1 = rect
        return x0 <= x <= x1 and y0 <= y <= y1