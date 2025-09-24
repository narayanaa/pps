from typing import List, Union, Optional

from ..data_element import DataElement
from .doc_component import DocumentComponent
from .image import Image
from .paragraph import Paragraph
from .table import Table


class Section(DataElement, DocumentComponent):
    def __init__(self, title: str, content: List[Union[Paragraph, Image, Table]], level: int = 1,
                 author: Optional[str] = None):
        super().__init__()
        self.title = title
        self.content = content
        self.level = level  # Define section level (e.g., 1 for main section, 2 for subsections)
        self.subsections = []  # To store nested subsections
        self.author = author

    def add_subsection(self, subsection):
        self.subsections.append(subsection)

    def aggregate_sentiment(self):
        if 'sentiment' in self.cache:
            return self.cache['sentiment']
        sentiments = [p.analyze_sentiment() for p in self.content if isinstance(p, Paragraph)]
        aggregated_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        self.cache['sentiment'] = aggregated_sentiment
        return aggregated_sentiment

    def aggregate_readability(self):
        if 'readability' in self.cache:
            return self.cache['readability']
        readabilities = [p.compute_readability() for p in self.content if isinstance(p, Paragraph)]
        aggregated_readability = sum(readabilities) / len(readabilities) if readabilities else 0
        self.cache['readability'] = aggregated_readability
        return aggregated_readability

    def aggregate_entities(self):
        if 'entities' in self.cache:
            return self.cache['entities']
        entities = [p.extract_entities() for p in self.content]
        self.cache['entities'] = entities
        return entities

    def extract_metadata(self, aspects: list = None):
        metadata = {
            "title": self.title,
            "paragraph_count": len(self.content)
        }
        if aspects and 'sentiment' in aspects:
            metadata["section_sentiment"] = self.aggregate_sentiment()
        if aspects and 'readability' in aspects:
            metadata["section_readability"] = self.aggregate_readability()
        if aspects and 'entities' in aspects:
            metadata["section_entities"] = self.aggregate_entities()
        return metadata

    def extract_keywords(self):
        """
        Aggregates keywords from all Paragraph objects in the section's content.
        """
        if 'keywords' in self.cache:
            return self.cache['keywords']

        all_keywords = []
        for element in self.content:
            if isinstance(element, Paragraph):
                keywords = element.extract_keywords()
                all_keywords.extend(keywords)

        # Store aggregated keywords in cache
        self.cache['keywords'] = all_keywords
        return all_keywords

    def get_content(self):
        return self.content

    def to_text(self):
        """Converts section content to plain text."""
        section_text = f"Section Title: {self.title}\n"
        for element in self.content:
            section_text += element.to_text() + "\n"
        return section_text

    def get_entities(self):
        """Extracts named entities from the section content."""
        all_entities = []
        for element in self.content:
            all_entities.extend(element.get_entities())
        return all_entities

    def __repr__(self):
        return f"Section(title='{self.title}', level={self.level}, content_items={len(self.content)})"

    def to_dict(self):
        """Convert Section to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "level": self.level,
            "author": self.author,
            "content": [item.to_dict() if hasattr(item, 'to_dict') else str(item) for item in self.content],
            "subsections": [sub.to_dict() if hasattr(sub, 'to_dict') else str(sub) for sub in self.subsections],
            "caption": self.caption,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }
