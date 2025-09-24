import os
import re
import yaml
from ..data_element import DataElement

def load_patterns_from_file(file_path: str = None) -> dict:
    """
    Loads hyperlink metadata patterns from a YAML file.

    Args:
        file_path (str): The path to the YAML file. If None, defaults to 'hyperlink_patterns.yaml' in the same directory.

    Returns:
        dict: Dictionary of patterns.
    """
    if file_path is None:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, "hyperlink_patterns.yaml")

    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

class Hyperlink(DataElement):
    def __init__(self, url: str, anchor_text: str = "", pattern_file: str = None):
        super().__init__()
        self.url = url
        self.anchor_text = anchor_text
        self.patterns = load_patterns_from_file(pattern_file)
        self.metadata = self.extract_metadata()

    def extract_metadata(self):
        metadata = {
            "header": {
                "keys": {}
            },
            "data": {}
        }
        
        for key, pattern in self.patterns.items():
            match = re.search(pattern["pattern"], self.url)
            if match:
                metadata["header"]["keys"][key] = pattern["data_type"]
                metadata["data"][key] = match.group(1)
        
        metadata["url"] = self.url
        metadata["anchor_text"] = self.anchor_text
        #print(f"Metadata: {metadata}")
        return metadata

    def to_dict(self):
        return {
            "url": self.url,
            "anchor_text": self.anchor_text,
            "metadata": self.metadata,
            "id": self.id
        }

    @classmethod
    def from_dict(cls, data: dict, pattern_file: str = None):
        hyperlink = cls(data["url"], data["anchor_text"], pattern_file)
        hyperlink.metadata = data["metadata"]
        hyperlink.id = data["id"]
        return hyperlink

    def to_text(self):
        """Returns the hyperlink as a plain text representation."""
        return f"Hyperlink: {self.anchor_text} ({self.url})"

    def get_entities(self):
        """Extracts entities from the hyperlink data."""
        return [(self.url, "URL"), (self.anchor_text, "ANCHOR_TEXT")]

    def __repr__(self):
        return f"Hyperlink(anchor_text='{self.anchor_text}', url='{self.url}')"

# Example usage
"""
hyperlink = Hyperlink("https://www.example.com", "Example Site")
metadata = hyperlink.metadata
print(metadata)

hyperlink_dict = hyperlink.to_dict()
new_hyperlink = Hyperlink.from_dict(hyperlink_dict)
print(new_hyperlink.metadata)
"""
