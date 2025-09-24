from typing import List, Union

from ..data_element import DataElement
from .image import Image
from .paragraph import Paragraph
from .table import Table


class Appendix(DataElement):
    def __init__(self, title: str, content: List[Union[Paragraph, Image, Table]]):
        super().__init__()
        self.title = title
        self.content = content

    def extract_metadata(self, aspects: list = None) -> dict:
        """Extract metadata from appendix content"""
        return {
            "title": self.title,
            "content_count": len(self.content),
            "content_types": [type(item).__name__ for item in self.content]
        }

    def to_text(self) -> str:
        """Convert appendix to plain text"""
        text = f"Appendix: {self.title}\n"
        for item in self.content:
            if hasattr(item, 'to_text'):
                text += item.to_text() + "\n"
            else:
                text += str(item) + "\n"
        return text

    def get_entities(self) -> list:
        """Extract entities from appendix content"""
        entities = []
        for item in self.content:
            if hasattr(item, 'get_entities'):
                entities.extend(item.get_entities())
        return entities

    def to_dict(self) -> dict:
        """Convert Appendix to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": "appendix",
            "title": self.title,
            "content": [item.to_dict() if hasattr(item, 'to_dict') else str(item) for item in self.content],
            "caption": self.caption,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create Appendix instance from dictionary"""
        # Note: This is a simplified version - in a real implementation,
        # you'd need to reconstruct the actual content objects
        appendix = cls(data["title"], [])
        appendix.id = data["id"]
        appendix.caption = data.get("caption")
        appendix.references = data.get("references", [])
        appendix.cache = data.get("cache", {})
        appendix.footnotes = data.get("footnotes")
        return appendix

    def __repr__(self) -> str:
        return f"Appendix(title='{self.title}', content_items={len(self.content)})"