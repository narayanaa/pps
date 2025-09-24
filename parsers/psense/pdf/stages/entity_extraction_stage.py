# entity_extraction_stage.py
from typing import List
from .parsing_stage import ParsingStage
from ..utils.entity_extraction_utils import EntityExtractionUtils


class EntityExtractionStage(ParsingStage):
    """Stage wrapper: fetch text from Document, call utils, store results."""

    def __init__(self, parser):
        self.parser = parser
        cfg = parser.config.get_setting("llm_postprocessing", {})
        self.util = EntityExtractionUtils(cfg)

    # Pipeline hook ----------------------------------------------------- #
    def process(self, doc):
        full_text: str = "\n".join(
            page.get("text", "") for page in getattr(doc, "pages", []) if page.get("text")
        )
        ents: List[dict] = self.util.extract(full_text)
        doc.entities = ents                         # <— enrich Document
        return doc
