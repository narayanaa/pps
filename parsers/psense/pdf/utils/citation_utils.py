"""Reference‑section detection & parsing."""
from __future__ import annotations

import re
from typing import List

import pdfplumber  # type: ignore


class CitationUtils:
    """Splits a References section into individual citations."""

    SECTION_KEYS = ("references", "bibliography", "works cited")

    def extract_references_section(self, doc: pdfplumber.PDF) -> str:
        for page in reversed(doc.pages):
            text = (page.extract_text() or "").lower()
            if any(k in text for k in self.SECTION_KEYS):
                return page.extract_text() or ""
        return ""

    def parse_references(self, section_text: str) -> List[str]:
        """Split a *references* blob into a clean list."""
        # Handle both numbered lists and plain paragraphs
        section_text = re.sub(r"\s+", " ", section_text.strip())  # normalise whitespace
        refs = re.split(r"(?:^|\n)\s*(?:\d+\.|•|\[\d+\])\s+", section_text)
        return [r.strip() for r in refs if r.strip()]
