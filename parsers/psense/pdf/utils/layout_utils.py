"""Enhanced Page-Layout Analysis Utilities

This module provides comprehensive tools for PDF layout analysis, including multi-column detection,
handling of spanning elements (images/tables), reading order construction, and block classification.
Optimized for research papers with complex variants like asymmetric columns or full-width figures.

complete, adaptive solution for PDF layout parsing, particularly suited for research documents 
with complex structures. By incorporating statistical adaptations and resilient fallbacks, 
it minimizes errors while maintaining efficiency.

Key Enhancements:
- Density-based clustering for robust column detection.
- Spanning element detection and reading order rerouting.
- Block classification including formulas and headings.
- Configurable thresholds with confidence scoring.
"""

from __future__ import annotations
import math
import re
import logging
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional

import pdfplumber  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class LayoutBlock:
    """Represents a block of content with layout information."""
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    text: str
    block_type: str  # paragraph, heading, caption, figure, table, formula, list_item, header, footer, footnote
    confidence: float = 1.0
    font_info: Optional[Dict[str, Any]] = None
    reading_order: int = 0
    column: Optional[int] = None  # assigned column index (None if not assigned)


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
    column_confidence: float = 1.0


class LayoutUtils:
    """Enhanced utility methods for page-layout analysis.

    - Adaptive per-page column detection with density variance in confidence
    - Figure-caption grouping including side captions with adaptive gaps
    - Display-equation detection via centering + math density
    - Robust extraction with fallbacks and edge-case handling
    - Relative classification using page font stats
    """

    def __init__(self, min_gap_threshold: float = 50.0, grid_size: int = 50,
                 expected_columns: int = 2, min_confidence: float = 0.65,
                 line_gap_multiplier: float = 1.6, horizontal_overlap_threshold: float = 0.3):
        self.min_gap_threshold = float(min_gap_threshold)
        self.grid_size = int(grid_size)
        self.expected_columns = max(1, int(expected_columns))
        self.min_confidence = float(min_confidence)
        self.line_gap_multiplier = float(line_gap_multiplier)
        self.horizontal_overlap_threshold = float(horizontal_overlap_threshold)  # New for side captions

    # ------------------------ Density map & projection -------------------------
    @staticmethod
    def get_density_map(page: pdfplumber.page.Page, grid_size: int = 50) -> List[List[int]]:
        """Bucket characters into a grid and return counts per cell. Skips if no chars."""
        W = getattr(page, "width", 0) or 0
        H = getattr(page, "height", 0) or 0
        if W <= 0 or H <= 0:
            return [[0]]
        cols = max(1, math.ceil(W / grid_size))
        rows = max(1, math.ceil(H / grid_size))
        density_map = [[0 for _ in range(cols)] for _ in range(rows)]

        chars = getattr(page, "chars", []) or []
        for ch in chars:
            x = ch.get("x0", ch.get("x", None))
            y = ch.get("top", ch.get("y0", None))
            if x is None or y is None or not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                continue
            col = int(x // grid_size)
            row = int(y // grid_size)
            if 0 <= row < rows and 0 <= col < cols:
                density_map[row][col] += 1
        return density_map

    def get_horizontal_projection(self, density_map: List[List[int]]) -> List[int]:
        """Project density_map horizontally (sum across rows) -> one value per x-bin."""
        if not density_map:
            return []
        return [sum(col) for col in zip(*density_map)]

    # ------------------------ Word/line/block extraction -----------------------
    def _extract_words(self, page: pdfplumber.page.Page) -> List[Dict[str, Any]]:
        """Return a robust list of words with coordinates. Fallback to chars grouping, filter non-text."""
        # Try pdfplumber's extract_words
        try:
            words = page.extract_words()
            if words:
                return words
        except Exception:
            words = []

        # Fallback: synthesize words from page.chars, filter control chars
        chars = [ch for ch in getattr(page, "chars", []) or [] if ch.get("text", "").strip() and not re.match(r'[\x00-\x1F\x7F-\x9F]', ch.get("text", ""))]  # Filter non-printable
        if not chars:
            return []

        # sort by top then x0
        chars_sorted = sorted(chars, key=lambda c: (c.get("top", 0), c.get("x0", 0)))
        # group by similar top (line tolerance)
        lines: List[List[Dict[str, Any]]] = []
        tol = 3.0
        for ch in chars_sorted:
            top = ch.get("top", 0)
            if not lines or abs(lines[-1][0].get("top", 0) - top) > tol:
                lines.append([ch])
            else:
                lines[-1].append(ch)

        synthesized_words: List[Dict[str, Any]] = []
        for line in lines:
            line = sorted(line, key=lambda c: c.get("x0", 0))
            current = [line[0]]
            for a, b in zip(line, line[1:]):
                gap = b.get("x0", 0) - a.get("x1", a.get("x0", 0))
                if gap > 3:  # heuristic
                    text = "".join([c.get("text", "") for c in current]).strip()
                    if text:
                        x0 = min(c.get("x0", 0) for c in current)
                        x1 = max(c.get("x1", 0) for c in current)
                        top = min(c.get("top", 0) for c in current)
                        bottom = max(c.get("bottom", 0) for c in current)
                        synthesized_words.append({"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom})
                    current = [b]
                else:
                    current.append(b)
            if current:
                text = "".join([c.get("text", "") for c in current]).strip()
                if text:
                    x0 = min(c.get("x0", 0) for c in current)
                    x1 = max(c.get("x1", 0) for c in current)
                    top = min(c.get("top", 0) for c in current)
                    bottom = max(c.get("bottom", 0) for c in current)
                    synthesized_words.append({"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom})
        return synthesized_words

    def _words_to_lines(self, words: List[Dict[str, Any]], y_tol: float = 3.0) -> List[Dict[str, Any]]:
        """Group words into lines using a tolerance on the top coordinate."""
        if not words:
            return []
        words_sorted = sorted(words, key=lambda w: (w.get("top", 0), w.get("x0", 0)))
        lines: List[Dict[str, Any]] = []
        current = {"text": "", "x0": float("inf"), "x1": 0, "top": 0, "bottom": 0, "words": []}
        for w in words_sorted:
            top = w.get("top", 0)
            if not current["words"]:
                current = {"text": w.get("text", ""), "x0": w.get("x0", 0), "x1": w.get("x1", 0),
                           "top": top, "bottom": w.get("bottom", 0), "words": [w]}
                continue
            if abs(top - current["top"]) <= y_tol:
                # same line
                current["text"] = (current["text"] + " " + w.get("text", "")).strip()
                current["x0"] = min(current["x0"], w.get("x0", 0))
                current["x1"] = max(current["x1"], w.get("x1", 0))
                current["bottom"] = max(current["bottom"], w.get("bottom", 0))
                current["words"].append(w)
            else:
                lines.append(current)
                current = {"text": w.get("text", ""), "x0": w.get("x0", 0), "x1": w.get("x1", 0),
                           "top": top, "bottom": w.get("bottom", 0), "words": [w]}
        if current["words"]:
            lines.append(current)
        return lines

    def _lines_to_blocks(self, lines: List[Dict[str, Any]], page_font_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Group lines into blocks using vertical gap heuristics, adaptive to page stats."""
        if not lines:
            return []
        heights = [ln["bottom"] - ln["top"] for ln in lines if ln["bottom"] > ln["top"]]
        median_h = statistics.median(heights) if heights else page_font_stats.get("median_size", 12) or 12
        max_gap = median_h * self.line_gap_multiplier

        blocks: List[Dict[str, Any]] = []
        current: Dict[str, Any] = {}
        for ln in lines:
            if not current:
                current = {"text": ln["text"].strip(), "x0": ln["x0"], "x1": ln["x1"],
                           "top": ln["top"], "bottom": ln["bottom"], "lines": [ln]}
                continue
            gap = ln["top"] - current["bottom"]
            if gap > max_gap:
                blocks.append(current)
                current = {"text": ln["text"].strip(), "x0": ln["x0"], "x1": ln["x1"],
                           "top": ln["top"], "bottom": ln["bottom"], "lines": [ln]}
            else:
                current["text"] += "\n" + ln["text"].strip()
                current["x0"] = min(current["x0"], ln["x0"])
                current["x1"] = max(current["x1"], ln["x1"])
                current["bottom"] = max(current["bottom"], ln["bottom"])
                current["lines"].append(ln)
        if current:
            blocks.append(current)
        return blocks

    # ------------------------- Column detection --------------------------------
    def detect_columns(self, page: pdfplumber.page.Page, table_rects: List[Tuple[float, float, float, float]] = [],
                       figure_rects: List[Tuple[float, float, float, float]] = []) -> Tuple[List[Tuple[float, float]], float]:
        """
        Detect column boundaries using deterministic gap-clustering and a projection fallback.
        Confidence now includes density variance for better assessment.
        """
        words = self._extract_words(page)
        lines = self._words_to_lines(words)
        if not lines:
            page_width = getattr(page, "width", 1.0)
            return [(0.0, page_width)], 1.0

        # Filter lines within table/figure rects
        def inside_rect(line_rect: Tuple[float, float, float, float], rects: List[Tuple[float, float, float, float]]):
            lx0, lt, lx1, lb = line_rect
            for rx0, rt, rx1, rb in rects:
                if lx0 >= rx0 and lt >= rt and lx1 <= rx1 and lb <= rb:
                    return True
            return False

        filtered = [ln for ln in lines if not inside_rect((ln["x0"], ln["top"], ln["x1"], ln["bottom"]), table_rects + figure_rects)]
        if not filtered:
            page_width = getattr(page, "width", 1.0)
            return [(0.0, page_width)], 1.0

        x_positions = sorted(ln["x0"] for ln in filtered if ln["x0"] > 0)  # Avoid zero or negative
        if not x_positions:
            page_width = getattr(page, "width", 1.0)
            return [(0.0, page_width)], 1.0

        # diffs between consecutive x0s
        diffs = [j - i for i, j in zip(x_positions[:-1], x_positions[1:]) if j - i > 0]  # Positive diffs only
        eps = max(self.min_gap_threshold, (statistics.median(diffs) * 2) if diffs else self.min_gap_threshold)

        clusters: List[List[float]] = []
        current = [x_positions[0]]
        for prev, x in zip(x_positions[:-1], x_positions[1:]):
            if x - prev <= eps:
                current.append(x)
            else:
                clusters.append(current)
                current = [x]
        clusters.append(current)

        # noise filtering
        min_points = max(1, int(len(x_positions) * 0.03))
        valid_clusters = [c for c in clusters if len(c) >= min_points]

        page_width = max(getattr(page, "width", max(x_positions) * 1.5 or 1.0), max(x_positions) * 1.5)  # Handle zero-width

        if len(valid_clusters) <= 1:
            # fallback to density projection (detect valleys)
            density_map = self.get_density_map(page, grid_size=self.grid_size)
            proj = self.get_horizontal_projection(density_map)
            if not proj:
                return [(0.0, page_width)], 0.5
            # find valleys (low bins)
            med = statistics.median([p for p in proj if p >= 0]) if any(p >= 0 for p in proj) else 0
            if med <= 0:
                return [(0.0, page_width)], 0.5
            valley_bins = [i for i, v in enumerate(proj) if v <= med * 0.2]
            if not valley_bins:
                return [(0.0, page_width)], 0.5
            # convert bins to cuts
            bin_w = page_width / max(1, len(proj))  # Avoid div zero
            cuts = sorted(set([0.0] + [float(b * bin_w) for b in valley_bins] + [page_width]))
            columns = list(zip(cuts[:-1], cuts[1:]))
            # compress adjacent tiny columns
            conf = 0.5
            if conf < self.min_confidence:
                logger.debug("Low column confidence on projection fallback: %.2f", conf)
            return columns, conf

        # derive boundaries from clusters
        cluster_bounds = [(min(c), max(c)) for c in valid_clusters]
        boundaries = [0.0]
        for i in range(len(cluster_bounds) - 1):
            boundary = (cluster_bounds[i][1] + cluster_bounds[i + 1][0]) / 2.0
            boundaries.append(boundary)
        boundaries.append(page_width)
        columns = list(zip(boundaries[:-1], boundaries[1:]))

        # confidence: intra-cluster variance + closeness to expected_columns + density variance
        cluster_vars = [statistics.pvariance(c) for c in valid_clusters if len(c) > 1]
        avg_var = float(statistics.mean(cluster_vars)) if cluster_vars else 0.0
        cluster_widths = [max(c) - min(c) for c in valid_clusters]
        avg_cw = float(statistics.mean(cluster_widths)) if cluster_widths else (page_width / max(1, len(columns)))
        density_map = self.get_density_map(page, self.grid_size)
        proj = self.get_horizontal_projection(density_map)
        proj_var = statistics.pvariance(proj) if proj and len(proj) > 1 else 0.0
        density_score = 1.0 - min(1.0, proj_var / (page_width / len(columns)))

        var_score = 1.0 - min(1.0, avg_var / max(1.0, avg_cw))
        if self.expected_columns > 0:
            col_score = 1.0 - (abs(len(columns) - self.expected_columns) / max(len(columns), self.expected_columns))
        else:
            col_score = 1.0
        confidence = max(0.0, min(1.0, 0.5 * var_score + 0.3 * col_score + 0.2 * density_score))

        if confidence < self.min_confidence:
            logger.warning("Low confidence (%.2f) in column detection; returning single column", confidence)
            return [(0.0, page_width)], confidence

        return columns, confidence

    # ----------------------- Spanning & caption grouping -----------------------
    def detect_spanning_blocks(self, blocks: List[LayoutBlock], columns: List[Tuple[float, float]], page_block_stats: Dict) -> List[LayoutBlock]:
        """
        Identify blocks spanning multiple columns or large full-width items.
        Groups figure/table blocks with nearby captions (below/above or side), with adaptive gaps.
        """
        if not columns:
            return []

        # average column width (approx)
        col_widths = [c[1] - c[0] for c in columns]
        avg_col_width = max(1.0, sum(col_widths) / len(col_widths))

        # median block height for adaptive gap
        block_heights = [b.bbox[3] - b.bbox[1] for b in blocks if b.bbox[3] > b.bbox[1]]
        median_height = statistics.median(block_heights) if block_heights else 50.0
        max_vertical_gap = median_height * 2.5  # Adaptive vertical gap

        # find captions first
        caption_indices = set()
        caption_pattern = re.compile(r'^\s*(figure|fig\.|table|tab\.)\s*\d+', re.IGNORECASE)
        for i, b in enumerate(blocks):
            txt = (b.text or "").strip()
            if caption_pattern.match(txt) or b.block_type == "caption":
                caption_indices.add(i)

        used = set()
        spanning: List[LayoutBlock] = []

        for i, b in enumerate(blocks):
            if i in used:
                continue
            b_w = b.bbox[2] - b.bbox[0]
            col_span_count = sum(1 for s, e in columns if (b.bbox[0] < e and b.bbox[2] > s))
            is_spanning = (col_span_count > 1) or (b_w > (avg_col_width * 1.4))

            txt = (b.text or "").strip()
            if i in caption_indices:
                # search for nearest non-caption block vertically or horizontally close
                candidates = []
                for j, other in enumerate(blocks):
                    if j == i or j in used or other.block_type == "caption":
                        continue
                    v_gap = abs(b.bbox[1] - other.bbox[3]) if other.bbox[3] <= b.bbox[1] else abs(other.bbox[1] - b.bbox[3])
                    h_overlap = max(0, min(b.bbox[2], other.bbox[2]) - max(b.bbox[0], other.bbox[0])) / min(b_w, other.bbox[2] - other.bbox[0])
                    if (v_gap < max_vertical_gap and h_overlap > 0.1) or (h_overlap > self.horizontal_overlap_threshold and v_gap < median_height * 1.5):
                        score = v_gap + (1 - h_overlap) * median_height  # Lower score better
                        candidates.append((score, j, other))
                if candidates:
                    candidates.sort(key=lambda x: x[0])
                    _, jidx, other = candidates[0]
                    # merge if other is spanning or wide, or high overlap
                    other_w = other.bbox[2] - other.bbox[0]
                    other_span = col_span_count > 1 or other_w > avg_col_width * 1.4
                    if other_span or is_spanning or h_overlap > self.horizontal_overlap_threshold:
                        merged_bbox = (min(other.bbox[0], b.bbox[0]), min(other.bbox[1], b.bbox[1]),
                                       max(other.bbox[2], b.bbox[2]), max(other.bbox[3], b.bbox[3]))
                        merged_text = (other.text or "").strip() + "\n" + txt
                        merged_type = "figure" if "figure" in txt.lower() or "fig." in txt.lower() else "table"
                        merged_conf = min(b.confidence, other.confidence) * 0.9  # Slight penalty for merge
                        merged_block = LayoutBlock(bbox=merged_bbox, text=merged_text, block_type=merged_type, confidence=merged_conf, font_info=None)
                        spanning.append(merged_block)
                        used.add(i)
                        used.add(jidx)
                        continue

            if is_spanning:
                b.confidence *= 0.95  # Slight confidence adjustment for spanning
                spanning.append(b)
                used.add(i)

        # ensure unique (preserve order by y)
        spanning_sorted = sorted({id(b): b for b in spanning}.values(), key=lambda b: b.bbox[1])
        return spanning_sorted

    # ------------------------- Reading order construction ---------------------
    def build_reading_order(self, page: pdfplumber.page.Page, blocks: List[LayoutBlock],
                            columns: List[Tuple[float, float]], spanning_blocks: List[LayoutBlock]) -> List[LayoutBlock]:
        """
        Assign blocks to columns (by max bbox overlap) and interleave spanning blocks at appropriate y-positions.
        Tie-break same-y by x0.
        """
        if not blocks:
            return []

        columns_sorted = sorted(columns, key=lambda c: c[0]) if columns else [(0.0, getattr(page, "width", 1.0))]
        col_centers = [((s + e) / 2.0) for s, e in columns_sorted]
        col_blocks: List[List[LayoutBlock]] = [[] for _ in columns_sorted]
        non_spanning = [b for b in blocks if b not in spanning_blocks]

        # assign non-spanning to columns by max bbox overlap
        for b in non_spanning:
            overlaps = []
            for idx, (s, e) in enumerate(columns_sorted):
                overlap = max(0, min(b.bbox[2], e) - max(b.bbox[0], s))
                overlaps.append(overlap)
            if max(overlaps) > 0:
                idx = overlaps.index(max(overlaps))
                b.column = idx
                col_blocks[idx].append(b)
            else:
                # fallback to center
                center_x = (b.bbox[0] + b.bbox[2]) / 2.0
                distances = [abs(center_x - c) for c in col_centers]
                idx = min(range(len(distances)), key=lambda k: distances[k])
                b.column = idx
                col_blocks[idx].append(b)

        # sort within columns top-to-bottom (y0 ascending), tie-break x0
        for col in col_blocks:
            col.sort(key=lambda b: (b.bbox[1], b.bbox[0]))

        # prepare spanning sorted by top
        spanning_sorted = sorted(spanning_blocks, key=lambda b: b.bbox[1])

        ordered: List[LayoutBlock] = []
        span_idx = 0

        # iterate columns left-to-right and interleave spanning blocks
        for col in col_blocks:
            for blk in col:
                # insert any spanning blocks that appear above this block
                while span_idx < len(spanning_sorted) and spanning_sorted[span_idx].bbox[1] <= blk.bbox[1] + 1e-6:
                    ordered.append(spanning_sorted[span_idx])
                    span_idx += 1
                ordered.append(blk)
        # append remaining spanning blocks
        while span_idx < len(spanning_sorted):
            ordered.append(spanning_sorted[span_idx])
            span_idx += 1

        # assign reading_order indices
        for i, b in enumerate(ordered):
            b.reading_order = i

        return ordered

    # ------------------------- Block extraction & classification -------------
    def extract_and_classify_blocks(self, page: pdfplumber.page.Page) -> List[LayoutBlock]:
        """
        Extract blocks. Prefer block-level extract_text('dict') if available for richer spans;
        else use fallback word->line->block grouping. Use page font stats for relative classification.
        """
        page_font_stats = self.get_page_font_stats(page)
        blocks: List[LayoutBlock] = []
        page_width = getattr(page, "width", 1.0)
        page_height = getattr(page, "height", 1.0)

        # Try extract_text('dict') if supported
        try:
            if hasattr(page, "extract_text"):
                text_dict = page.extract_text("dict") or {}
            else:
                text_dict = {}
        except Exception:
            text_dict = {}

        if text_dict and "blocks" in text_dict:
            for bdata in text_dict.get("blocks", []):
                if "lines" not in bdata:
                    continue
                block_text = ""
                font_info = {}
                for line in bdata.get("lines", []):
                    for span in line.get("spans", []):
                        block_text += span.get("text", "")
                        if not font_info:
                            font_info = {
                                "font": span.get("font", ""),
                                "size": span.get("size", 0),
                                "flags": span.get("flags", 0),
                                "color": span.get("color", 0),
                            }
                block_text = (block_text or "").strip()
                if not block_text:
                    continue
                bbox = tuple(bdata.get("bbox", (0.0, 0.0, page_width, page_height)))
                btype, conf = self._classify_block(block_text, font_info, bbox, page, page_font_stats)
                blocks.append(LayoutBlock(bbox=bbox, text=block_text, block_type=btype, confidence=conf, font_info=font_info))
            return blocks

        # Fallback pipeline:
        words = self._extract_words(page)
        lines = self._words_to_lines(words)
        raw_blocks = self._lines_to_blocks(lines, page_font_stats)
        chars = getattr(page, "chars", []) or []

        for rb in raw_blocks:
            bbox = (rb["x0"], rb["top"], rb["x1"], rb["bottom"])
            text = rb["text"].strip()
            # try to find a representative char for font_info
            font_info = {}
            for ch in chars:
                # small intersection test: char entirely inside block
                if ch.get("x0", 0) >= bbox[0] - 1e-6 and ch.get("x1", 0) <= bbox[2] + 1e-6 and ch.get("top", 0) >= bbox[1] - 1e-6 and ch.get("bottom", 0) <= bbox[3] + 1e-6:
                    font_info = {"font": ch.get("fontname", ch.get("font", "")), "size": ch.get("size", ch.get("fontsize", None)), "flags": ch.get("flags", None)}
                    break
            btype, conf = self._classify_block(text, font_info, bbox, page, page_font_stats)
            blocks.append(LayoutBlock(bbox=bbox, text=text, block_type=btype, confidence=conf, font_info=font_info))
        return blocks

    def _classify_block(self, text: str, font_info: Dict, bbox: Tuple[float, float, float, float], page, page_font_stats: Dict[str, Any]) -> Tuple[str, float]:
        """
        Conservative heuristics for classifying a text block, relative to page stats.
        Returns (type, confidence).
        """
        page_width = getattr(page, "width", bbox[2] * 2)
        page_height = getattr(page, "height", bbox[3] * 2)
        median_size = page_font_stats.get("median_size", 12) or 12

        t = (text or "").strip()
        if not t:
            return "paragraph", 0.5

        # immediate formula detection from tokens or latex markers
        if self._contains_math_indicators(t):
            # If this looks like a display equation (centered + symbol density), prefer formula type
            center_x = (bbox[0] + bbox[2]) / 2.0
            centered = abs(center_x - page_width / 2.0) < (0.12 * page_width)
            # math density: occurrences of math symbols or latex markers
            math_symbols = re.findall(r'[=^_{}\\\\]|\\begin\\{equation\\}|\\\[|\\\]', t)
            math_density = len(math_symbols) / max(1, len(t))
            conf = 0.8 + 0.1 * math_density
            if centered and math_density > 0.04:
                return "formula", min(1.0, conf)
            # short inline formula lines might be part of paragraph
            if math_density > 0.12 or re.search(r'\\begin\{equation\}', t):
                return "formula", min(1.0, conf)

        # headings (relative font size heuristics)
        size_val = float(font_info.get("size") or median_size)
        if size_val > median_size * 1.1 and len(t) < 400:
            conf = min(1.0, (size_val / median_size) * 0.8)
            return "heading", conf

        tl = t.lower()
        if tl.startswith(("figure", "fig.", "table", "tab.")) or tl.strip().startswith(("fig.", "figure", "table", "tab.")):
            return "caption", 0.9

        # footnote: small font near bottom
        if size_val < median_size * 0.9 and bbox[1] > page_height * 0.82:
            return "footnote", 0.85

        # header/footer by position heuristics
        if bbox[1] < page_height * 0.08:
            return "header", 0.9
        if bbox[1] > page_height * 0.92:
            return "footer", 0.9

        # list items (1. or - or bullet)
        if re.match(r'^\s*[\dA-Za-z]+[\.\)]\s+', t) or t.strip().startswith("•") or t.strip().startswith("-"):
            return "list_item", 0.9

        # short caption-like paragraph
        if len(t) < 120 and any(p in t for p in [":", "—", "-"]) and (bbox[2] - bbox[0]) < (page_width * 0.6):
            return "caption", 0.75

        # default
        return "paragraph", 0.7

    @staticmethod
    def _contains_math_indicators(text: str) -> bool:
        """Conservative regex-based math indicator detection."""
        patterns = [
            r'[∑∫∏√±×÷≠≤≥∞∂∇α-ωΑ-Ω]',  # symbols
            r'\b\d+[\+\-\*/=]\d+\b',  # simple arithmetic
            r'\([^)]*[+\-*/=][^)]*\)',  # parentheses with operators
            r'[a-zA-Z]\s*=\s*[a-zA-Z0-9\+\-\*/\(\)]+',  # assignments/equality
            r'\b(?:sin|cos|tan|log|ln|exp|sqrt|sum|int)\s*\(',  # functions
            r'\\begin\{equation\}',  # latex equation env
            r'\\\[|\\\]',  # \[ \] display math
            r'\\\(|\\\)',  # \( \) inline math
        ]
        return any(re.search(p, text) for p in patterns)

    # ------------------------- Page orchestration ------------------------------
    def analyze_page_layout(self, page: pdfplumber.page.Page, table_rects: List = [], figure_rects: List = []) -> PageLayout:
        """
        Orchestrates full layout analysis for one page, with page stats integration.
        """
        blocks = self.extract_and_classify_blocks(page)
        columns, confidence = self.detect_columns(page, table_rects=table_rects, figure_rects=figure_rects)
        page_block_stats = {"median_height": statistics.median([b.bbox[3] - b.bbox[1] for b in blocks if b.bbox[3] > b.bbox[1]]) if blocks else 50.0}
        spanning = self.detect_spanning_blocks(blocks, columns, page_block_stats)
        ordered_blocks = self.build_reading_order(page, blocks, columns, spanning)
        headers, footers = self.identify_headers_footers(ordered_blocks, page)

        return PageLayout(
            page_number=getattr(page, "page_number", 1),
            width=getattr(page, "width", 0.0) or 0.0,
            height=getattr(page, "height", 0.0) or 0.0,
            blocks=ordered_blocks,
            columns=columns,
            headers=headers,
            footers=footers,
            spanning_blocks=spanning,
            column_confidence=confidence
        )

    def analyze_document(self, pages: List[pdfplumber.page.Page]) -> List[PageLayout]:
        """
        Analyze multiple pages and detect repeated headers/footers across pages, with global font cache.
        """
        global_font_stats = self._compute_global_font_stats(pages)
        page_layouts: List[PageLayout] = []
        for p in pages:
            pl = self.analyze_page_layout(p)
            page_layouts.append(pl)

        # collect header/footer candidates
        header_cand = defaultdict(int)
        footer_cand = defaultdict(int)
        for pl in page_layouts:
            for h in pl.headers:
                header_cand[h.text.strip()] += 1
            for f in pl.footers:
                footer_cand[f.text.strip()] += 1

        pages_n = max(1, len(page_layouts))
        repeated_headers = {t for t, c in header_cand.items() if c >= max(2, pages_n // 2)}
        repeated_footers = {t for t, c in footer_cand.items() if c >= max(2, pages_n // 2)}

        # mark matched blocks with high confidence
        for pl in page_layouts:
            for b in pl.blocks:
                text = b.text.strip()
                if text in repeated_headers:
                    b.block_type = "header"
                    b.confidence = max(b.confidence, 0.95)
                if text in repeated_footers:
                    b.block_type = "footer"
                    b.confidence = max(b.confidence, 0.95)
        return page_layouts

    def _compute_global_font_stats(self, pages: List[pdfplumber.page.Page]) -> Dict[str, Any]:
        """Cache global median font size across pages for consistent classification."""
        all_sizes = []
        for p in pages:
            stats = self.get_page_font_stats(p)
            all_sizes.extend([stats.get("median_size", 12)] * len(p.chars))  # Weighted by char count approx
        if not all_sizes:
            return {"global_median_size": 12}
        return {"global_median_size": statistics.median(all_sizes)}

    # ------------------------- Legacy helpers ---------------------------------
    @classmethod
    def strip_headers_footers(cls, page: pdfplumber.page.Page, header_h: int = 50, footer_h: int = 50):
        """Crop page in-place to remove header/footer regions (use with caution)."""
        try:
            page.crop((0, header_h, page.width, page.height - footer_h))
        except Exception:
            logger.exception("Failed to crop page for header/footer stripping")

    def identify_headers_footers(self, blocks: List[LayoutBlock], page) -> Tuple[List[LayoutBlock], List[LayoutBlock]]:
        """Identify header/footer blocks from a list of blocks (by position or type)."""
        page_height = getattr(page, "height", 1000)
        headers = [b for b in blocks if b.block_type == "header" or b.bbox[1] < page_height * 0.08]
        footers = [b for b in blocks if b.block_type == "footer" or b.bbox[1] > page_height * 0.92]
        return headers, footers

    @staticmethod
    def get_page_font_stats(page: pdfplumber.page.Page) -> Dict[str, Any]:
        """Return font-size statistics for the page's chars, with median."""
        font_sizes = [ch.get("size", ch.get("fontsize", None)) for ch in getattr(page, "chars", []) or []]
        font_sizes = [s for s in font_sizes if isinstance(s, (int, float)) and s > 0]  # Positive only
        if not font_sizes:
            return {"most_common_size": None, "avg_size": None, "median_size": 12}
        counter = Counter(font_sizes)
        return {"most_common_size": counter.most_common(1)[0][0] if counter else None,
                "avg_size": sum(font_sizes) / len(font_sizes),
                "median_size": statistics.median(font_sizes)}


# ------------------------- Diagnostic / example usage -------------------------
if __name__ == "__main__":
    import sys
    import pdfplumber
    if len(sys.argv) < 2:
        print("Usage: python layout_utils_enhanced.py <pdf-path>")
        sys.exit(1)
    pdf_path = sys.argv[1]
    with pdfplumber.open(pdf_path) as doc:
        lu = LayoutUtils(expected_columns=2)
        pages = [doc.pages[i] for i in range(min(5, len(doc.pages)))]
        layouts = lu.analyze_document(pages)
        for pl in layouts:
            print(f"--- Page {pl.page_number} (cols={len(pl.columns)}, conf={pl.column_confidence:.2f}) ---")
            print("Columns:", pl.columns)
            print("Spanning blocks:", [(b.block_type, b.bbox, b.text[:80].replace('\n', ' ')) for b in pl.spanning_blocks])
            print("First 8 reading order blocks:")
            for b in pl.blocks[:8]:
                print(f"  order={b.reading_order} col={b.column} type={b.block_type} conf={b.confidence:.2f} bbox={b.bbox} text='{b.text[:120].replace('\n',' ')}'")
