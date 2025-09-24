from .parsing_stage import ParsingStage
from ..utils.structural_segmentation_utils import StructuralSegmentationUtils


class StructuralSegmentationStage(ParsingStage):
    def __init__(self, parser):
        self.parser = parser
        cfg = parser.config.get_setting("llm_postprocessing", {})
        self.util = StructuralSegmentationUtils(cfg)

    def process(self, doc):
        full_text = "\n".join(
            page.get("text", "") for page in getattr(doc, "pages", []) if page.get("text")
        )
        doc.sections = self.util.segment(full_text)
        return doc
