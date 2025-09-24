from .page_processing_stage import PageProcessingStage
import logging
from ..utils.ocr_utils import OCRUtils

logger = logging.getLogger(__name__)


class OCRStage(PageProcessingStage):
    def should_process_page(self, page):
        return page.is_scanned

    def process_page(self, page, plumber_page, fitz_page):
        try:
            ocr_text = OCRUtils.run_ocr(fitz_page)
            logger.info(f"OCR completed for page {page.number if hasattr(page, 'number') else 'unknown'}")
            return {"text": ocr_text}
        except Exception as e:
            logger.error(f"OCR failed for page: {str(e)}")
            return {"text": "", "error": str(e)}
