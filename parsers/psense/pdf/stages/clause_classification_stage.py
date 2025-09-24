from typing import List
from .parsing_stage import ParsingStage
from ..utils.clause_classification_utils import ClauseClassificationUtils


class ClauseClassificationStage(ParsingStage):
    def __init__(self, parser):
        self.parser = parser
        cfg = parser.config.get_setting("llm_postprocessing", {})
        self.util = ClauseClassificationUtils(cfg)

    def process(self, doc):
        # Use already segmented sections if available, else naive split by full stops
        raw_clauses: List[str]
        if hasattr(doc, "sections") and doc.sections:
            raw_clauses = [s["text"] for s in doc.sections]
        else:
            full_text = "\n".join(
                page.get("text", "") for page in getattr(doc, "pages", []) if page.get("text")
            )
            raw_clauses = [c.strip() for c in full_text.split(".") if len(c.strip()) > 10]

        doc.clause_labels = self.util.classify(raw_clauses)
        return doc
