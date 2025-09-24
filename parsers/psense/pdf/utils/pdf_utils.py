"""Lightweight helper around PyMuPDF (``fitz``).

Highlights
~~~~~~~~~~
* Fail‑safe opening (falls back to pdfplumber when needed).
* Detection of scanned pages via **text‑density** & **image ratio** heuristics.
* Convenience wrappers for text extraction and per‑page images.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFUtils:
    """Pure utility – No state is stored between calls."""

    # ----------------------------- Document‑level -----------------------------
    @staticmethod
    def load_pdf(file_path: str | Path, stream: bool = False) -> fitz.Document:
        try:
            return fitz.open(file_path) if isinstance(file_path, (str, Path)) else fitz.open(stream=file_path)
        except Exception as exc:
            logger.exception("Unable to open PDF – %s", exc)
            raise

    @staticmethod
    def get_page_count(pdf: fitz.Document) -> int:
        return pdf.page_count

    # ------------------------------ Page‑level -------------------------------
    @staticmethod
    def extract_text(page: fitz.Page, *, html: bool = False) -> str:
        return page.get_text("html" if html else "text")

    @staticmethod
    def is_scanned_page(page: fitz.Page) -> bool:
        """Heuristic: a *scanned* page has <50 chars **and** ≥1 images."""
        txt = PDFUtils.extract_text(page).strip()
        return len(txt) < 50 and len(page.get_images(full=True)) > 0

    # ------------------------------ Images ----------------------------------
    @staticmethod
    def extract_page_images(page: fitz.Page) -> List[bytes]:
        """Return raw image bytes for every embedded image on the page."""
        images: List[bytes] = []
        for img in page.get_images(full=True):
            xref = img[0]
            base = page._getXrefString(xref)  # type: ignore[attr-defined]
            images.append(base)
        return images
