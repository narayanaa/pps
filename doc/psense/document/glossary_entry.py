from doc.psense.data_element import DataElement


class GlossaryEntry(DataElement):
    def __init__(self, term: str, definition: str):
        super().__init__()
        self.term = term
        self.definition = definition

    def extract_metadata(self, aspects: list = None) -> dict:
        """Extract metadata from glossary entry"""
        return {
            "term": self.term,
            "definition_length": len(self.definition),
            "word_count": len(self.definition.split())
        }

    def to_text(self) -> str:
        """Convert glossary entry to plain text"""
        return f"{self.term}: {self.definition}"

    def get_entities(self) -> list:
        """Extract entities from glossary entry"""
        return [(self.term, "TERM"), (self.definition, "DEFINITION")]

    def to_dict(self) -> dict:
        """Convert GlossaryEntry to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": "glossary_entry",
            "term": self.term,
            "definition": self.definition,
            "caption": self.caption,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create GlossaryEntry instance from dictionary"""
        entry = cls(data["term"], data["definition"])
        entry.id = data["id"]
        entry.caption = data.get("caption")
        entry.references = data.get("references", [])
        entry.cache = data.get("cache", {})
        entry.footnotes = data.get("footnotes")
        return entry

    def __repr__(self) -> str:
        return f"GlossaryEntry(term='{self.term}')"