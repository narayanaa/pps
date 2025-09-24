"""
DOCX Parser Implementation

Features:
1. Tables: The parser loops through the tables found in the DOCX document and creates a Table object
   with the extracted data, which is appended to the content of the current section or chapter.
2. Images: Similarly, the parser looks for any images (using docx.part.rels) and creates an
   Image object with metadata like file path, caption, and alt text, and
   appends them to the current section or chapter.
"""
import mimetypes
import os
import tempfile
import zipfile
from datetime import datetime
from typing import List, Optional

# Handle the python-docx import issue
try:
    from docx import Document as DocxDocument  # Importing python-docx Document
except ImportError:
    # Fallback for environments where python-docx might have import issues
    DocxDocument = None

from doc.psense.data_element import DataElement
from doc.psense.document.document import Document
from doc.psense.document.document_parser import DocumentParser
from doc.psense.document.table import Table
from doc.psense.document.paragraph import Paragraph
from doc.psense.document.image import Image
from doc.psense.document.section import Section
from doc.psense.document.chapter import Chapter
from doc.psense.document.video import Video


class DOCXParser(DocumentParser):
    """DOCX Parser that conforms to unified doc.psense structure"""
    
    def __init__(self):
        if DocxDocument is None:
            raise ImportError("python-docx is not installed or not accessible")
    
    def parse(self, filepath: str) -> Document:
        """Parse DOCX file into unified Document structure"""
        try:
            docx_doc = DocxDocument(filepath)
            
            # Extract document metadata
            title = self._extract_title(docx_doc) or os.path.basename(filepath)
            author = self._extract_author(docx_doc)
            
            # Create unified Document
            document = Document(
                title=title,
                author=author,
                created_date=datetime.now(),
                url=filepath,
                language="English"  # Default, could be enhanced to detect language
            )
            
            # Process document content
            current_chapter = Chapter(
                title="Main Content",
                sections=[],
                number=1
            )
            
            current_section = Section(
                title="Content",
                content=[],
                level=1
            )
            
            # Process paragraphs and other elements
            for element in docx_doc.element.body:
                self._process_element(element, current_section, docx_doc)
            
            # Process tables
            for table in docx_doc.tables:
                table_obj = self._extract_table(table)
                if table_obj:
                    current_section.content.append(table_obj)
            
            # Process images
            images = self._extract_images(docx_doc, filepath)
            current_section.content.extend(images)
            
            # Add section to chapter and chapter to document
            current_chapter.sections.append(current_section)
            document.add_chapter(current_chapter)
            
            return document
            
        except Exception as e:
            # Create minimal document with error information
            error_doc = Document(
                title=f"Error parsing {os.path.basename(filepath)}",
                author="DOCX Parser",
                created_date=datetime.now(),
                url=filepath,
                description=f"Error: {str(e)}"
            )
            
            error_chapter = Chapter(
                title="Error",
                sections=[Section(
                    title="Parsing Error",
                    content=[Paragraph(f"Failed to parse DOCX file: {str(e)}")],
                    level=1
                )],
                number=1
            )
            error_doc.add_chapter(error_chapter)
            return error_doc
    
    def _extract_title(self, docx_doc: DocxDocument) -> Optional[str]:
        """Extract document title from DOCX metadata or first heading"""
        try:
            # Try to get title from document properties
            if hasattr(docx_doc.core_properties, 'title') and docx_doc.core_properties.title:
                return docx_doc.core_properties.title
            
            # Try to get title from first heading
            for paragraph in docx_doc.paragraphs:
                if paragraph.style.name.startswith('Heading'):
                    return paragraph.text.strip()
                    
        except Exception:
            pass
        return None
    
    def _extract_author(self, docx_doc: DocxDocument) -> Optional[str]:
        """Extract document author from DOCX metadata"""
        try:
            if hasattr(docx_doc.core_properties, 'author') and docx_doc.core_properties.author:
                return docx_doc.core_properties.author
        except Exception:
            pass
        return None
    
    def _process_element(self, element, section: Section, docx_doc: DocxDocument):
        """Process individual DOCX elements"""
        try:
            # Process paragraphs
            if element.tag.endswith('p'):  # Paragraph
                paragraph_text = self._extract_paragraph_text(element)
                if paragraph_text.strip():
                    paragraph = Paragraph(
                        text=paragraph_text,
                        style=self._get_paragraph_style(element)
                    )
                    section.content.append(paragraph)
                    
        except Exception as e:
            # Add error paragraph for debugging
            error_para = Paragraph(f"Error processing element: {str(e)}")
            section.content.append(error_para)
    
    def _extract_paragraph_text(self, element) -> str:
        """Extract text from paragraph element"""
        try:
            text_content = []
            for run in element.findall('.//w:t', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}):
                if run.text:
                    text_content.append(run.text)
            return ' '.join(text_content)
        except Exception:
            return ""
    
    def _get_paragraph_style(self, element) -> str:
        """Get paragraph style information"""
        try:
            # Extract style information if available
            style_elements = element.findall('.//w:pStyle', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
            if style_elements:
                return style_elements[0].get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'Normal')
        except Exception:
            pass
        return 'Normal'
    
    def _extract_table(self, docx_table) -> Optional[Table]:
        """Extract table data and create Table object"""
        try:
            table_data = []
            headers = []
            
            # Extract table data
            for i, row in enumerate(docx_table.rows):
                row_data = []
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    row_data.append(cell_text)
                
                if i == 0:  # First row as headers
                    headers = row_data
                else:
                    table_data.append(row_data)
            
            if table_data or headers:
                return Table(
                    data=table_data,
                    headers=headers if any(headers) else None,
                    caption="Table from DOCX"
                )
                
        except Exception as e:
            # Return table with error information
            return Table(
                data=[[f"Error extracting table: {str(e)}"]],
                headers=["Error"],
                caption="Table extraction error"
            )
        return None
    
    def _extract_images(self, docx_doc: DocxDocument, filepath: str) -> List[Image]:
        """Extract images from DOCX document"""
        images = []
        
        try:
            # Create temporary directory for extracted images
            temp_dir = tempfile.mkdtemp()
            
            # Extract images from the DOCX file (which is a ZIP)
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                for file_info in zip_ref.filelist:
                    if file_info.filename.startswith('word/media/'):
                        # Extract image to temporary directory
                        zip_ref.extract(file_info, temp_dir)
                        
                        # Create Image object
                        image_path = os.path.join(temp_dir, file_info.filename)
                        
                        # Determine MIME type
                        mime_type, _ = mimetypes.guess_type(image_path)
                        
                        if mime_type and mime_type.startswith('image/'):
                            image = Image(
                                file_path=image_path,
                                caption=f"Image from {os.path.basename(file_info.filename)}",
                                alt_text=f"Extracted from DOCX: {file_info.filename}"
                            )
                            images.append(image)
                            
        except Exception as e:
            # Create error image entry
            error_image = Image(
                file_path="",
                caption="Image extraction error",
                alt_text=f"Failed to extract images: {str(e)}"
            )
            images.append(error_image)
        
        return images


