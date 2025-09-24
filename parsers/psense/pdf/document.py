from __future__ import annotations
from typing import List, Dict, Any
import json

class Document:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.path = file_path
        self.metadata: Dict[str, Any] = {}
        self.document_type: str = ""
        self.pages: List[Dict[str, Any]] = []  # List of page-level dictionaries
        self.references: List[str] = []
        self.errors: List[str] = []

    def add_page(self, page_data: Dict[str, Any]):
        """Add processed page data to the document."""
        self.pages.append(page_data)

    def set_metadata(self, metadata: Dict[str, Any]):
        """Update document metadata."""
        self.metadata.update(metadata)

    def set_document_type(self, doc_type: str):
        """Set the document type."""
        self.document_type = doc_type

    def add_references(self, references: List[str]):
        """Add extracted references."""
        self.references.extend(references)

    def add_error(self, error: str):
        """Add an error encountered during parsing."""
        self.errors.append(error)

    def to_dict(self) -> Dict[str, Any]:
        """Convert Document to a dictionary, ensuring all types are serializable."""
        def serialize(obj):
            if isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            elif isinstance(obj, (list, tuple)):
                return [serialize(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: serialize(value) for key, value in obj.items()}
            else:
                return str(obj)  # Fallback for non-serializable types

        return {
            "file_path": self.file_path,
            "metadata": serialize(self.metadata),
            "document_type": self.document_type,
            "pages": serialize(self.pages),
            "references": self.references,
            "errors": self.errors
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert the document to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
