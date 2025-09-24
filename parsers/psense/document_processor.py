# A unified interface to process documents
from doc.psense.document.document_parser import DocumentParser
from doc.psense.document.doc_component import DocumentComponent


class DocumentProcessor:
    def __init__(self, parser: DocumentParser):
        self.parser = parser

    def process_document(self, filepath: str) -> DocumentComponent:
        return self.parser.parse(filepath)
