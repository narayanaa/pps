from typing import List

from doc.psense.data_element import DataElement


class TableOfContents(DataElement):
    def __init__(self, entries: List[str]):
        super().__init__()
        self.entries = entries

    def add_entry(self, entry: str):
        """Add a new table of contents entry"""
        self.entries.append(entry)

    def remove_entry(self, entry: str) -> bool:
        """Remove a table of contents entry"""
        if entry in self.entries:
            self.entries.remove(entry)
            return True
        return False

    def extract_metadata(self, aspects: list = None) -> dict:
        """Extract metadata from table of contents"""
        return {
            "entry_count": len(self.entries),
            "entries": self.entries.copy(),
            "total_length": sum(len(entry) for entry in self.entries)
        }

    def to_text(self) -> str:
        """Convert table of contents to plain text"""
        text = "Table of Contents:\n"
        for i, entry in enumerate(self.entries, 1):
            text += f"  {i}. {entry}\n"
        return text

    def get_entities(self) -> list:
        """Extract entities from table of contents entries"""
        return [(entry, "TOC_ENTRY") for entry in self.entries]

    def to_dict(self) -> dict:
        """Convert TableOfContents to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": "table_of_contents",
            "entries": self.entries.copy(),
            "caption": self.caption,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create TableOfContents instance from dictionary"""
        toc = cls(data.get("entries", []))
        toc.id = data["id"]
        toc.caption = data.get("caption")
        toc.references = data.get("references", [])
        toc.cache = data.get("cache", {})
        toc.footnotes = data.get("footnotes")
        return toc

    def __repr__(self) -> str:
        return f"TableOfContents(entries={len(self.entries)})"