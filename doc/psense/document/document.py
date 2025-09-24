# Enhanced Metadata support for the entire document
from datetime import datetime
from typing import Optional
from ..data_element import DataElement
from .section import Section
from .chapter import Chapter
from .paragraph import Paragraph
from .table import Table
from .hyperlink import Hyperlink
from .image import Image


class Document(DataElement):
    def __init__(self, title: str, author: Optional[str] = None, created_date: Optional[datetime] = None,
                 language: Optional[str] = "English", translator: Optional[str] = "Original",
                 description: Optional[str] = None, url: Optional[str] = None):
        super().__init__()
        self.title = title
        self.author = author
        self.created_date = created_date or datetime.now()
        self.language = language
        self.translator = translator
        self.description = description
        self.url = url
        self.chapters = []
        self.images = []
        self.tables = []
        self.image_content = []
        self.child_documents = []

    def add_chapter(self, chapter):
        self.chapters.append(chapter)

    def add_images(self, page_number, imgs):
        self.images.append({"page: ": page_number, "images: ": imgs})

    def add_table(self, page_number, table):
        self.tables.append({"page: ": page_number, "data: ": table})

    def add_image_content(self, page_number, content):
        self.image_content.append({"page: ": page_number, "content: ": content})

    def add_section(self, section: Section):
        if not self.chapters:
            default_chapter = Chapter(title=self.title, sections=[], number=1)
            self.chapters.append(default_chapter)
        self.chapters[-1].sections.append(section)

    def aggregate_sentiment(self):
        sentiments = [chapter.aggregate_sentiment() for chapter in self.chapters]
        return sum(sentiments) / len(sentiments) if sentiments else 0

    def aggregate_readability(self):
        readabilities = [chapter.aggregate_readability() for chapter in self.chapters]
        return sum(readabilities) / len(readabilities) if readabilities else 0

    def aggregate_keywords(self):
        keywords = [chapter.aggregate_keywords() for chapter in self.chapters]
        return keywords

    def extract_metadata(self, aspects: list = None):
        metadata = {
            "title": self.title,
            "author": self.author,
            "chapter_count": len(self.chapters),
            "created_date": self.created_date
        }
        if aspects:
            if 'sentiment' in aspects:
                metadata["document_sentiment"] = self.aggregate_sentiment()
            if 'readability' in aspects:
                metadata["document_readability"] = self.aggregate_readability()
            if 'keywords' in aspects:
                metadata["document_keywords"] = self.aggregate_keywords()
        return metadata

    def get_entities(self):
        """
        Concrete implementation of get_entities.
        Collects entities from each chapter.
        """
        all_entities = []
        for chapter in self.chapters:
            if hasattr(chapter, "get_entities"):
                all_entities.extend(chapter.get_entities())
        return all_entities

    def to_text(self):
        """
        Converts the document into the desired formatted string.
        Format:
          Document Title: <title>
          Extracted Paragraph: Author: <author> Created Date: <formatted date>
          New Chapter: <chapter title>
          Extracted Paragraph: <chapter-level paragraph text> (if any)
          New Section under Chapter <number>: <chapter title>: <section title>
          Extracted Paragraph: <section paragraph text>
        """
        lines = []
        # Document metadata.
        lines.append(f"Document Title: {self.title}")
        lines.append("\n")
        lines.append(f"Author: {self.author}")
        lines.append("\n")
        # created_str = self.created_date.strftime("%B %d, %Y") if self.created_date else ""
        # lines.append(f"Extracted Paragraph: Author: {self.author} Created Date: {created_str}")
        # lines.append("\n")

        # Process each chapter.
        for chapter in self.chapters:
            lines.append(f"New Chapter: {chapter.title}")
            lines.append("\n")
            # Print chapter-level paragraphs if available.
            if hasattr(chapter, "paragraphs") and chapter.paragraphs:
                for para in chapter.paragraphs:
                    lines.append(f"Extracted Paragraph: {para.text}")
                    lines.append("\n")
            # Then print each section.
            for section in chapter.sections:
                lines.append(f"New Section under Chapter: {chapter.title}: {section.title}")
                lines.append("\n")
                for para in section.content:
                    lines.append(f"Extracted Paragraph: {para.text}")
                    lines.append("\n")
        lines.append(f"{self.images}")
        lines.append(f"table content: {self.tables}")
        lines.append("\n")
        lines.append(f"image_content: {self.image_content} ")
        return "\n".join(lines)

    def print_content(self, depth=0, is_child=False):
        """
        Generates structured content of the document.

        Args:
            depth (int): The depth of the hierarchy for indentation.
            is_child (bool): Whether the current document is a child document.

        Returns:
            str: The structured content as a string.
        """
        output = []

        # Print chapters and sections
        for chapter in self.chapters:
            output.append(f"{'  ' * depth}Chapter: {chapter.title}")
            for section in chapter.sections:
                output.append(f"{'  ' * depth}  Section: {section.title}")

                for content in section.content:
                    if isinstance(content, Paragraph):
                        output.append(f"{'  ' * depth}    Paragraph: {content.text}")

                    elif isinstance(content, Table):
                        output.append(f"{'  ' * depth}    Table: {content.headers}")
                        for row in content.data:
                            output.append(f"{'  ' * depth}      Row: {row}")

                    elif isinstance(content, Image) and content.ocr_data:
                        ocr_text = content.ocr_data.get("ocr_text", "No OCR Text Extracted")
                        output.append(f"{'  ' * depth}    Extracted Text: {ocr_text}")

                    elif isinstance(content, Hyperlink):
                        hyperlink_text = content.anchor_text or "No text available"
                        output.append(f"{'  ' * depth}    Hyperlink: {content.url} (Text: {hyperlink_text})")

        # Recursively validate child documents
        if hasattr(self, "child_documents") and self.child_documents:
            output.append(f"{'  ' * depth}Linked Documents:")
            for child_doc_content in self.child_documents:
                if isinstance(child_doc_content, Document):
                    child_output = child_doc_content.print_content(depth + 1, is_child=True)
                    output.append(child_output)
                elif isinstance(child_doc_content, str):
                    output.append(f"{'  ' * (depth + 1)}{child_doc_content}")

        return '\n'.join(output)

    def to_dict(self):
        """Convert Document to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "language": self.language,
            "translator": self.translator,
            "description": self.description,
            "url": self.url,
            "chapters": [chapter.to_dict() if hasattr(chapter, 'to_dict') else str(chapter) for chapter in self.chapters],
            "images": self.images,
            "tables": self.tables,
            "image_content": self.image_content,
            "child_documents": [doc.to_dict() if hasattr(doc, 'to_dict') else str(doc) for doc in self.child_documents],
            "caption": self.caption,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }

    def __repr__(self):
        return (f"Document(title='{self.title}', author='{self.author}', "
                f"created_date='{self.created_date}', chapters='{self.chapters}', "
                f"images='{self.images}', tables='{self.tables}', image_content='{self.image_content}')")
