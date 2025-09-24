import datetime

import markdown
from bs4 import BeautifulSoup
from doc.psense.document.chapter import Chapter
from doc.psense.document.document import Document
from doc.psense.document.document_parser import DocumentParser
from doc.psense.document.paragraph import Paragraph
from doc.psense.document.section import Section


class MarkdownParser(DocumentParser):
    def parse(self, filepath: str) -> Document:
        with open(filepath, 'r', encoding='utf-8') as f:
            md_text = f.read()

        html = markdown.markdown(md_text)

        soup = BeautifulSoup(html, 'html.parser')

        # Initialize the Document
        document_title = 'Untitled Document'
        first_heading = soup.find(['h1'])
        if first_heading:
            document_title = first_heading.get_text()

        document = Document(title=document_title, created_date=datetime.datetime.now(), url=filepath)

        current_chapter = None
        current_section = None
        
        # Process all elements in the HTML
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
            if element.name in ['h1', 'h2']:
                # Create new chapter
                if current_chapter:
                    document.add_chapter(current_chapter)
                
                chapter_title = element.get_text().strip()
                current_chapter = Chapter(
                    title=chapter_title,
                    sections=[],
                    number=len(document.chapters) + 1
                )
                current_section = None
                
            elif element.name in ['h3', 'h4', 'h5', 'h6']:
                # Create new section
                if not current_chapter:
                    current_chapter = Chapter(
                        title="Main Content",
                        sections=[],
                        number=1
                    )
                
                section_title = element.get_text().strip()
                current_section = Section(
                    title=section_title,
                    content=[],
                    level=int(element.name[1]) - 2  # h3=1, h4=2, etc.
                )
                current_chapter.sections.append(current_section)
                
            elif element.name == 'p':
                # Add paragraph to current section
                if not current_chapter:
                    current_chapter = Chapter(
                        title="Main Content",
                        sections=[],
                        number=1
                    )
                
                if not current_section:
                    current_section = Section(
                        title="Content",
                        content=[],
                        level=1
                    )
                    current_chapter.sections.append(current_section)
                
                para_text = element.get_text().strip()
                if para_text:
                    paragraph = Paragraph(text=para_text)
                    current_section.content.append(paragraph)
        
        # Add the last chapter if it exists
        if current_chapter:
            document.add_chapter(current_chapter)
        
        # Ensure document has at least one chapter
        if not document.chapters:
            default_chapter = Chapter(
                title="Main Content",
                sections=[Section(
                    title="Content",
                    content=[Paragraph("No content found")],
                    level=1
                )],
                number=1
            )
            document.add_chapter(default_chapter)
        
        return document

        for element in soup.descendants:
            if element.name == 'h1':
                if current_chapter:
                    document.add_chapter(current_chapter)
                current_chapter = Chapter(title=element.get_text(), sections=[], number=len(document.chapters) + 1)
                current_section = None
            elif element.name == 'h2':
                if current_section and current_chapter:
                    current_chapter.sections.append(current_section)
                current_section = Section(title=element.get_text(), content=[])
            elif element.name == 'p':
                paragraph = Paragraph(text=element.get_text())
                if current_section:
                    current_section.content.append(paragraph)
                elif current_chapter:
                    # If no current section, create a default section
                    current_section = Section(title="Introduction", content=[paragraph])
                    current_chapter.sections.append(current_section)
                else:
                    # If no chapter, create a default chapter
                    current_chapter = Chapter(title="Chapter 1", sections=[], number=1)
                    current_section = Section(title="Introduction", content=[paragraph])
                    current_chapter.sections.append(current_section)
                    document.add_chapter(current_chapter)

        # Add any remaining sections and chapters
        if current_section and current_chapter:
            current_chapter.sections.append(current_section)
        if current_chapter:
            document.add_chapter(current_chapter)

        return document
