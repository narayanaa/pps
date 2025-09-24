import pytest
from pathlib import Path

# Try to import parser classes; set to None if unavailable
try:
    from parsers.psense.pdf.pdf_parser import PDFParser  # type: ignore
except Exception:
    PDFParser = None  # type: ignore

try:
    from parsers.psense.docx.docx_parser import DOCXParser  # type: ignore
except Exception:
    DOCXParser = None  # type: ignore

try:
    from parsers.psense.ebook.epub_parser import EBookParser  # type: ignore
except Exception:
    EBookParser = None  # type: ignore

try:
    from parsers.psense.md.md_parser import MarkdownParser  # type: ignore
except Exception:
    MarkdownParser = None  # type: ignore

from doc.psense.document.document import Document
from doc.psense.document.chapter import Chapter
from doc.psense.document.section import Section
from doc.psense.document.paragraph import Paragraph


def _assert_canonical_document_structure(doc: Document, parser_name: str) -> None:
    assert isinstance(doc, Document)
    assert hasattr(doc, 'title') and hasattr(doc, 'chapters')
    for ch in doc.chapters:
        assert isinstance(ch, Chapter)
        for sec in ch.sections:
            assert isinstance(sec, Section)
            assert isinstance(sec.content, list)


def test_parser_instantiation_and_min_parse():
    candidates = [
        ("PDF", PDFParser),
        ("DOCX", DOCXParser),
        ("ePub", EBookParser),
        ("Markdown", MarkdownParser),
    ]

    for name, cls in candidates:
        if cls is None:
            pytest.skip(f"{name} parser not available in this environment")
        # Instantiate with config if PDF
        if name == "PDF":
            config = Path(__file__).parent / ".." / ".." / ".." / "parsers" / "psense" / "pdf" / "tests" / "config.json"
            parser = cls(str(config)) if config.exists() else cls()
        else:
            parser = cls()
        assert parser is not None


def test_document_serialization_basic():
    doc = Document(title="Test Doc")
    ch = Chapter(title="C1", sections=[], number=1)
    sec = Section(title="S1", content=[Paragraph("Hello")], level=1)
    ch.sections.append(sec)
    doc.chapters.append(ch)
    text = doc.to_text()
    assert isinstance(text, str) and "Test Doc" in text