def append_media_to_correct_section(document: Document, media_obj: DataElement):
    """Append media to the correct section."""
    # Ensure we are appending to the correct section, not just the last one
    if document.chapters and document.chapters[-1].sections:
        last_section = document.chapters[-1].sections[-1]
        last_section.content.append(media_obj)
        print(f"Appending {media_obj.__class__.__name__}: {media_obj.caption} to Section: '{last_section.title}'")
    else:
        print(f"Warning: No valid section found to append the media object {media_obj.__class__.__name__}.")


def extract_video_metadata(file):
    """Extract video metadata such as caption and alt text."""
    # Simulate extracting metadata for the video (metadata for media is not always directly accessible)
    caption = f"Caption for {file.split('/')[-1]}"
    alt_text = f"Alt text for {file.split('/')[-1]}"
    return caption, alt_text


def extract_image_metadata(file):
    """Extract image metadata such as caption and alt text."""
    # Simulate extracting metadata from the file (docx doesn't directly store metadata for media)
    caption = f"Caption for {file.split('/')[-1]}"
    alt_text = f"Alt text for {file.split('/')[-1]}"
    return caption, alt_text


def extract_table_caption(docx, table):
    """Extract captions or titles for tables if available in the document."""
    for para in docx.paragraphs:
        if para.text.strip().startswith("Table") and table._element in para._element.iter():
            return para.text.strip()  # Return the table caption
    return ""  # No caption found


