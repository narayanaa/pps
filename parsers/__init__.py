# Main parsers module - unified interface
# Access parsers through parsers.psense namespace
from . import psense

# Direct access to commonly used parsers
try:
    from .psense.pdf import PDFParser
except ImportError:
    PDFParser = None
    
try:
    from .psense.docx import DOCXParser
except ImportError:
    DOCXParser = None
    
try:
    from .psense.ebook import EBookParser
except ImportError:
    EBookParser = None
    
try:
    from .psense.md import MarkdownParser
except ImportError:
    MarkdownParser = None

# Document processor for unified interface
try:
    from .psense.document_processor import DocumentProcessor
except ImportError:
    DocumentProcessor = None
