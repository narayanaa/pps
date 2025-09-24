"""
Lightweight dependency guards and a simple document validator.

Feature flags can be used by parsers to gracefully skip optional features.
"""

from typing import Optional, List


def _has(module: str) -> bool:
    try:
        __import__(module)
        return True
    except Exception:
        return False


HAS_PDF = _has("pdfplumber") and _has("fitz")
HAS_CAMEL0T = _has("camelot") or _has("camelot.io")
HAS_DOCX = _has("docx")
HAS_EPUB = _has("ebooklib")
HAS_TESSERACT = _has("pytesseract")
HAS_PADDLE = _has("paddleocr") and _has("paddleocr.ocr")
HAS_TRANSFORMERS = _has("transformers")


def validate_document(doc) -> List[str]:
    """Validate core invariants of the unified Document structure.

    Returns a list of human-readable warnings/errors (empty if valid).
    """
    problems: List[str] = []

    # Loose import to avoid circulars when imported from parsers
    try:
        from .document import Document  # type: ignore
        from .chapter import Chapter  # type: ignore
        from .section import Section  # type: ignore
    except Exception:
        # Best effort if running outside full package context
        Document = type("Document", (), {})  # type: ignore
        Chapter = type("Chapter", (), {})  # type: ignore
        Section = type("Section", (), {})  # type: ignore

    if not hasattr(doc, "chapters") or doc.chapters is None:
        problems.append("Document has no chapters list")
        return problems

    seen_ids = set()
    def _check_id(obj):
        obj_id = getattr(obj, "id", None)
        if obj_id is not None:
            if obj_id in seen_ids:
                problems.append(f"Duplicate id detected: {obj_id}")
            seen_ids.add(obj_id)

    _check_id(doc)

    for ch in getattr(doc, "chapters", []) or []:
        if not hasattr(ch, "sections"):
            problems.append("Chapter missing sections")
            continue
        _check_id(ch)
        for sec in getattr(ch, "sections", []) or []:
            _check_id(sec)
            if not hasattr(sec, "content"):
                problems.append("Section missing content list")
                continue
            if not isinstance(sec.content, list):
                problems.append("Section content is not a list")

    return problems



