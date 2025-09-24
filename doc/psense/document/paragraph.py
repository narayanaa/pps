
from textblob import TextBlob
import spacy

from ..data_element import DataElement
from .unique_id import generate_unique_id

# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")


class Paragraph(DataElement):
    def __init__(self, text: str, style: str = "Normal"):
        super().__init__()
        self.id = generate_unique_id()  # Unique identifier for each element
        self.text = text
        self.style = style  # For handling different paragraph styles (e.g., headings)

    def analyze_sentiment(self):
        if 'sentiment' in self.cache:
            return self.cache['sentiment']
        blob = TextBlob(self.text)
        sentiment = blob.sentiment.polarity
        self.cache['sentiment'] = sentiment
        return sentiment

    def extract_entities(self):
        if 'entities' in self.cache:
            return self.cache['entities']
        doc = nlp(self.text)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        self.cache['entities'] = entities
        return entities

    def compute_readability(self):
        if 'readability' in self.cache:
            return self.cache['readability']
        word_count = len(self.text.split())
        sentence_count = len(TextBlob(self.text).sentences)
        readability = word_count / sentence_count if sentence_count > 0 else 0
        self.cache['readability'] = readability
        return readability

    def extract_keywords(self):
        if 'keywords' in self.cache:
            return self.cache['keywords']
        doc = nlp(self.text)
        keywords = [chunk.text for chunk in doc.noun_chunks]
        self.cache['keywords'] = keywords
        return keywords

    def extract_metadata(self, aspects: list = None):
        if aspects is None:
            aspects = []  # Default to an empty list if aspects is None

        metadata = {
            "text": self.text,
            "style": self.style
        }
        if aspects and 'sentiment' in aspects:
            metadata["sentiment"] = self.analyze_sentiment()
        if aspects and 'entities' in aspects:
            metadata["entities"] = self.extract_entities()
        if aspects and 'readability' in aspects:
            metadata["readability"] = self.compute_readability()
        if aspects and 'keywords' in aspects:
            metadata["keywords"] = self.extract_keywords()
        return metadata

    def to_text(self):
        """Converts paragraph content to plain text."""
        return f"Paragraph (Style: {self.style}): {self.text}"

    def get_entities(self):
        """Extracts named entities from the paragraph using NLP."""
        if 'entities' in self.cache:
            return self.cache['entities']
        doc = nlp(self.text)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        self.cache['entities'] = entities
        return entities

    def __repr__(self):
        return f"Paragraph(style='{self.style}', text='{self.text[:30]}...')"

    def to_dict(self):
        """Convert Paragraph to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "text": self.text,
            "style": self.style,
            "caption": self.caption,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }
