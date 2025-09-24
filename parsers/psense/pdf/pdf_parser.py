from __future__ import annotations

"""
PDF Parser Implementation

Utilities:
1. PDFUtils
2. OCRUtils
3. LayoutUtils
4. ClassificationUtils
5. TableFigureUtils
6. MetadataUtils
7. CitationUtils
8. ConfigManager
9. LoggingUtils
10. ErrorHandler
11. PerformanceMonitor
12. PDFParser

High‑level orchestrator – configure once, call `parse()`.
"""

from pathlib import Path
from typing import List

# Import from corrected paths using relative imports
from .stages.citation_extraction_stage import CitationExtractionStage
from .utils.citation_utils import CitationUtils
from .utils.classification_utils import ClassificationUtils
from .config_manager import ConfigManager
from .stages.classification_stage import ClassificationStage
from .error_handler import ErrorHandler
from .utils.layout_utils import LayoutUtils
from .logging_utils import LoggingUtils
from .stages.metadata_extraction_stage import MetadataExtractionStage
from .utils.metadata_utils import MetadataUtils
from .utils.ocr_utils import OCRUtils
from .stages.page_processing_stage import PageProcessingStage
from .stages.parsing_stage import ParsingStage
from .utils.pdf_utils import PDFUtils
from .performance_monitor import PerformanceMonitor
from .utils.table_figure_utils import TableFigureUtils

# Import unified doc structure
from doc.psense.document.document import Document
from doc.psense.document.document_parser import DocumentParser
from doc.psense.document.chapter import Chapter
from doc.psense.document.section import Section
from doc.psense.document.paragraph import Paragraph
from doc.psense.document.table import Table
from doc.psense.document.image import Image


class PDFParser:
    """Compose multiple *ParsingStage* instances into a coherent pipeline."""

    def __init__(self, config_file: str | Path | None = None, stages: List[ParsingStage] | None = None):
        if config_file is None:
            config_file = "acme_ai_hub/config/parsers/pdf_config.json"
        self.config = ConfigManager(str(config_file))
        self.logger = LoggingUtils(self.config.get_setting("log_file") or "parser.log")
        self.error_handler = ErrorHandler()
        self.perf = PerformanceMonitor()

        # Shared utilities
        self.pdf_utils = PDFUtils()
        ocr_config = self.config.get_setting("ocr", {})
        self.ocr_utils = OCRUtils(ocr_config)
        self.layout_utils = LayoutUtils()
        self.classification_utils = ClassificationUtils()
        self.table_figure_utils = TableFigureUtils()
        self.metadata_utils = MetadataUtils()
        self.citation_utils = CitationUtils()

        # Build default pipeline
        self.stages: List[ParsingStage] = stages or [
            MetadataExtractionStage(self),
            ClassificationStage(self),
            PageProcessingStage(self),
            CitationExtractionStage(self),
        ]

    def add_stage(self, stage: ParsingStage):
        self.stages.append(stage)

    def parse(self, pdf_path: str | Path) -> Document:
        """Parse a PDF and return a canonical doc.psense.document.Document object."""
        path = Path(pdf_path)
        # Start with minimal metadata; stages will fill in details
        canonical_doc = Document(title=path.stem)
        canonical_doc.url = str(path)
        self.logger.log_info(f"Parsing '{path.name}' – {len(self.stages)} stages")
        with self.perf.track("total_parse"):
            for stage in self.stages:
                if not stage.should_process(canonical_doc):
                    continue
                name = stage.__class__.__name__
                self.logger.log_info(f"→ {name}")
                try:
                    with self.perf.track(name):
                        stage.process(canonical_doc)
                except Exception as exc:
                    self.error_handler.handle_exception(name, exc)
                    # Log error instead of adding to document since add_error method doesn't exist
                    self.logger.log_error(f"Error in stage {name}: {str(exc)}")
        self.logger.log_info("Done in %.2fs", self.perf.metrics().get("total_parse", 0))
        return canonical_doc


if __name__ == "__main__":
    import argparse, pprint

    parser = argparse.ArgumentParser(description="Parse a single PDF file -> JSON")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    args = parser.parse_args()

    engine = PDFParser(args.config)
    data = engine.parse(args.pdf)
    pprint.pp(data)
