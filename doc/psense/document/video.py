from doc.psense.data_element import DataElement
from doc.psense.document.image import load_patterns_from_file


class Video(DataElement):
    def __init__(self, file_path: str, caption: str = "", alt_text: str = None,
                 metadata_file: str = 'video_metadata.yaml'):
        super().__init__()
        self.file_path = file_path
        self.caption = caption
        self.alt_text = alt_text
        self.metadata = self.extract_metadata(metadata_file)

    def extract_metadata(self, aspects: list = None):
        # Placeholder for video metadata extraction (can be expanded for video analysis)
        video_metadata = load_patterns_from_file("video_metadata.yaml")

        metadata = {
            "caption": self.caption,
            "alt_text": self.alt_text,
            "file_path": self.file_path,
            "duration": video_metadata.get("duration", "unknown"),
            "resolution": video_metadata.get("resolution", "unknown"),
            "file_format": video_metadata.get("format", "unknown"),
            "frame_rate": video_metadata.get("frame_rate", "unknown"),
        }

        return metadata

    def to_dict(self):
        return {
            "file_path": self.file_path,
            "caption": self.caption,
            "alt_text": self.alt_text,
            "metadata": self.metadata,
            "id": self.id
        }

    @classmethod
    def from_dict(cls, data: dict, metadata_file: str = 'video_metadata.yaml'):
        video = cls(data["file_path"], data["caption"], data["alt_text"], metadata_file)
        video.metadata = data["metadata"]
        video.id = data["id"]
        return video

    def to_text(self):
        """Returns the caption or alt text as plain text for the video."""
        return f"Video: {self.caption or self.alt_text}"

    def get_entities(self):
        """Extracts entities from the video metadata."""
        entities = []
        if self.caption:
            entities.append((self.caption, "CAPTION"))
        if self.alt_text:
            entities.append((self.alt_text, "ALT_TEXT"))
        return entities

    def __repr__(self):
        return f"Video(caption='{self.caption}', file_path='{self.file_path}')"
