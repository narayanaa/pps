"""Page‑layout analysis (columns, headers, reading order…)."""
from __future__ import annotations
import math
from collections import Counter
import itertools
import logging
from typing import Dict, List, Tuple, Any

import pdfplumber  # type: ignore

logger = logging.getLogger(__name__)


class LayoutUtils:
    """Utility methods for page-layout analysis that do not mutate the page object in-place.

    Provides tools for column detection, reading order construction, and block extraction,
    with enhancements for handling multi-column layouts, tables, and figures.
    """

    # ------------------------------------------------------------------
    # Column detection - retained for classification compatibility
    # ------------------------------------------------------------------
    def detect_columns(self, page: pdfplumber.page.Page) -> int:
        """Detects the number of columns based on word gaps. Used in classification.

        Args:
            page (pdfplumber.page.Page): The page to analyze.

        Returns:
            int: Number of columns (minimum 1).
        """
        words = page.extract_words() or []
        if not words:
            return 1
        x_positions = sorted(w["x0"] for w in words)
        gaps = [b - a for a, b in itertools.pairwise(x_positions)]
        large_gaps = [g for g in gaps if g > 50]  # Threshold may need tuning
        return len(large_gaps) + 1

    # ------------------------------------------------------------------
    # Column boundaries - new method for multi-column handling
    # ------------------------------------------------------------------
    @classmethod
    def get_column_boundaries(cls, page: pdfplumber.page.Page, table_rects: List[Tuple[float, float, float, float]],
                              figure_rects: List[Tuple[float, float, float, float]]) -> List[float]:
        """Calculates x-boundaries of columns, excluding text within tables and figures.

        Args:
            page (pdfplumber.page.Page): The page to analyze.
            table_rects (List[Tuple[float, float, float, float]]): Bounding boxes of tables (x0, top, x1, bottom).
            figure_rects (List[Tuple[float, float, float, float]]): Bounding boxes of figures.

        Returns:
            List[float]: List of x-coordinates defining column boundaries (e.g., [0, 205, page.width]).
        """
        lines = page.extract_text_lines() or []
        if not lines:
            return [0, page.width]

        # Helper to check if a line is fully within any rectangle
        def is_within_rect(line: Dict, rects: List[Tuple[float, float, float, float]]) -> bool:
            line_rect = (line["x0"], line["top"], line["x1"], line["bottom"])
            for r in rects:
                if (line_rect[0] >= r[0] and line_rect[1] >= r[1] and
                        line_rect[2] <= r[2] and line_rect[3] <= r[3]):
                    return True
            return False

        # Filter out lines within table or figure areas
        text_lines = [line for line in lines if not is_within_rect(line, table_rects + figure_rects)]
        if not text_lines:
            return [0, page.width]

        # Sort lines by left edge and find large gaps
        x_positions = sorted(line["x0"] for line in text_lines)
        gaps = [b - a for a, b in itertools.pairwise(x_positions)]
        large_gap_indices = [i for i, g in enumerate(gaps) if g > 50]  # Adjustable threshold

        # Define boundaries at midpoints of large gaps
        boundaries = [0]
        for idx in large_gap_indices:
            boundary = (x_positions[idx] + x_positions[idx + 1]) / 2
            boundaries.append(boundary)
        boundaries.append(page.width)
        return boundaries

    # ------------------------------------------------------------------
    # Reading order - enhanced for multi-column layouts
    # ------------------------------------------------------------------
    @classmethod
    def build_reading_order(cls, page: pdfplumber.page.Page, table_rects: List[Tuple[float, float, float, float]] = [],
                            figure_rects: List[Tuple[float, float, float, float]] = []) -> List[Dict]:
        """Builds a list of words in correct reading order for multi-column layouts.

        Assigns words to columns based on boundaries, sorts vertically within columns,
        and concatenates left-to-right.

        Args:
            page (pdfplumber.page.Page): The page to process.
            table_rects (List[Tuple[float, float, float, float]]): Table bounding boxes.
            figure_rects (List[Tuple[float, float, float, float]]): Figure bounding boxes.

        Returns:
            List[Dict]: List of word dictionaries in reading order.
        """
        # Get column boundaries excluding tables and figures
        boundaries = cls.get_column_boundaries(page, table_rects, figure_rects)

        # Extract all words
        words = page.extract_words() or []
        if not words:
            return []

        # Assign words to columns based on their x0 position
        column_words = [[] for _ in range(len(boundaries) - 1)]
        for word in words:
            x0 = word["x0"]
            for i in range(len(boundaries) - 1):
                if boundaries[i] <= x0 < boundaries[i + 1]:
                    column_words[i].append(word)
                    break

        # Sort words within each column by top position, then x0
        for col in column_words:
            col.sort(key=lambda w: (w["top"], w["x0"]))

        # Concatenate columns left-to-right
        reading_order = []
        for col in column_words:
            reading_order.extend(col)

        return reading_order

    # ------------------------------------------------------------------
    # Headers / footers stripping - unchanged, simple cropping
    # ------------------------------------------------------------------
    @classmethod
    def strip_headers_footers(cls, page: pdfplumber.page.Page, header_h: int = 50, footer_h: int = 50):
        """Crops the page to remove headers and footers (mutates in-place).

        Args:
            page (pdfplumber.page.Page): The page to crop.
            header_h (int): Height of header to remove.
            footer_h (int): Height of footer to remove.
        """
        page.crop((0, header_h, page.width, page.height - footer_h))

    # ------------------------------------------------------------------
    # Header/footer detection - unchanged, works across first 3 pages
    # ------------------------------------------------------------------
    def identify_headers_footers(self, doc: pdfplumber.PDF) -> Dict[str, str]:
        """Identifies repeated header/footer text across the first few pages.

        Args:
            doc (pdfplumber.PDF): The document to analyze.

        Returns:
            Dict[str, str]: Dictionary with 'header' and 'footer' keys.
        """
        headers, footers = {}, {}
        for p in doc.pages[:min(3, len(doc.pages))]:
            top = (p.crop((0, 0, p.width, 50)).extract_text() or "").strip()
            bot = (p.crop((0, p.height - 50, p.width, p.height)).extract_text() or "").strip()
            headers[top] = headers.get(top, 0) + 1
            footers[bot] = footers.get(bot, 0) + 1
        return {
            "header": max(headers, key=headers.get, default=""),
            "footer": max(footers, key=footers.get, default=""),
        }

    @staticmethod
    def get_page_font_stats(page: pdfplumber.page.Page) -> Dict[str, Any]:
        """Calculate font size statistics for the page."""
        font_sizes = [char['fontsize'] for char in page.chars if 'fontsize' in char]
        if not font_sizes:
            return {'most_common_size': None, 'avg_size': None}
        counter = Counter(font_sizes)
        most_common_size = counter.most_common(1)[0][0]
        avg_size = sum(font_sizes) / len(font_sizes)
        return {'most_common_size': most_common_size, 'avg_size': avg_size}

    # ------------------------------------------------------------------
    # Block extraction - basic implementation, could be enhanced
    # ------------------------------------------------------------------
    def extract_blocks(self, page: pdfplumber.page.Page) -> List[Dict]:
        """Extract text blocks with font size and heading information."""
        lines = page.extract_text_lines() or []
        page_stats = self.get_page_font_stats(page)
        page_most_common_size = page_stats['most_common_size']
        if page_most_common_size is None:
            return lines

        for line in lines:
            if 'chars' not in line:
                continue
            font_sizes = [char['fontsize'] for char in line['chars'] if 'fontsize' in char]
            if font_sizes:
                counter = Counter(font_sizes)
                line_most_common_size = counter.most_common(1)[0][0]
                word_count = len(line['text'].split())
                # Flag as potential heading if font size is 10% larger and line is short
                is_potential_heading = (
                        line_most_common_size > page_most_common_size * 1.1 and
                        word_count < 10
                )
                line['most_common_font_size'] = line_most_common_size
                line['word_count'] = word_count
                line['is_potential_heading'] = is_potential_heading
            else:
                line['most_common_font_size'] = None
                line['word_count'] = 0
                line['is_potential_heading'] = False
        return lines

    @staticmethod
    def get_density_map(page: pdfplumber.page.Page, grid_size: int = 50) -> List[List[int]]:
        """Generate a grid-based text density map."""
        W, H = page.width, page.height
        cols = math.ceil(W / grid_size)
        rows = math.ceil(H / grid_size)
        density_map = [[0 for _ in range(cols)] for _ in range(rows)]

        for char in page.chars:
            x = char['x0']
            y = char['top']
            col = int(x // grid_size)
            row = int(y // grid_size)
            if 0 <= row < rows and 0 <= col < cols:
                density_map[row][col] += 1
        return density_map
