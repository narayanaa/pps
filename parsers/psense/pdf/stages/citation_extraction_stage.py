try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    pdfplumber = None
    PDFPLUMBER_AVAILABLE = False
    
from doc.psense.document.document import Document
from .parsing_stage import ParsingStage


class CitationExtractionStage(ParsingStage):
    def __init__(self, parser):
        super().__init__(parser)

    def process(self, doc: Document):
        if not PDFPLUMBER_AVAILABLE:
            print("Warning: pdfplumber not available, skipping citation extraction")
            return
            
        with pdfplumber.open(doc.url) as plumber_doc:
            section = self.parser.citation_utils.extract_references_section(plumber_doc)
            if section:
                citations = self.parser.citation_utils.parse_references(section)
                # Add as a section at the end
                from doc.psense.document.section import Section
                from doc.psense.document.paragraph import Paragraph
                ref_section = Section(title="References", content=[Paragraph(c) for c in citations], level=1)
                if doc.chapters:
                    doc.chapters[-1].sections.append(ref_section)
                else:
                    from doc.psense.document.chapter import Chapter
                    doc.chapters.append(Chapter(title=doc.title, sections=[ref_section], number=1, author=doc.author))
                # Store references in cache instead of metadata (which doesn't exist)
                if hasattr(doc, 'cache'):
                    doc.cache["references"] = citations
