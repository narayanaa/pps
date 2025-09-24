from typing import Dict, List, Optional

from doc.psense.data_element import DataElement
from doc.psense.document.glossary_entry import GlossaryEntry


class Glossary(DataElement):
    def __init__(self, entries: List[GlossaryEntry]):
        super().__init__()
        self.entries = {entry.term: entry for entry in entries}

    def get_definition(self, term: str) -> Optional[str]:
        entry = self.entries.get(term)
        return entry.definition if entry else None

    def add_entry(self, entry: GlossaryEntry):
        """Add a new glossary entry"""
        self.entries[entry.term] = entry

    def remove_entry(self, term: str) -> bool:
        """Remove a glossary entry by term"""
        if term in self.entries:
            del self.entries[term]
            return True
        return False

    def extract_metadata(self, aspects: list = None) -> dict:
        """Extract metadata from glossary"""
        return {
            "entry_count": len(self.entries),
            "terms": list(self.entries.keys()),
            "total_definitions_length": sum(len(entry.definition) for entry in self.entries.values())
        }

    def to_text(self) -> str:
        """Convert glossary to plain text"""
        text = "Glossary:\n"
        for term, entry in sorted(self.entries.items()):
            text += f"  {entry.to_text()}\n"
        return text

    def get_entities(self) -> list:
        """Extract entities from all glossary entries"""
        entities = []
        for entry in self.entries.values():
            entities.extend(entry.get_entities())
        return entities

    def to_dict(self) -> dict:
        """Convert Glossary to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": "glossary",
            "entries": {term: entry.to_dict() for term, entry in self.entries.items()},
            "caption": self.caption,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create Glossary instance from dictionary"""
        entries = []
        for term, entry_data in data.get("entries", {}).items():
            if isinstance(entry_data, dict):
                entries.append(GlossaryEntry.from_dict(entry_data))
        
        glossary = cls(entries)
        glossary.id = data["id"]
        glossary.caption = data.get("caption")
        glossary.references = data.get("references", [])
        glossary.cache = data.get("cache", {})
        glossary.footnotes = data.get("footnotes")
        return glossary

    def __repr__(self) -> str:
        return f"Glossary(entries={len(self.entries)})"