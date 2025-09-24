"""Extract embedded or inferred metadata."""
from __future__ import annotations

from typing import Dict

import fitz  # PyMuPDF
import pdfplumber  # type: ignore


class MetadataUtils:
    def extract_metadata(self, pdf: fitz.Document) -> Dict[str, str]:
        return pdf.metadata or {}

    def infer_metadata(self, doc: pdfplumber.PDF) -> Dict[str, str]:
        fp_text = doc.pages[0].extract_text() or ""
        lines = [ln.strip() for ln in fp_text.split("\n") if ln.strip()]
        return {
            "title": lines[0] if lines else "Unknown",
            "author": lines[1] if len(lines) > 1 else "Unknown",
        }
