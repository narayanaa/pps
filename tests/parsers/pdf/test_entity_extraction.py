import pytest
from pathlib import Path

# Skip if heavy deps are missing
pdfplumber = pytest.importorskip("pdfplumber")
fitz = pytest.importorskip("fitz")

from parsers.psense.pdf.utils.citation_utils import CitationUtils


def test_citation_extraction_smoke():
    sample_pdf = Path(__file__).parent.parent.parent / ".." / ".." / "parsers" / "psense" / "pdf" / "tests" / "eurosurv-25-15-4.pdf"
    if not sample_pdf.exists():
        pytest.skip(f"Sample PDF not found: {sample_pdf}")
    text = "This is a reference to WHO (2020) and CDC (2019) publications."
    refs = CitationUtils.extract_citations_from_text(text)
    assert isinstance(refs, list)

