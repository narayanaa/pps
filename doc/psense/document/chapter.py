from typing import List, Optional

from ..data_element import DataElement
from .section import Section


class Chapter(DataElement):
    def __init__(self, title: str, sections: List[Section], number: int, author: Optional[str] = None):
        super().__init__()
        self.title = title
        self.sections = sections
        self.number = number  # Track chapter number
        self.author = author

    def aggregate_sentiment(self):
        if 'sentiment' in self.cache:
            return self.cache['sentiment']
        sentiments = [section.aggregate_sentiment() for section in self.sections]
        chapter_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        self.cache['sentiment'] = chapter_sentiment
        return chapter_sentiment

    def aggregate_readability(self):
        if 'readability' in self.cache:
            return self.cache['readability']
        readabilities = [section.aggregate_readability() for section in self.sections]
        chapter_readability = sum(readabilities) / len(readabilities) if readabilities else 0
        self.cache['readability'] = chapter_readability
        return chapter_readability

    def aggregate_keywords(self):
        if 'keywords' in self.cache:
            return self.cache['keywords']
        keywords = [section.extract_keywords() for section in self.sections]
        self.cache['keywords'] = keywords
        return keywords

    def extract_metadata(self, aspects: list = None):
        metadata = {
            "title": self.title,
            "author": self.author,
            "section_count": len(self.sections)
        }
        if aspects and 'sentiment' in aspects:
            metadata["chapter_sentiment"] = self.aggregate_sentiment()
        if aspects and 'readability' in aspects:
            metadata["chapter_readability"] = self.aggregate_readability()
        if aspects and 'keywords' in aspects:
            metadata["chapter_keywords"] = self.aggregate_keywords()
        return metadata

    def to_text(self):
        """Recursively converts the chapter content to plain text."""
        chapter_text = f"Chapter {self.number}: {self.title}\n"
        for section in self.sections:
            chapter_text += section.to_text() + "\n"
        return chapter_text

    def get_entities(self):
        """Extracts named entities from the chapter content."""
        all_entities = []
        for section in self.sections:
            all_entities.extend(section.get_entities())
        return all_entities

    def __repr__(self):
        return f"Chapter(title='{self.title}', number={self.number}, sections={len(self.sections)})"

    def to_dict(self):
        """Convert Chapter to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "number": self.number,
            "author": self.author,
            "sections": [section.to_dict() if hasattr(section, 'to_dict') else str(section) for section in self.sections],
            "caption": self.caption,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }
