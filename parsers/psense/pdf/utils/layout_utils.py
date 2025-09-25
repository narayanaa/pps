"""Enhanced Page-Layout Analysis Utilities

This module provides comprehensive tools for PDF layout analysis, including multi-column detection,
handling of spanning elements (images/tables), reading order construction, and block classification.
Optimized for research papers with complex variants like asymmetric columns or full-width figures.

Key Enhancements:
- Density-based clustering for robust column detection.
- Spanning element detection and reading order rerouting.
- Block classification including formulas and headings.
- Configurable thresholds with confidence scoring.
"""

from __future__ import annotations
import math
from collections import Counter
import itertools
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field

import pdfplumber  # type: ignore
import re  # For formula patterns

logger = logging.getLogger(__name__)


@dataclass
class LayoutBlock:
    """Represents a block of content with layout information."""
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    text: str
    block_type: str  # text, figure, table, formula, heading, etc.
    confidence: float = 1.0
    font_info: Optional[Dict[str, Any]] = None
    reading_order: int = 0


@dataclass
class PageLayout:
    """Represents the layout structure of a PDF page."""
    page_number: int
    width: float
    height: float
    blocks: List[LayoutBlock] = field(default_factory=list)
    columns: List[Tuple[float, float]] = field(default_factory=list)  # (start, end) pairs
    headers: List[LayoutBlock] = field(default_factory=list)
    footers: List[LayoutBlock] = field(default_factory=list)
    spanning_blocks: List[LayoutBlock] = field(default_factory=list)  # Blocks crossing columns