def extract_media(filepath: str, document: Document):
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(filepath, 'r') as docx_zip:
            for file in docx_zip.namelist():
                print(f"Extracting {file.title()} with extension {file.split('.')[-1]}")
                if file.startswith('word/media/'):
                    docx_zip.extract(file, temp_dir)
                    media_path = os.path.join(temp_dir, file)

                    # Detect image types and extract metadata
                    if file.endswith(('.png', '.jpeg', '.jpg')):
                        caption, alt_text = extract_image_metadata(file)
                        image_obj = Image(file_path=media_path, caption=caption, alt_text=alt_text)
                        append_media_to_correct_section(document, image_obj)

                    # Detect video types and extract metadata
                    elif file.endswith(('.mp4', '.avi')):
                        caption, alt_text = extract_video_metadata(file)
                        video_obj = Video(file_path=media_path, caption=caption, alt_text=alt_text)
                        append_media_to_correct_section(document, video_obj)

                # Check for embedded objects like videos
                elif file.startswith('word/embeddings/'):
                    print(f"Found embedded object: {file}")
                    docx_zip.extract(file, temp_dir)
                    embedded_path = os.path.join(temp_dir, file)

                    # Check if the embedded object is a video
                    if embedded_path.endswith('.mp4'):
                        caption, alt_text = extract_video_metadata(file)
                        video_obj = Video(file_path=embedded_path, caption=caption, alt_text=alt_text)
                        append_media_to_correct_section(document, video_obj)


class DOCXParser(DocumentParser):
    def parse(self, filepath: str) -> Document:
        docx = DocxDocument(filepath)  # Use python-docx's Document to read the file
        document_title = docx.paragraphs[0].text if docx.paragraphs else "Untitled Document"
        document = Document(title=document_title, created_date=datetime.now())  # Your Document class

        current_chapter = None
        current_section = None
        chapter_count = 0

        for para in docx.paragraphs:
            if para.style.name.startswith('Heading 1') and para.text.strip():
                if current_chapter:
                    document.add_chapter(current_chapter)
                print(f"Creating Chapter: {para.text}")
                current_chapter = Chapter(para.text, [], chapter_count + 1)
                current_section = None

            elif para.style.name.startswith('Heading 2') and para.text.strip():
                if current_section and current_chapter:
                    current_chapter.sections.append(current_section)
                print(f"Creating Section: {para.text} under Chapter: {current_chapter.title}")
                current_section = Section(para.text, [])

            else:
                # Add paragraphs to the current section
                if current_section:
                    current_section.content.append(Paragraph(para.text))
                else:
                    if current_chapter:
                        current_chapter.sections.append(Section("Uncategorized", [Paragraph(para.text)]))

        # Add any remaining sections and chapters
        if current_section and current_chapter:
            current_chapter.sections.append(current_section)
        if current_chapter:
            document.add_chapter(current_chapter)

        # Adding tables with captions (if available)
        for table in docx.tables:
            print(f"\\n The table is:\n {table}")
            table_data = [[cell.text for cell in row.cells] for row in table.rows]
            table_caption = extract_table_caption(docx, table)  # Extract table captions
            table_obj = Table(table_data, caption=table_caption)
            if current_section:
                current_section.content.append(table_obj)
            else:
                if document.chapters and document.chapters[-1].sections:
                    document.chapters[-1].sections[-1].content.append(table_obj)

        # Extract images and videos from the .docx file
        extract_media(filepath, document)
        print(f"Returning the document from the DOCX file...")
        return document
