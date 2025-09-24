from ..utils.layout_utils import LayoutUtils
from .parsing_stage import ParsingStage


class LayoutAnalysisStage(ParsingStage):
    def process(self, doc):
        for page in doc.pages:
            LayoutUtils.strip_headers_footers(page)
            page.reading_order = LayoutUtils.build_reading_order(page)
