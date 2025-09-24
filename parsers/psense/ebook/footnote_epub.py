# footnote.py
class Footnote:
    def __init__(self, text: str, reference: str = ""):
        """
        A simple class to represent a footnote in the document.

        :param text: The actual content of the footnote.
        :param reference: The location or reference in the text (e.g., a link or anchor).
        """
        self.text = text
        self.reference = reference

    def __repr__(self):
        return f"Footnote(text={self.text}, reference={self.reference})"

    def to_dict(self):
        """Converts the footnote into a dictionary format for easy serialization."""
        return {
            "text": self.text,
            "reference": self.reference
        }
