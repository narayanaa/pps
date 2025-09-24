"""
Universal Document Parser Framework
Provides unified interface for parsing multiple document formats
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

from doc.psense.document.document import Document


class BaseDocumentParser(ABC):
    """Abstract base class for all document parsers"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the given file"""
        pass
        
    @abstractmethod
    def parse(self, file_path: str) -> Optional[Document]:
        """Parse the document and return Document structure"""
        pass
        
    @abstractmethod
    def get_supported_extensions(self) -> list:
        """Return list of supported file extensions"""
        pass


class DocumentParserFactory:
    """Factory for creating appropriate document parsers"""
    
    _parsers = {}
    
    @classmethod
    def register_parser(cls, parser_class: type, extensions: list):
        """Register a parser for specific file extensions"""
        for ext in extensions:
            cls._parsers[ext.lower()] = parser_class
    
    @classmethod
    def get_parser(cls, file_path: str, config: Optional[Dict[str, Any]] = None):
        """Get appropriate parser for the file"""
        ext = Path(file_path).suffix.lower()
        if ext in cls._parsers:
            return cls._parsers[ext](config)
        return None
    
    @classmethod
    def parse_document(cls, file_path: str, config: Optional[Dict[str, Any]] = None) -> Optional[Document]:
        """Parse any supported document format"""
        parser = cls.get_parser(file_path, config)
        if parser and parser.can_parse(file_path):
            return parser.parse(file_path)
        return None


class HTMLDocumentParser(BaseDocumentParser):
    """Parser for HTML content (web scraping integration)"""
    
    def can_parse(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in ['.html', '.htm']
    
    def get_supported_extensions(self) -> list:
        return ['.html', '.htm']
    
    def parse(self, file_path: str) -> Optional[Document]:
        """Parse HTML file using existing web scraper logic"""
        try:
            from bs4 import BeautifulSoup
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'lxml')
            
            # Use existing scraper parsing logic
            try:
                from scrapers.psense.web.scraper import WebScraper
                temp_config = {"scraper": {"url": file_path}}
                scraper = WebScraper(temp_config)
                
                return scraper._parse_to_document(soup, file_path)
            except ImportError:
                # Fallback to basic parsing if scraper not available
                print(f"Warning: WebScraper not available, skipping HTML file {file_path}")
                return None
            
        except Exception as e:
            print(f"Error parsing HTML file {file_path}: {e}")
            return None


class MarkdownDocumentParser(BaseDocumentParser):
    """Parser for Markdown files"""
    
    def can_parse(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in ['.md', '.markdown']
    
    def get_supported_extensions(self) -> list:
        return ['.md', '.markdown']
    
    def parse(self, file_path: str) -> Optional[Document]:
        """Parse Markdown file into Document structure"""
        try:
            import re
            from datetime import datetime
            from doc.psense.document.chapter import Chapter
            from doc.psense.document.section import Section
            from doc.psense.document.paragraph import Paragraph
            from doc.psense.document.enhanced_content import CodeBlock
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title from first h1 or filename
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else Path(file_path).stem
            
            doc = Document(title=title, url=file_path, created_date=datetime.now())
            
            # Split content by headers
            sections = re.split(r'^(#{1,6})\s+(.+)$', content, flags=re.MULTILINE)
            
            current_chapter = Chapter("Main", [], number=1)
            doc.add_chapter(current_chapter)
            
            current_section = Section("Content", [])
            current_chapter.sections.append(current_section)
            
            for i in range(1, len(sections), 3):
                if i + 2 < len(sections):
                    header_level = len(sections[i])
                    header_text = sections[i + 1]
                    section_content = sections[i + 2] if i + 2 < len(sections) else ""
                    
                    if header_level == 1:  # New chapter
                        current_chapter = Chapter(header_text, [], number=len(doc.chapters) + 1)
                        doc.add_chapter(current_chapter)
                        current_section = Section("Content", [])
                        current_chapter.sections.append(current_section)
                    elif header_level <= 3:  # New section
                        current_section = Section(header_text, [])
                        current_chapter.sections.append(current_section)
                    
                    # Process content
                    self._process_markdown_content(section_content, current_section)
            
            return doc
            
        except Exception as e:
            print(f"Error parsing Markdown file {file_path}: {e}")
            return None
    
    def _process_markdown_content(self, content: str, section):
        """Process markdown content into appropriate elements"""
        import re
        from doc.psense.document.paragraph import Paragraph
        from doc.psense.document.enhanced_content import CodeBlock
        
        # Split by code blocks
        parts = re.split(r'```(\w+)?\n(.*?)\n```', content, flags=re.DOTALL)
        
        for i, part in enumerate(parts):
            if i % 3 == 0:  # Regular text
                paragraphs = [p.strip() for p in part.split('\n\n') if p.strip()]
                for para_text in paragraphs:
                    if para_text:
                        # Remove markdown formatting for plain text
                        clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', para_text)  # Bold
                        clean_text = re.sub(r'\*(.*?)\*', r'\1', clean_text)      # Italic
                        clean_text = re.sub(r'`(.*?)`', r'\1', clean_text)        # Inline code
                        section.content.append(Paragraph(clean_text))
            elif i % 3 == 2:  # Code block content
                language = parts[i - 1] if parts[i - 1] else "text"
                section.content.append(CodeBlock(part, language))


# Register parsers
DocumentParserFactory.register_parser(HTMLDocumentParser, ['.html', '.htm'])
DocumentParserFactory.register_parser(MarkdownDocumentParser, ['.md', '.markdown'])


def parse_any_document(file_path: str, config: Optional[Dict[str, Any]] = None) -> Optional[Document]:
    """Convenience function to parse any supported document format"""
    return DocumentParserFactory.parse_document(file_path, config)


# Example usage
if __name__ == "__main__":
    # Parse different document types
    html_doc = parse_any_document("example.html")
    md_doc = parse_any_document("README.md")
    
    if html_doc:
        print(f"HTML Document: {html_doc.title}")
        print(f"Chapters: {len(html_doc.chapters)}")
    
    if md_doc:
        print(f"Markdown Document: {md_doc.title}")
        print(f"Chapters: {len(md_doc.chapters)}")