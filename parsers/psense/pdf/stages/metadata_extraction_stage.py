
import pdfplumber

from doc.psense.document.document import Document
from parsers.psense.pdf.stages.parsing_stage import ParsingStage


class MetadataExtractionStage(ParsingStage):
    def process(self, doc: Document):
        pdf = self.parser.pdf_utils.load_pdf(doc.url)
        metadata = self.parser.metadata_utils.extract_metadata(pdf)
        if not metadata:
            import pdfplumber
            with pdfplumber.open(doc.url) as plumber_doc:
                metadata = self.parser.metadata_utils.infer_metadata(plumber_doc)
        # Set canonical fields
        doc.author = metadata.get("author")
        doc.created_date = metadata.get("created_date")
        doc.language = metadata.get("language", "English")
        doc.description = metadata.get("description")
        doc.title = metadata.get("title", doc.title)
        # Optionally store all metadata
        doc.metadata = metadata