class LayoutUtils:
    """Enhanced utility methods for page-layout analysis.

    Does not mutate objects in-place unless specified. Supports multi-column variants,
    spanning elements, and density-based detection for research PDFs.
    """

    def __init__(self, min_gap_threshold: float = 50.0, grid_size: int = 50,
                 expected_columns: int = 1, min_confidence: float = 0.7):
        self.min_gap_threshold = min_gap_threshold
        self.grid_size = grid_size
        self.expected_columns = expected_columns
        self.min_confidence = min_confidence

    # ------------------------------------------------------------------
    # Density Map Generation - Enhanced for projections
    # ------------------------------------------------------------------
    @staticmethod
    def get_density_map(page: pdfplumber.page.Page, grid_size: int = 50) -> List[List[int]]:
        """Generate a grid-based text density map with horizontal projections."""
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

    def get_horizontal_projection(self, density_map: List[List[int]]) -> List[int]:
        """Compute horizontal density projection for column valley detection."""
        return [sum(col) for col in zip(*density_map)]

    # ------------------------------------------------------------------
    # Column Detection - Density-based with manual DBSCAN approximation
    # ------------------------------------------------------------------
    def detect_columns(self, page: pdfplumber.page.Page, table_rects: List[Tuple[float, float, float, float]] = [],
                       figure_rects: List[Tuple[float, float, float, float]] = []) -> Tuple[List[Tuple[float, float]], float]:
        """Detects column boundaries using density clustering, excluding tables/figures.
        
        Returns boundaries and confidence score. Falls back to single-column if low confidence.
        
        Args:
            page: The page to analyze.
            table_rects: Table bounding boxes.
            figure_rects: Figure bounding boxes.
        
        Returns:
            Tuple[List[Tuple[float, float]], float]: Column (start, end) pairs and confidence (0-1).
        """
        lines = page.extract_text_lines() or []
        if not lines:
            return [(0, page.width)], 1.0

        # Filter lines outside tables/figures
        def is_within_rect(line: Dict, rects: List[Tuple]) -> bool:
            line_rect = (line["x0"], line["top"], line["x1"], line["bottom"])
            for r in rects:
                if line_rect[0] >= r[0] and line_rect[1] >= r[1] and line_rect[2] <= r[2] and line_rect[3] <= r[3]:
                    return True
            return False

        text_lines = [line for line in lines if not is_within_rect(line, table_rects + figure_rects)]
        if not text_lines:
            return [(0, page.width)], 1.0

        # Get x0 positions
        x_positions = sorted(line["x0"] for line in text_lines)

        # Manual DBSCAN-like clustering: Group points within eps (min_gap_threshold)
        eps = self.min_gap_threshold
        clusters = []
        current_cluster = [x_positions[0]]
        for x in x_positions[1:]:
            if x - current_cluster[-1] <= eps:
                current_cluster.append(x)
            else:
                clusters.append(current_cluster)
                current_cluster = [x]
        clusters.append(current_cluster)

        # Filter small clusters as noise (min_points heuristic: at least 5% of positions)
        min_points = len(x_positions) * 0.05
        valid_clusters = [c for c in clusters if len(c) >= min_points]

        if not valid_clusters:
            return [(0, page.width)], 0.5  # Low confidence fallback

        # Compute mid-boundaries between clusters
        boundaries = [0]
        for i in range(len(valid_clusters) - 1):
            boundary = (max(valid_clusters[i]) + min(valid_clusters[i + 1])) / 2
            boundaries.append(boundary)
        boundaries.append(page.width)

        columns = list(zip(boundaries[:-1], boundaries[1:]))

        # Confidence: Based on cluster consistency (variance) and match to expected_columns
        cluster_vars = [math.var(c) for c in valid_clusters if len(c) > 1]
        avg_var = sum(cluster_vars) / len(cluster_vars) if cluster_vars else 0
        num_cols = len(columns)
        confidence = (1 - avg_var / (page.width / num_cols)) * (1 - abs(num_cols - self.expected_columns) / max(num_cols, self.expected_columns))
        confidence = max(0, min(1, confidence))

        if confidence < self.min_confidence:
            logger.warning(f"Low confidence ({confidence:.2f}) in column detection; falling back to single-column.")
            return [(0, page.width)], confidence

        return columns, confidence

    # ------------------------------------------------------------------
    # Spanning Element Detection and Handling
    # ------------------------------------------------------------------
    def detect_spanning_blocks(self, blocks: List[LayoutBlock], columns: List[Tuple[float, float]]) -> List[LayoutBlock]:
        """Identifies blocks (e.g., images/tables) spanning multiple columns."""
        spanning = []
        for block in blocks:
            block_width = block.bbox[2] - block.bbox[0]
            col_span_count = sum(1 for col_start, col_end in columns if block.bbox[0] < col_end and block.bbox[2] > col_start)
            if col_span_count > 1 or block_width > (columns[0][1] - columns[0][0]) * 1.5:
                spanning.append(block)
        return spanning

    # ------------------------------------------------------------------
    # Reading Order - Enhanced for multi-columns and spanning elements
    # ------------------------------------------------------------------
    def build_reading_order(self, page: pdfplumber.page.Page, blocks: List[LayoutBlock],
                            columns: List[Tuple[float, float]], spanning_blocks: List[LayoutBlock]) -> List[LayoutBlock]:
        """Builds reading order, handling columns and rerouting around spanning blocks.
        
        Sorts vertically within columns, concatenates left-to-right, and treats spanning as full-width interruptions.
        """
        if not blocks:
            return []

        # Group blocks by column, excluding spanning
        column_blocks = [[] for _ in columns]
        non_spanning = [b for b in blocks if b not in spanning_blocks]

        for block in non_spanning:
            center_x = (block.bbox[0] + block.bbox[2]) / 2
            for i, (start, end) in enumerate(columns):
                if start <= center_x < end:
                    column_blocks[i].append(block)
                    break
            else:
                column_blocks[0].append(block)  # Fallback

        # Sort within columns by y0 (top-to-bottom)
        for col in column_blocks:
            col.sort(key=lambda b: b.bbox[1])

        # Interleave spanning blocks by their y-position
        all_blocks = column_blocks + [spanning_blocks]
        flat_blocks = []
        for col in column_blocks:
            flat_blocks.extend(col)
        flat_blocks.extend(spanning_blocks)
        flat_blocks.sort(key=lambda b: b.bbox[1])  # Global sort by vertical position

        # Assign order
        for order, block in enumerate(flat_blocks):
            block.reading_order = order

        return flat_blocks

    # ------------------------------------------------------------------
    # Block Extraction and Classification - Ported and enhanced
    # ------------------------------------------------------------------
    def extract_and_classify_blocks(self, page: pdfplumber.page.Page) -> List[LayoutBlock]:
        """Extracts and classifies blocks with font, heading, and formula detection."""
        text_dict = page.extract_text("dict") if hasattr(page, 'extract_text') else {}  # Assume PyMuPDF-like access if needed
        blocks = []

        for block_data in text_dict.get("blocks", []):
            if "lines" in block_data:
                block_text = ""
                font_info = {}
                for line in block_data["lines"]:
                    for span in line["spans"]:
                        block_text += span.get("text", "")
                        if not font_info:
                            font_info = {
                                'font': span.get('font', ''),
                                'size': span.get('size', 0),
                                'flags': span.get('flags', 0),
                                'color': span.get('color', 0)
                            }
                
                if block_text.strip():
                    bbox = tuple(block_data["bbox"])
                    block_type = self._classify_block(block_text, font_info, bbox, page)
                    layout_block = LayoutBlock(bbox=bbox, text=block_text.strip(), block_type=block_type, font_info=font_info)
                    blocks.append(layout_block)

        return blocks

    def _classify_block(self, text: str, font_info: Dict, bbox: Tuple, page) -> str:
        """Classifies block type with enhanced formula and heading logic."""
        page_height = page.height if hasattr(page, 'height') else bbox[3] * 2  # Fallback
        if self._contains_math_indicators(text):
            return "formula"
        if font_info.get('size', 0) > 14 and len(text) < 200:
            return "heading"
        if text.lower().startswith(('figure', 'table', 'fig.', 'tab.')):
            return "caption"
        if font_info.get('size', 0) < 10 and bbox[1] > page_height * 0.85:
            return "footnote"
        if bbox[1] < page_height * 0.1:
            return "header"
        if bbox[1] > page_height * 0.9:
            return "footer"
        if re.match(r'^\s*[\d\w]+[\.\)]\s', text) or text.startswith('•'):
            return "list_item"
        return "paragraph"

    @staticmethod
    def _contains_math_indicators(text: str) -> bool:
        """Enhanced check for mathematical notation."""
        patterns = [
            r'[∑∫∏√±×÷≠≤≥∞∂∇α-ωΑ-Ω]',  # Symbols
            r'\b\d+[\+\-\*/=]\d+\b',  # Equations
            r'\([^)]*[+\-*/=][^)]*\)',  # Parentheses
            r'[a-zA-Z]\s*=\s*[a-zA-Z0-9\+\-\*/\(\)]+',  # Assignments
            r'\b(?:sin|cos|tan|log|ln|exp|sqrt|sum|int)\s*\(',  # Functions
            r'\\begin\{equation\}',  # LaTeX
        ]
        return any(re.search(p, text) for p in patterns)

    # ------------------------------------------------------------------
    # Full Page Layout Analysis - New orchestrator method
    # ------------------------------------------------------------------
    def analyze_page_layout(self, page: pdfplumber.page.Page, table_rects: List = [], figure_rects: List = []) -> PageLayout:
        """Orchestrates full layout analysis for a page.
        
        Returns a PageLayout object with blocks, columns, headers, footers, and spanning info.
        """
        blocks = self.extract_and_classify_blocks(page)
        columns, confidence = self.detect_columns(page, table_rects, figure_rects)
        headers, footers = self.identify_headers_footers(blocks, page)
        spanning = self.detect_spanning_blocks(blocks, columns)
        ordered_blocks = self.build_reading_order(page, blocks, columns, spanning)

        return PageLayout(
            page_number=page.page_number if hasattr(page, 'page_number') else 1,
            width=page.width,
            height=page.height,
            blocks=ordered_blocks,
            columns=columns,
            headers=headers,
            footers=footers,
            spanning_blocks=spanning
        )

    # ------------------------------------------------------------------
    # Legacy Methods - Retained/Updated for compatibility
    # ------------------------------------------------------------------
    @classmethod
    def strip_headers_footers(cls, page: pdfplumber.page.Page, header_h: int = 50, footer_h: int = 50):
        """Crops page to remove headers/footers (mutates in-place)."""
        page.crop((0, header_h, page.width, page.height - footer_h))

    def identify_headers_footers(self, blocks: List[LayoutBlock], page) -> Tuple[List[LayoutBlock], List[LayoutBlock]]:
        """Identifies headers/footers from blocks."""
        page_height = page.height if hasattr(page, 'height') else 1000
        headers = [b for b in blocks if b.block_type == "header" or b.bbox[1] < page_height * 0.1]
        footers = [b for b in blocks if b.block_type == "footer" or b.bbox[1] > page_height * 0.9]
        return headers, footers

    @staticmethod
    def get_page_font_stats(page: pdfplumber.page.Page) -> Dict[str, Any]:
        """Calculate font size statistics."""
        font_sizes = [char['fontsize'] for char in page.chars if 'fontsize' in char]
        if not font_sizes:
            return {'most_common_size': None, 'avg_size': None}
        counter = Counter(font_sizes)
        return {'most_common_size': counter.most_common(1)[0][0], 'avg_size': sum(font_sizes) / len(font_sizes)}
