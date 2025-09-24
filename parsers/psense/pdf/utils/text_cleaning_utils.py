import unicodedata
import re


class TextCleaningUtils:
    @staticmethod
    def clean_text(text: str, config: dict) -> str:
        # Normalize unicode characters
        if config.get("normalize_unicode", True):
            text = unicodedata.normalize("NFKC", text)

        # Replace common ligatures
        if config.get("replace_ligatures", True):
            ligatures = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
            for lig, rep in ligatures.items():
                text = text.replace(lig, rep)

        # Remove non-ASCII characters
        if config.get("remove_non_ascii", True):
            text = ''.join(c for c in text if ord(c) < 128)

        # Collapse multiple newlines into one
        if config.get("collapse_newlines", True):
            text = re.sub(r'\n+', '\n', text)

        # Normalize whitespace
        if config.get("fix_whitespace", True):
            text = re.sub(r'\s+', ' ', text).strip()

        # Remove headers/footers (customize patterns as needed)
        if config.get("remove_headers_footers", True):
            lines = text.splitlines()
            cleaned_lines = [line for line in lines if
                             not re.match(r'^Page\s+\d+|^Confidential|^[A-Z]{2,}\s+\d+$', line, re.IGNORECASE)]
            text = '\n'.join(cleaned_lines)

        # Remove repeated characters (e.g., "eee" -> "e")
        text = re.sub(r'(.)\1{2,}', r'\1', text)

        # Remove OCR artifacts like (cid:xx)
        text = re.sub(r'\(cid:\d+\)', '', text)

        # Remove random sequences of short words (e.g., "a een a een")
        text = re.sub(r'\b\w{1,3}\s+\w{1,3}\s+\w{1,3}\b', '', text)

        # Keep only alphanumeric characters, spaces, and basic punctuation
        text = re.sub(r'[^\w\s.,!?]', '', text)

        return text
