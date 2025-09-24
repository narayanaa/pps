from __future__ import annotations
import logging
import pdfplumber  # type: ignore
from typing import Any, Dict
from doc.psense.document.document import Document
from .parsing_stage import ParsingStage

logger = logging.getLogger(__name__)


class ClassificationStage(ParsingStage):
    """Stage for classifying the document type using ClassificationUtils."""

    def __init__(self, parser):
        super().__init__(parser)
        self.domain = self.parser.config.get_setting("classification_domain", "generic")

    def should_process(self, doc: Document) -> bool:
        """Process the document if it hasn't been classified yet."""
        return not getattr(doc, "document_type", None)

    def process(self, doc: Document) -> None:
        """Classify the document and update its type."""
        try:
            with pdfplumber.open(doc.url) as plumber_doc:
                classification_result = self.parser.classification_utils.classify(plumber_doc, domain=self.domain)
                doc.document_type = classification_result.label
                logger.info(
                    f"Document classified as '{classification_result.label}' with confidence {classification_result.confidence or 'N/A'}")
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            if hasattr(doc, "add_error"):
                doc.add_error(f"ClassificationStage error: {str(e)}")
