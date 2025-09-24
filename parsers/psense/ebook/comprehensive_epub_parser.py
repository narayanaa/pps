"""
Comprehensive EPUB Parser Implementation

This module provides a full-featured EPUB parser that extracts:
- Complete metadata (Dublin Core and custom)
- Table of contents with hierarchy
- Chapter structure with proper nesting
- Images with OCR processing
- Annotations and bookmarks
- Font and styling information
- Cross-references and links
"""

from __future__ import annotations
import os
import zipfile
import tempfile
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import unquote

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString
from PIL import Image as PILImage

from doc.psense.document.document_parser import DocumentParser
from doc.psense.document.document import Document
from doc.psense.document.chapter import Chapter
from doc.psense.document.section import Section
from doc.psense.document.paragraph import Paragraph
from doc.psense.document.table import Table
from doc.psense.document.image import Image
from doc.psense.document.hyperlink import Hyperlink
from doc.psense.document.advanced_content import Formula, InteractiveElement, Annotation
from doc.psense.document.advanced_content import FormulaNotation, InteractionType, AnnotationType

logger = logging.getLogger(__name__)


@dataclass
class EPUBMetadata:
    """Comprehensive EPUB metadata container."""
    title: str
    author: List[str]
    language: str
    publisher: Optional[str] = None
    description: Optional[str] = None
    subject: List[str] = None
    date: Optional[str] = None
    rights: Optional[str] = None
    identifier: Optional[str] = None
    contributor: List[str] = None
    coverage: Optional[str] = None
    format: str = "EPUB"
    relation: Optional[str] = None
    source: Optional[str] = None
    type: Optional[str] = None
    custom_metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.subject is None:
            self.subject = []
        if self.contributor is None:
            self.contributor = []
        if self.custom_metadata is None:
            self.custom_metadata = {}


@dataclass
class TOCEntry:
    """Table of Contents entry with hierarchy support."""
    title: str
    href: str
    level: int = 0
    children: List['TOCEntry'] = None
    play_order: int = 0

    def __post_init__(self):
        if self.children is None:
            self.children = []


