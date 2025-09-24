

from abc import ABC, abstractmethod
from typing import Union

from .document.invalid_reference_error import InvalidReferenceError
from .document.unique_id import generate_unique_id


class DataElement(ABC):
    def __init__(self):
        self.caption = None
        self.id = generate_unique_id()
        self.references = []  # Store references to other document elements
        self.cache = {}  # To store computed aspects
        self.footnotes = None

    def add_reference(self, element: Union[dict, 'DataElement']) -> None:
        """
        Adds a reference to the element.

        :param element: A dictionary containing an 'id' key or an instance of DataElement.
        :raises InvalidReferenceError: If the element is not a valid type.
        """

        def get_id(ref) -> str:
            """Extract the ID from a dictionary or an object."""
            if isinstance(ref, dict) and "id" in ref:
                return ref["id"]
            elif hasattr(ref, 'id'):
                return ref.id
            else:
                raise InvalidReferenceError(f"Invalid reference type: {type(ref)}")

        try:
            self.references.append(get_id(element))
        except InvalidReferenceError as e:
            # You can add logging here if needed
            print(f"Failed to add reference: {e}")

    def clear_cache(self):
        self.cache.clear()

    def get_aspect(self, aspect_name):
        if aspect_name in self.cache:
            return self.cache[aspect_name]
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "caption": self.caption,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }

    @classmethod
    def from_dict(cls, data):
        element = cls()
        element.id = data["id"]
        element.caption = data["caption"] if "caption" in data else None
        element.references = data["references"]
        element.cache = data["cache"]
        element.footnotes = data["footnotes"]
        return element

    @abstractmethod
    def extract_metadata(self, aspects: list = None) -> dict:
        """
        Extract metadata for the document element. Each subclass must implement its own method.
        """
        pass

    @abstractmethod
    def to_text(self) -> str:
        pass

    @abstractmethod
    def get_entities(self) -> list:
        pass

    @abstractmethod
    def __repr__(self) -> str:
        """
        A string representation of the document element. Each subclass must implement its own method.
        """
        pass
