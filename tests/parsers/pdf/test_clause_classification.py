import pytest
from pathlib import Path

pytest.importorskip("transformers")
pdfplumber = pytest.importorskip("pdfplumber")
fitz = pytest.importorskip("fitz")

from parsers.psense.pdf.utils.clause_classification_utils import ClauseClassificationUtils


def test_clause_classification_smoke():
	utils = ClauseClassificationUtils({})
	labels = utils.classify_clauses(["This is a sample contract clause."])
	assert isinstance(labels, list)