class ComprehensiveEPUBParser(DocumentParser):
    """
    Full-featured EPUB parser with advanced capabilities.
    
    Features:
    - Complete Dublin Core metadata extraction
    - Hierarchical table of contents processing
    - Chapter and section structure preservation
    - Image extraction with optional OCR
    - Font and styling analysis
    - Cross-reference resolution
    - Annotation and bookmark support
    """

    def __init__(self, extract_images: bool = True, perform_ocr: bool = False,
                 preserve_styling: bool = True, extract_annotations: bool = True):
        super().__init__()
        self.extract_images = extract_images
        self.perform_ocr = perform_ocr
        self.preserve_styling = preserve_styling
        self.extract_annotations = extract_annotations
        
        # Initialize OCR capability if requested
        self.ocr_available = False
        if perform_ocr:
            try:
                import pytesseract
                import cv2
                self.ocr_available = True
                logger.info("OCR capabilities enabled")
            except ImportError:
                logger.warning("OCR libraries not available, OCR disabled")

    def parse(self, filepath: str) -> Document:
        """Parse EPUB file into comprehensive Document structure."""
        try:
            book = epub.read_epub(filepath)
            logger.info(f"Starting comprehensive EPUB parsing: {filepath}")
            
            # Extract comprehensive metadata
            metadata = self._extract_comprehensive_metadata(book)
            
            # Create document with rich metadata
            document = Document(
                title=metadata.title,
                author=metadata.author[0] if metadata.author else None,
                language=metadata.language,
                created_date=metadata.date,
                description=metadata.description,
                url=filepath
            )
            
            # Add comprehensive metadata to document cache
            document.cache['epub_metadata'] = metadata.__dict__
            
            # Extract and process table of contents
            toc_structure = self._extract_table_of_contents(book)
            document.cache['table_of_contents'] = [entry.__dict__ for entry in toc_structure]
            
            # Process all document items
            document_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
            image_items = list(book.get_items_of_type(ebooklib.ITEM_IMAGE))
            
            logger.info(f"Found {len(document_items)} document items, {len(image_items)} images")
            
            # Extract and process images if requested
            if self.extract_images and image_items:
                self._process_images(image_items, document)
            
            # Process document content with TOC guidance
            self._process_document_content(document_items, toc_structure, document, book)
            
            # Extract fonts and styling information
            if self.preserve_styling:
                self._extract_styling_information(book, document)
            
            # Extract annotations and bookmarks
            if self.extract_annotations:
                self._extract_annotations(book, document)
            
            # Post-process and validate structure
            self._post_process_document(document)
            
            logger.info(f"EPUB parsing completed: {len(document.chapters)} chapters extracted")
            return document
            
        except Exception as e:
            logger.error(f"EPUB parsing failed: {str(e)}")
            # Return minimal document with error information
            return Document(
                title=f"EPUB Parse Error: {Path(filepath).name}",
                description=f"Parsing failed: {str(e)}",
                url=filepath
            )

    def _extract_comprehensive_metadata(self, book: epub.EpubBook) -> EPUBMetadata:
        """Extract complete Dublin Core and custom metadata."""
        def get_metadata_value(namespace: str, name: str) -> List[str]:
            metadata = book.get_metadata(namespace, name)
            return [item[0] for item in metadata] if metadata else []

        def get_first_metadata(namespace: str, name: str) -> Optional[str]:
            values = get_metadata_value(namespace, name)
            return values[0] if values else None

        # Extract Dublin Core metadata
        title = get_first_metadata('DC', 'title') or "Unknown Title"
        author = get_metadata_value('DC', 'creator')
        language = get_first_metadata('DC', 'language') or "en"
        publisher = get_first_metadata('DC', 'publisher')
        description = get_first_metadata('DC', 'description')
        subject = get_metadata_value('DC', 'subject')
        date = get_first_metadata('DC', 'date')
        rights = get_first_metadata('DC', 'rights')
        identifier = get_first_metadata('DC', 'identifier')
        contributor = get_metadata_value('DC', 'contributor')
        coverage = get_first_metadata('DC', 'coverage')
        relation = get_first_metadata('DC', 'relation')
        source = get_first_metadata('DC', 'source')
        type_info = get_first_metadata('DC', 'type')

        # Extract custom metadata
        custom_metadata = {}
        for namespace in book.metadata:
            if namespace not in ['DC']:  # Skip Dublin Core
                custom_metadata[namespace] = {}
                for key, items in book.metadata[namespace].items():
                    custom_metadata[namespace][key] = [item[0] for item in items]

        return EPUBMetadata(
            title=title,
            author=author,
            language=language,
            publisher=publisher,
            description=description,
            subject=subject,
            date=date,
            rights=rights,
            identifier=identifier,
            contributor=contributor,
            coverage=coverage,
            relation=relation,
            source=source,
            type=type_info,
            custom_metadata=custom_metadata
        )

    def _extract_table_of_contents(self, book: epub.EpubBook) -> List[TOCEntry]:
        """Extract hierarchical table of contents."""
        toc_entries = []
        
        def process_toc_item(item, level=0, play_order=0):
            if isinstance(item, tuple):
                # This is a section (title, list of items)
                section_title, section_items = item
                toc_entry = TOCEntry(
                    title=section_title,
                    href="",  # Section headers don't have direct links
                    level=level,
                    play_order=play_order
                )
                
                play_order += 1
                for sub_item in section_items:
                    child_entry, play_order = process_toc_item(sub_item, level + 1, play_order)
                    toc_entry.children.append(child_entry)
                
                return toc_entry, play_order
            
            elif hasattr(item, 'title') and hasattr(item, 'href'):
                # This is a direct TOC item
                return TOCEntry(
                    title=item.title,
                    href=item.href,
                    level=level,
                    play_order=play_order
                ), play_order + 1
            
            elif isinstance(item, str):
                # Handle string items
                return TOCEntry(
                    title=item,
                    href="",
                    level=level,
                    play_order=play_order
                ), play_order + 1
            
            else:
                # Fallback for unknown item types
                return TOCEntry(
                    title=str(item),
                    href="",
                    level=level,
                    play_order=play_order
                ), play_order + 1

        # Process table of contents
        play_order = 0
        for toc_item in book.toc:
            entry, play_order = process_toc_item(toc_item, 0, play_order)
            toc_entries.append(entry)

        return toc_entries

    def _process_images(self, image_items: List, document: Document) -> None:
        """Process and extract images from EPUB."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            for image_item in image_items:
                try:
                    # Save image to temporary file
                    image_filename = os.path.basename(image_item.file_name)
                    image_path = os.path.join(temp_dir, image_filename)
                    
                    with open(image_path, 'wb') as img_file:
                        img_file.write(image_item.get_content())
                    
                    # Create Image object
                    image_obj = Image(
                        file_path=image_path,
                        caption=f"Image from EPUB: {image_filename}",
                        alt_text=f"Extracted image: {image_filename}"
                    )
                    
                    # Perform OCR if enabled and available
                    if self.perform_ocr and self.ocr_available:
                        try:
                            import pytesseract
                            from PIL import Image as PILImage
                            
                            pil_img = PILImage.open(image_path)
                            ocr_text = pytesseract.image_to_string(pil_img)
                            if ocr_text.strip():
                                image_obj.cache['ocr_text'] = ocr_text.strip()
                        except Exception as e:
                            logger.warning(f"OCR failed for {image_filename}: {e}")
                    
                    # Add to document images
                    document.images.append(image_obj)
                    
                except Exception as e:
                    logger.warning(f"Failed to process image {image_item.file_name}: {e}")
        
        finally:
            # Cleanup temporary directory
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _process_document_content(self, document_items: List, toc_structure: List[TOCEntry], 
                                document: Document, book: epub.EpubBook) -> None:
        """Process document content with TOC guidance."""
        
        # Create mapping of href to TOC entries
        href_to_toc = {}
        def map_toc_entries(entries, parent_level=0):
            for entry in entries:
                if entry.href:
                    # Clean href (remove fragments)
                    clean_href = entry.href.split('#')[0]
                    href_to_toc[clean_href] = entry
                map_toc_entries(entry.children, parent_level + 1)
        
        map_toc_entries(toc_structure)
        
        current_chapter = None
        current_section = None
        
        for item in document_items:
            try:
                # Get item filename for TOC matching
                item_filename = os.path.basename(item.file_name)
                
                # Parse HTML content
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                
                # Check if this item corresponds to a TOC entry
                toc_entry = href_to_toc.get(item_filename)
                
                # If this is a new chapter based on TOC
                if toc_entry and toc_entry.level <= 1:
                    current_chapter = Chapter(
                        title=toc_entry.title,
                        sections=[],
                        number=len(document.chapters) + 1
                    )
                    document.add_chapter(current_chapter)
                    current_section = None
                    logger.info(f"Created chapter: {toc_entry.title}")
                
                # Process HTML content
                self._process_html_content(soup, current_chapter, current_section, document, item.file_name)
                
            except Exception as e:
                logger.warning(f"Failed to process document item {item.file_name}: {e}")

    def _process_html_content(self, soup: BeautifulSoup, current_chapter: Optional[Chapter], 
                            current_section: Optional[Section], document: Document, source_file: str) -> Tuple[Optional[Chapter], Optional[Section]]:
        """Process HTML content and extract structured elements."""
        
        # Process all relevant HTML elements
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 
                                    'table', 'img', 'a', 'blockquote', 'pre', 'code']):
            
            # Handle headings
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                heading_level = int(element.name[1])
                heading_text = element.get_text().strip()
                
                if not heading_text:
                    continue
                
                # Create chapter for h1-h2, section for h3-h6
                if heading_level <= 2:
                    current_chapter = Chapter(
                        title=heading_text,
                        sections=[],
                        number=len(document.chapters) + 1
                    )
                    document.add_chapter(current_chapter)
                    current_section = None
                else:
                    if not current_chapter:
                        current_chapter = Chapter(
                            title="Main Content",
                            sections=[],
                            number=len(document.chapters) + 1
                        )
                        document.add_chapter(current_chapter)
                    
                    current_section = Section(
                        title=heading_text,
                        content=[],
                        level=heading_level - 2
                    )
                    current_chapter.sections.append(current_section)
            
            # Handle paragraphs and text content
            elif element.name in ['p', 'div']:
                text_content = element.get_text().strip()
                if text_content:
                    # Check for mathematical formulas
                    if self._contains_math(element):
                        formula = self._extract_formula(element)
                        if formula:
                            self._add_content_to_structure(formula, current_chapter, current_section, document)
                    else:
                        paragraph = Paragraph(text=text_content)
                        
                        # Add styling information if available
                        if self.preserve_styling and element.get('style'):
                            paragraph.cache['html_style'] = element.get('style')
                        
                        self._add_content_to_structure(paragraph, current_chapter, current_section, document)
            
            # Handle tables
            elif element.name == 'table':
                table_obj = self._extract_table(element)
                if table_obj:
                    self._add_content_to_structure(table_obj, current_chapter, current_section, document)
            
            # Handle images
            elif element.name == 'img':
                image_obj = self._extract_image_reference(element, source_file)
                if image_obj:
                    self._add_content_to_structure(image_obj, current_chapter, current_section, document)
            
            # Handle links
            elif element.name == 'a':
                link_obj = self._extract_link(element)
                if link_obj:
                    self._add_content_to_structure(link_obj, current_chapter, current_section, document)
            
            # Handle code blocks
            elif element.name in ['pre', 'code']:
                code_text = element.get_text()
                if code_text.strip():
                    # Create a specialized paragraph for code
                    code_paragraph = Paragraph(text=code_text)
                    code_paragraph.cache['content_type'] = 'code'
                    code_paragraph.cache['language'] = element.get('class', [''])[0] if element.get('class') else 'text'
                    self._add_content_to_structure(code_paragraph, current_chapter, current_section, document)
        
        return current_chapter, current_section

    def _add_content_to_structure(self, content_obj, current_chapter: Optional[Chapter], 
                                current_section: Optional[Section], document: Document) -> None:
        """Add content to appropriate document structure level."""
        if current_section:
            current_section.content.append(content_obj)
        elif current_chapter:
            # Create default section if none exists
            if not current_chapter.sections:
                default_section = Section(title="Content", content=[], level=1)
                current_chapter.sections.append(default_section)
            current_chapter.sections[0].content.append(content_obj)
        else:
            # Create standalone chapter for orphaned content
            standalone_chapter = Chapter(
                title="Standalone Content",
                sections=[Section(title="Content", content=[content_obj], level=1)],
                number=len(document.chapters) + 1
            )
            document.add_chapter(standalone_chapter)

    def _contains_math(self, element) -> bool:
        """Check if element contains mathematical notation."""
        text = element.get_text()
        math_indicators = ['\\(', '\\)', '\\[', '\\]', '$', '$$', '<math>', '</math>']
        return any(indicator in text for indicator in math_indicators)

    def _extract_formula(self, element) -> Optional[Formula]:
        """Extract mathematical formula from element."""
        text = element.get_text()
        
        # Detect notation type
        if '<math>' in str(element):
            # MathML
            mathml_content = str(element.find('math')) if element.find('math') else text
            return Formula(
                formula=mathml_content,
                notation=FormulaNotation.MATHML,
                inline='display' not in element.get('class', [])
            )
        elif '\\(' in text and '\\)' in text:
            # Inline LaTeX
            formula_text = text.split('\\(')[1].split('\\)')[0]
            return Formula(
                formula=formula_text,
                notation=FormulaNotation.LATEX,
                inline=True
            )
        elif '\\[' in text and '\\]' in text:
            # Display LaTeX
            formula_text = text.split('\\[')[1].split('\\]')[0]
            return Formula(
                formula=formula_text,
                notation=FormulaNotation.LATEX,
                inline=False
            )
        elif '$' in text:
            # LaTeX with dollar signs
            if '$$' in text:
                formula_text = text.split('$$')[1]
                return Formula(
                    formula=formula_text,
                    notation=FormulaNotation.LATEX,
                    inline=False
                )
            else:
                formula_text = text.split('$')[1]
                return Formula(
                    formula=formula_text,
                    notation=FormulaNotation.LATEX,
                    inline=True
                )
        
        return None

    def _extract_table(self, table_element) -> Optional[Table]:
        """Extract table data with headers and proper structure."""
        try:
            rows = []
            headers = []
            
            # Extract headers
            thead = table_element.find('thead')
            if thead:
                header_row = thead.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
            
            # Extract data rows
            tbody = table_element.find('tbody') or table_element
            for row in tbody.find_all('tr'):
                row_data = [td.get_text().strip() for td in row.find_all(['td', 'th'])]
                if row_data:
                    rows.append(row_data)
            
            # If no headers found but we have data, use first row as headers
            if not headers and rows:
                headers = rows[0]
                rows = rows[1:]
            
            if rows or headers:
                caption = ""
                caption_element = table_element.find('caption')
                if caption_element:
                    caption = caption_element.get_text().strip()
                
                return Table(
                    data=rows,
                    headers=headers,
                    caption=caption
                )
        
        except Exception as e:
            logger.warning(f"Failed to extract table: {e}")
        
        return None

    def _extract_image_reference(self, img_element, source_file: str) -> Optional[Image]:
        """Extract image reference and metadata."""
        src = img_element.get('src')
        if not src:
            return None
        
        alt_text = img_element.get('alt', '')
        title = img_element.get('title', '')
        
        # Try to find corresponding image in document images by filename
        image_filename = os.path.basename(src)
        
        return Image(
            file_path=src,
            caption=title or alt_text or f"Image: {image_filename}",
            alt_text=alt_text,
            metadata={'source_file': source_file, 'original_src': src}
        )

    def _extract_link(self, link_element) -> Optional[Hyperlink]:
        """Extract hyperlink with metadata."""
        href = link_element.get('href')
        if not href:
            return None
        
        text = link_element.get_text().strip()
        title = link_element.get('title', '')
        
        # Determine link type
        link_type = "external"
        if href.startswith('#'):
            link_type = "internal_anchor"
        elif href.startswith('mailto:'):
            link_type = "email"
        elif not href.startswith(('http://', 'https://', 'ftp://')):
            link_type = "internal_document"
        
        return Hyperlink(
            url=href,
            text=text,
            title=title,
            metadata={'link_type': link_type}
        )

    def _extract_styling_information(self, book: epub.EpubBook, document: Document) -> None:
        """Extract CSS and styling information."""
        styling_info = {
            'css_files': [],
            'embedded_styles': [],
            'font_families': set(),
            'color_schemes': set()
        }
        
        # Extract CSS files
        for item in book.get_items_of_type(ebooklib.ITEM_STYLE):
            css_content = item.get_content().decode('utf-8', errors='ignore')
            styling_info['css_files'].append({
                'filename': item.file_name,
                'content': css_content
            })
            
            # Extract font families and colors (basic parsing)
            import re
            fonts = re.findall(r'font-family:\s*([^;]+)', css_content)
            colors = re.findall(r'color:\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}|\w+)', css_content)
            
            styling_info['font_families'].update(font.strip() for font in fonts)
            styling_info['color_schemes'].update(color.strip() for color in colors)
        
        # Convert sets to lists for JSON serialization
        styling_info['font_families'] = list(styling_info['font_families'])
        styling_info['color_schemes'] = list(styling_info['color_schemes'])
        
        document.cache['styling_information'] = styling_info

    def _extract_annotations(self, book: epub.EpubBook, document: Document) -> None:
        """Extract annotations and bookmarks if present."""
        annotations = []
        
        # Look for annotation files (this is highly dependent on EPUB reader implementation)
        # Most EPUBs don't contain reader annotations, but we can look for embedded notes
        
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_body_content(), 'html.parser')
            
            # Look for common annotation patterns
            for note_element in soup.find_all(['aside', 'div'], class_=['note', 'annotation', 'comment']):
                note_text = note_element.get_text().strip()
                if note_text:
                    annotation = Annotation(
                        content=note_text,
                        annotation_type=AnnotationType.NOTE,
                        target_element_id=item.file_name
                    )
                    annotations.append(annotation)
            
            # Look for footnotes as annotations
            for footnote in soup.find_all('a', href=lambda x: x and '#' in x):
                if footnote.get_text().strip():
                    annotation = Annotation(
                        content=footnote.get_text().strip(),
                        annotation_type=AnnotationType.BOOKMARK,
                        target_element_id=footnote.get('href', ''),
                        position={'href': footnote.get('href')}
                    )
                    annotations.append(annotation)
        
        if annotations:
            document.cache['extracted_annotations'] = [ann.to_dict() for ann in annotations]

    def _post_process_document(self, document: Document) -> None:
        """Post-process document to ensure proper structure and metadata."""
        
        # Ensure document has at least one chapter
        if not document.chapters:
            default_chapter = Chapter(
                title="Main Content",
                sections=[Section(
                    title="Content",
                    content=[Paragraph("No structured content found in EPUB.")],
                    level=1
                )],
                number=1
            )
            document.add_chapter(default_chapter)
        
        # Add processing statistics
        stats = {
            'total_chapters': len(document.chapters),
            'total_sections': sum(len(chapter.sections) for chapter in document.chapters),
            'total_paragraphs': self._count_paragraphs(document),
            'total_images': len(document.images),
            'has_table_of_contents': 'table_of_contents' in document.cache,
            'has_styling_info': 'styling_information' in document.cache,
            'processing_timestamp': datetime.now().isoformat()
        }
        
        document.cache['processing_statistics'] = stats
        logger.info(f"Document processing complete: {stats}")

    def _count_paragraphs(self, document: Document) -> int:
        """Count total paragraphs in document."""
        count = 0
        for chapter in document.chapters:
            for section in chapter.sections:
                count += sum(1 for content in section.content 
                           if isinstance(content, Paragraph))
        return count


# Utility functions

def parse_epub_file(filepath: str, **kwargs) -> Document:
    """Convenience function to parse EPUB file with default settings."""
    parser = ComprehensiveEPUBParser(**kwargs)
    return parser.parse(filepath)


def extract_epub_metadata_only(filepath: str) -> Dict[str, Any]:
    """Extract only metadata from EPUB file without full parsing."""
    try:
        book = epub.read_epub(filepath)
        parser = ComprehensiveEPUBParser()
        metadata = parser._extract_comprehensive_metadata(book)
        return metadata.__dict__
    except Exception as e:
        logger.error(f"Metadata extraction failed: {e}")
        return {"error": str(e)}


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python comprehensive_epub_parser.py <epub_file>")
        sys.exit(1)
    
    epub_file = sys.argv[1]
    parser = ComprehensiveEPUBParser(
        extract_images=True,
        perform_ocr=False,  # Set to True if OCR libraries are available
        preserve_styling=True,
        extract_annotations=True
    )
    
    document = parser.parse(epub_file)
    
    print(f"Parsed EPUB: {document.title}")
    print(f"Chapters: {len(document.chapters)}")
    print(f"Images: {len(document.images)}")
    print("\nFirst few chapters:")
    for i, chapter in enumerate(document.chapters[:3]):
        print(f"  {i+1}. {chapter.title} ({len(chapter.sections)} sections)")