import pytest
from pathlib import Path

pdfplumber = pytest.importorskip("pdfplumber")
fitz = pytest.importorskip("fitz")

from parsers.psense.pdf.utils.structural_segmentation_utils import StructuralSegmentationUtils
from parsers.psense.pdf.pdf_parser import PDFParser
from doc.psense.document.document import Document


def test_segmentation_utils_smoke():
	utils = StructuralSegmentationUtils({})
	sections = utils.segment("Intro. Background. Methods. Results. Conclusion.")
	assert isinstance(sections, list)
	assert all(set(["label","text","start","end"]) <= set(s.keys()) for s in sections)


def test_pdf_parser_smoke():
	sample_pdf = Path(__file__).parent.parent / "pdf_raw" / "eurosurv-25-15-4.pdf"
	if not sample_pdf.exists():
		pytest.skip(f"Sample PDF not found: {sample_pdf}")
	config = Path(__file__).parent.parent / "pdf_raw" / "config.json"
	parser = PDFParser(str(config)) if config.exists() else PDFParser()
	doc = parser.parse(str(sample_pdf))
	assert isinstance(doc, Document)
	assert doc.chapters

