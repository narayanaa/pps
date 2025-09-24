import os
import ebooklib
from doc.psense.document.document_parser import DocumentParser
from doc.psense.document.document import Document
from doc.psense.document.chapter import Chapter
from doc.psense.document.image import Image
from doc.psense.document.paragraph import Paragraph
from doc.psense.document.section import Section
from doc.psense.document.table import Table

from ebooklib import epub
from bs4 import BeautifulSoup
from PIL import Image as PILImage  # For handling images in eBooks

from parsers.psense.ebook.footnote_epub import Footnote


class EBookParser(DocumentParser):
    def parse(self, filepath: str) -> Document:
        book = epub.read_epub(filepath)

        # Start by creating a document object with the book title
        title_metadata = book.get_metadata('DC', 'title')
        title = title_metadata[0][0] if title_metadata else "Unknown Title"
        document = Document(title=title)

        # Extract description and metadata like author, release date, etc.
        description_metadata = book.get_metadata('DC', 'description')
        description = description_metadata[0][0] if description_metadata else "No Description Available"
        document.description = description

        # Extracting metadata (author, translator, language, etc.)
        metadata = {
            "author": book.get_metadata('DC', 'creator'),
            "language": book.get_metadata('DC', 'language'),
            "release_date": book.get_metadata('DC', 'date'),
            "translator": book.get_metadata('DC', 'contributor')
        }

        document.author = metadata['author']
        document.language = metadata['language']
        document.created_date = metadata['release_date']
        document.translator = metadata['translator']

        current_chapter = None
        current_section = None
        footnotes = []
        title_recognized = False  # Flag to ensure we recognize the title only once

        print(f"Total items in the eBook: {len(book.items)}")

        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_body_content(), 'html.parser')

            # Process HTML content (chapters, sections, paragraphs, etc.)
            for tag in soup.find_all(['h1', 'h2', 'p', 'table', 'img', 'sup', 'a']):

                # Recognize and skip the title (h1) if it's the first one we encounter
                if tag.name == 'h1' and not title_recognized and self.is_title(tag):
                    title_recognized = True  # Ensure title is recognized only once
                    continue  # Skip processing this title

                # Recognize chapters from 'h1' tags, but only after the title
                if tag.name == 'h1' and title_recognized:
                    # Close off previous chapter and section, if applicable
                    current_section = None  # Reset section as we are in a new chapter
                    current_chapter = Chapter(tag.get_text().strip(), [], len(document.chapters) + 1)
                    document.add_chapter(current_chapter)
                    print(f"Creating Chapter: {current_chapter.title}")

                # Recognize sections from 'h2' tags
                elif tag.name == 'h2':
                    if current_chapter:
                        current_section = Section(tag.get_text().strip(), [])
                        current_chapter.sections.append(current_section)
                        print(f"Creating Section: {current_section.title} under Chapter: {current_chapter.title}")
                    else:
                        # Create a default chapter if sections appear before any chapter
                        current_chapter = Chapter("Default Chapter", [], len(document.chapters) + 1)
                        document.add_chapter(current_chapter)
                        current_section = Section(tag.get_text().strip(), [])
                        current_chapter.sections.append(current_section)
                        print(f"Creating Default Chapter and Section: {current_section.title}")

                # Handle paragraphs
                elif tag.name == 'p':
                    paragraph = Paragraph(tag.get_text().strip())
                    if current_section:
                        current_section.content.append(paragraph)
                    elif current_chapter:
                        # If there's a chapter but no section, create a default section
                        current_section = Section("General Content", [])
                        current_chapter.sections.append(current_section)
                        current_section.content.append(paragraph)
                    else:
                        # If no chapter exists, add paragraphs as standalone in the document
                        standalone_section = Section("Standalone Content", [paragraph])
                        document.add_section(standalone_section)
                    print(
                        f"Adding Paragraph to Section: {current_section.title if current_section else 'Standalone Content'}")

                # Handle tables
                elif tag.name == 'table':
                    table_data = self.extract_table(tag)
                    if table_data:
                        table_obj = Table(table_data[0], table_data[1:])
                        if current_section:
                            current_section.content.append(table_obj)
                        elif current_chapter:
                            if not current_section:
                                current_section = Section("General Content", [])
                                current_chapter.sections.append(current_section)
                            current_section.content.append(table_obj)
                        else:
                            # Add the table as standalone content
                            standalone_section = Section("Standalone Table", [table_obj])
                            document.add_section(standalone_section)
                        print(
                            f"Adding Table to Section: {current_section.title if current_section else 'Standalone Content'}")

                # Handle images
                elif tag.name == 'img':
                    image_obj = self.extract_image(tag, item.file_name)
                    if image_obj:
                        if current_section:
                            current_section.content.append(image_obj)
                        elif current_chapter:
                            if not current_section:
                                current_section = Section("General Content", [])
                                current_chapter.sections.append(current_section)
                            current_section.content.append(image_obj)
                        else:
                            # Add image as standalone content
                            standalone_section = Section("Standalone Image", [image_obj])
                            document.add_section(standalone_section)
                        print(f"Adding Image to Section: "
                              f"{current_section.title if current_section else 'Standalone Content'}")

                # Handle footnotes
                if tag.name == 'a' and 'Footnote' in tag.get_text():
                    footnote_text = tag.get_text().strip()
                    footnote_ref = tag.get('href', '').strip() if tag.get('href') else ''
                    footnote = Footnote(text=footnote_text, reference=footnote_ref)
                    if current_section:
                        current_section.footnotes = footnote
                    elif current_chapter:
                        current_chapter.footnotes = footnote
                    else:
                        document.footnotes = footnote
                    print(f"Detected Footnote: {footnote_text} with reference {footnote_ref}")

        return document

    def is_title(self, tag):
        """Determine if the current 'h1' tag represents the title (based on structure or content)"""
        title_keywords = ["Title", "Prologue", "Introduction"]
        return any(keyword.lower() in tag.get_text().strip().lower() for keyword in title_keywords)

    def extract_table(self, tag):
        """Extract table data from a BeautifulSoup tag"""
        rows = []
        for row in tag.find_all('tr'):
            cols = [col.get_text().strip() for col in row.find_all(['td', 'th'])]
            rows.append(cols)

        if len(rows) > 1 and all(len(row) == len(rows[0]) for row in rows):
            return rows
        return None

    def extract_image(self, tag, item_filename):
        """Extract an image from an HTML tag and return an Image object"""
        img_src = tag['src']
        img_full_path = os.path.join(os.path.dirname(item_filename), img_src)

        if os.path.exists(img_full_path):
            try:
                pil_image = PILImage.open(img_full_path)
                return Image(img_full_path, caption="Extracted Image")
            except Exception as e:
                print(f"Failed to load image: {img_full_path}, error: {e}")
        else:
            print(f"Image not found: {img_full_path}")
        return None


def main():
    epub_file = "C:/Users/Sushil.Das/Downloads/pg12058-images-3.epub"  # Replace with actual ePub path
    ebook_parser = EBookParser()
    parsed_document = ebook_parser.parse(epub_file)
    print(parsed_document)


if __name__ == "__main__":
    main()
