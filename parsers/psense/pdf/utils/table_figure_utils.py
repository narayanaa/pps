"""Extract tables & figures using Camelot + PyMuPDF."""
from __future__ import annotations

import logging
from typing import Any, List

import camelot
import fitz  # PyMuPDF
import pdfplumber  # type: ignore
from PIL import Image

logger = logging.getLogger(__name__)


class TableFigureUtils:
    # ------------------------------------------------------------------
    # Tables (Camelot)
    # ------------------------------------------------------------------
    def detect_tables(self, plumber_page: pdfplumber.page.Page) -> List[Any]:
        page_no = plumber_page.page_number  # 1‑based in Camelot
        with pdfplumber.open(plumber_page.pdf.stream) as doc_stream:  # type: ignore[arg-type]
            path = doc_stream.stream.name  # path on disk (temp file) – works for real paths
        try:
            tables = camelot.read_pdf(path, pages=str(page_no), flavor="stream")
            return list(tables)
        except Exception as exc:
            logger.debug("Camelot failed on page %s – %s", page_no, exc)
            return []

    def extract_table_data(self, table: Any):
        return table.df.values.tolist() if hasattr(table, "df") else table.data

    # ------------------------------------------------------------------
    # Figures (PyMuPDF raster crops)
    # ------------------------------------------------------------------
    def detect_figures(self, page: fitz.Page) -> List[fitz.Rect]:
        return [fitz.Rect(img["bbox"]) if isinstance(img, dict) else fitz.Rect(img[:4]) for img in page.get_images(full=True)]

    def extract_figure(self, page: fitz.Page, rect: fitz.Rect) -> Image.Image:
        pix = page.get_pixmap(clip=rect)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
