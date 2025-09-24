# Abstract class for Document Parsing
from abc import ABC, abstractmethod

from doc.psense.document.document import Document


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, filepath: str) -> Document:
        pass
