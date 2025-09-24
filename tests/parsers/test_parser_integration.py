import pytest
from pathlib import Path

try:
    from parsers.psense.pdf.pdf_parser import PDFParser  # type: ignore
except Exception:
    PDFParser = None  # type: ignore

def test_parser_error_handling_minimal():
    if PDFParser is None:
        pytest.skip("PDFParser not available")
    config = Path(__file__).parent / ".." / ".." / ".." / "parsers" / "psense" / "pdf" / "tests" / "config.json"
    parser = PDFParser(str(config)) if config.exists() else PDFParser()
    with pytest.raises(Exception):
        parser.parse("/path/to/nonexistent.pdf")

