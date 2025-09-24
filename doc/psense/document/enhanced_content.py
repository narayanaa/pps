"""
Enhanced content elements for comprehensive document support
"""

from typing import List, Optional
from doc.psense.data_element import DataElement
from doc.psense.document.unique_id import generate_unique_id


class CodeBlock(DataElement):
    """Programming code content with syntax highlighting support"""
    
    def __init__(self, code: str, language: str = "text", caption: str = "", 
                 line_numbers: bool = False):
        super().__init__()
        self.code = code
        self.language = language  # Programming language for syntax highlighting
        self.caption = caption
        self.line_numbers = line_numbers
        
    def extract_metadata(self, aspects: list = None):
        """Extract code-specific metadata"""
        metadata = {
            "language": self.language,
            "line_count": len(self.code.split('\n')),
            "character_count": len(self.code),
            "caption": self.caption
        }
        
        # Language-specific analysis
        if aspects and 'complexity' in aspects:
            metadata["complexity"] = self._analyze_complexity()
            
        return metadata
    
    def _analyze_complexity(self):
        """Basic code complexity analysis"""
        lines = self.code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        return {
            "total_lines": len(lines),
            "code_lines": len(non_empty_lines),
            "comment_lines": len([line for line in lines if line.strip().startswith('#')])
        }
    
    def to_text(self):
        """Convert to plain text representation"""
        return f"Code Block ({self.language}): {self.caption}\n{self.code}"
    
    def get_entities(self):
        """Extract entities from code comments and strings"""
        # Simple implementation - can be enhanced with AST parsing
        return [(self.language, "PROGRAMMING_LANGUAGE")]
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": "code_block",
            "code": self.code,
            "language": self.language,
            "caption": self.caption,
            "line_numbers": self.line_numbers,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }
    
    def __repr__(self):
        return f"CodeBlock(language='{self.language}', lines={len(self.code.split())})"


class Formula(DataElement):
    """Mathematical formula with LaTeX support"""
    
    def __init__(self, formula: str, notation: str = "latex", caption: str = ""):
        super().__init__()
        self.formula = formula
        self.notation = notation  # latex, mathml, ascii
        self.caption = caption
        
    def extract_metadata(self, aspects: list = None):
        """Extract formula metadata"""
        metadata = {
            "notation": self.notation,
            "length": len(self.formula),
            "caption": self.caption
        }
        
        if aspects and 'variables' in aspects:
            metadata["variables"] = self._extract_variables()
            
        return metadata
    
    def _extract_variables(self):
        """Extract mathematical variables from formula"""
        # Basic implementation for LaTeX
        import re
        if self.notation == "latex":
            variables = re.findall(r'\\?([a-zA-Z])', self.formula)
            return list(set(variables))
        return []
    
    def to_text(self):
        """Convert to plain text"""
        return f"Formula ({self.notation}): {self.caption}\n{self.formula}"
    
    def get_entities(self):
        """Extract mathematical entities"""
        variables = self._extract_variables()
        return [(var, "MATHEMATICAL_VARIABLE") for var in variables]
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": "formula",
            "formula": self.formula,
            "notation": self.notation,
            "caption": self.caption,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }
    
    def __repr__(self):
        return f"Formula(notation='{self.notation}', caption='{self.caption[:30]}...')"


class Annotation(DataElement):
    """Comments, highlights, and notes within documents"""
    
    def __init__(self, content: str, annotation_type: str = "comment", 
                 target_element_id: Optional[str] = None, author: Optional[str] = None):
        super().__init__()
        self.content = content
        self.annotation_type = annotation_type  # comment, highlight, note, bookmark
        self.target_element_id = target_element_id  # ID of element being annotated
        self.author = author
        
    def extract_metadata(self, aspects: list = None):
        """Extract annotation metadata"""
        metadata = {
            "type": self.annotation_type,
            "author": self.author,
            "target_element": self.target_element_id,
            "length": len(self.content)
        }
        return metadata
    
    def to_text(self):
        """Convert to plain text"""
        return f"Annotation ({self.annotation_type}): {self.content}"
    
    def get_entities(self):
        """Extract entities from annotation content"""
        return [(self.content, f"ANNOTATION_{self.annotation_type.upper()}")]
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": "annotation",
            "content": self.content,
            "annotation_type": self.annotation_type,
            "target_element_id": self.target_element_id,
            "author": self.author,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }
    
    def __repr__(self):
        return f"Annotation(type='{self.annotation_type}', author='{self.author}')"