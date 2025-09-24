"""
Advanced Content Types for Comprehensive Document Processing

This module provides specialized content types for mathematical formulas,
interactive elements, and annotations to enhance document richness.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from datetime import datetime

from .data_element import DataElement


class FormulaNotation(Enum):
    """Supported mathematical notation formats."""
    LATEX = "latex"
    MATHML = "mathml"
    ASCII_MATH = "asciimath"
    UNICODE = "unicode"


class InteractionType(Enum):
    """Types of interactive elements."""
    FORM = "form"
    BUTTON = "button"
    LINK = "link"
    INPUT_FIELD = "input_field"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    RADIO_BUTTON = "radio_button"
    SLIDER = "slider"
    VIDEO_PLAYER = "video_player"
    AUDIO_PLAYER = "audio_player"


class AnnotationType(Enum):
    """Types of annotations."""
    COMMENT = "comment"
    HIGHLIGHT = "highlight"
    NOTE = "note"
    BOOKMARK = "bookmark"
    STICKY_NOTE = "sticky_note"
    UNDERLINE = "underline"
    STRIKETHROUGH = "strikethrough"
    REVIEW = "review"


@dataclass
class Formula(DataElement):
    """
    Mathematical formula with support for multiple notation formats.
    
    Features:
    - Multiple notation format support (LaTeX, MathML, ASCII Math)
    - Rendered image path for display
    - Alternative text for accessibility
    - Variable definitions
    """
    
    formula: str
    notation: FormulaNotation = FormulaNotation.LATEX
    rendered_path: Optional[str] = None
    alt_text: Optional[str] = None
    variables: Dict[str, str] = field(default_factory=dict)
    inline: bool = False
    
    def __post_init__(self):
        super().__init__()
        if not self.alt_text:
            self.alt_text = f"Mathematical formula: {self.formula[:50]}..."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert formula to dictionary representation."""
        return {
            **super().to_dict(),
            "type": "formula",
            "formula": self.formula,
            "notation": self.notation.value,
            "rendered_path": self.rendered_path,
            "alt_text": self.alt_text,
            "variables": self.variables,
            "inline": self.inline,
            "complexity_score": self._calculate_complexity()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Formula':
        """Create Formula from dictionary."""
        return cls(
            id=data.get('id'),
            formula=data['formula'],
            notation=FormulaNotation(data.get('notation', 'latex')),
            rendered_path=data.get('rendered_path'),
            alt_text=data.get('alt_text'),
            variables=data.get('variables', {}),
            inline=data.get('inline', False)
        )
    
    def extract_metadata(self, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Extract comprehensive metadata from formula."""
        metadata = super().extract_metadata(fields)
        
        formula_metadata = {
            "notation_type": self.notation.value,
            "is_inline": self.inline,
            "has_rendered_image": self.rendered_path is not None,
            "variable_count": len(self.variables),
            "formula_length": len(self.formula),
            "complexity_indicators": self._analyze_complexity()
        }
        
        metadata.update(formula_metadata)
        return metadata
    
    def to_text(self) -> str:
        """Convert to plain text representation."""
        if self.alt_text:
            return self.alt_text
        return f"Formula ({self.notation.value}): {self.formula}"
    
    def _calculate_complexity(self) -> int:
        """Calculate formula complexity score (0-10)."""
        complexity_indicators = [
            ('\\int', 2), ('\\sum', 2), ('\\prod', 2),  # Integrals, sums
            ('\\frac', 1), ('\\sqrt', 1), ('\\partial', 2),  # Fractions, roots, partials
            ('^', 1), ('_', 1),  # Super/subscripts
            ('\\alpha', 1), ('\\beta', 1), ('\\gamma', 1),  # Greek letters
            ('\\matrix', 3), ('\\begin', 2)  # Matrices, environments
        ]
        
        score = 0
        for indicator, weight in complexity_indicators:
            score += self.formula.count(indicator) * weight
        
        return min(score, 10)  # Cap at 10
    
    def _analyze_complexity(self) -> Dict[str, Any]:
        """Analyze formula complexity in detail."""
        return {
            "has_integrals": '\\int' in self.formula,
            "has_summations": '\\sum' in self.formula,
            "has_fractions": '\\frac' in self.formula,
            "has_matrices": '\\matrix' in self.formula or '\\begin{matrix}' in self.formula,
            "has_greek_letters": any(letter in self.formula 
                                   for letter in ['\\alpha', '\\beta', '\\gamma', '\\delta', '\\theta']),
            "complexity_score": self._calculate_complexity()
        }


@dataclass  
class InteractiveElement(DataElement):
    """
    Interactive element within documents (forms, buttons, media players, etc.).
    
    Features:
    - Multiple interaction types
    - State management
    - Event handling metadata
    - Accessibility support
    """
    
    element_type: InteractionType
    properties: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    events: List[str] = field(default_factory=list)
    accessible: bool = True
    label: Optional[str] = None
    
    def __post_init__(self):
        super().__init__()
        if not self.label:
            self.label = f"{self.element_type.value.replace('_', ' ').title()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert interactive element to dictionary."""
        return {
            **super().to_dict(),
            "type": "interactive_element",
            "element_type": self.element_type.value,
            "properties": self.properties,
            "state": self.state,
            "events": self.events,
            "accessible": self.accessible,
            "label": self.label,
            "interaction_metadata": self._analyze_interactions()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InteractiveElement':
        """Create InteractiveElement from dictionary."""
        return cls(
            id=data.get('id'),
            element_type=InteractionType(data['element_type']),
            properties=data.get('properties', {}),
            state=data.get('state', {}),
            events=data.get('events', []),
            accessible=data.get('accessible', True),
            label=data.get('label')
        )
    
    def extract_metadata(self, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Extract metadata from interactive element."""
        metadata = super().extract_metadata(fields)
        
        interaction_metadata = {
            "interaction_type": self.element_type.value,
            "has_events": len(self.events) > 0,
            "is_accessible": self.accessible,
            "property_count": len(self.properties),
            "has_state": len(self.state) > 0,
            "complexity_level": self._assess_complexity()
        }
        
        metadata.update(interaction_metadata)
        return metadata
    
    def to_text(self) -> str:
        """Convert to text representation."""
        text = f"Interactive {self.element_type.value.replace('_', ' ')}"
        if self.label:
            text += f": {self.label}"
        
        # Add key properties
        if 'value' in self.properties:
            text += f" (Value: {self.properties['value']})"
        if 'href' in self.properties:
            text += f" (Link: {self.properties['href']})"
            
        return text
    
    def _analyze_interactions(self) -> Dict[str, Any]:
        """Analyze interaction patterns."""
        return {
            "event_types": list(set(self.events)),
            "has_validation": 'required' in self.properties or 'pattern' in self.properties,
            "is_multimedia": self.element_type in [InteractionType.VIDEO_PLAYER, InteractionType.AUDIO_PLAYER],
            "complexity_assessment": self._assess_complexity()
        }
    
    def _assess_complexity(self) -> str:
        """Assess interaction complexity."""
        if len(self.events) > 3 or len(self.properties) > 5:
            return "high"
        elif len(self.events) > 1 or len(self.properties) > 2:
            return "medium"
        else:
            return "low"


@dataclass
class Annotation(DataElement):
    """
    Annotation for document markup and collaboration.
    
    Features:
    - Multiple annotation types
    - Author tracking
    - Timestamp management
    - Reply threads
    - Status tracking
    """
    
    content: str
    annotation_type: AnnotationType
    author: Optional[str] = None
    created_date: datetime = field(default_factory=datetime.now)
    modified_date: Optional[datetime] = None
    target_element_id: Optional[str] = None
    position: Optional[Dict[str, Union[int, float]]] = None
    replies: List['Annotation'] = field(default_factory=list)
    status: str = "active"  # active, resolved, deleted
    priority: str = "normal"  # low, normal, high, urgent
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        super().__init__()
        if self.modified_date is None:
            self.modified_date = self.created_date
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert annotation to dictionary."""
        return {
            **super().to_dict(),
            "type": "annotation",
            "content": self.content,
            "annotation_type": self.annotation_type.value,
            "author": self.author,
            "created_date": self.created_date.isoformat(),
            "modified_date": self.modified_date.isoformat() if self.modified_date else None,
            "target_element_id": self.target_element_id,
            "position": self.position,
            "replies": [reply.to_dict() for reply in self.replies],
            "status": self.status,
            "priority": self.priority,
            "tags": self.tags,
            "thread_metadata": self._analyze_thread()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Annotation':
        """Create Annotation from dictionary."""
        return cls(
            id=data.get('id'),
            content=data['content'],
            annotation_type=AnnotationType(data['annotation_type']),
            author=data.get('author'),
            created_date=datetime.fromisoformat(data['created_date']) 
                         if 'created_date' in data else datetime.now(),
            modified_date=datetime.fromisoformat(data['modified_date']) 
                         if data.get('modified_date') else None,
            target_element_id=data.get('target_element_id'),
            position=data.get('position'),
            replies=[cls.from_dict(reply) for reply in data.get('replies', [])],
            status=data.get('status', 'active'),
            priority=data.get('priority', 'normal'),
            tags=data.get('tags', [])
        )
    
    def extract_metadata(self, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Extract annotation metadata."""
        metadata = super().extract_metadata(fields)
        
        annotation_metadata = {
            "annotation_type": self.annotation_type.value,
            "has_author": self.author is not None,
            "has_replies": len(self.replies) > 0,
            "reply_count": len(self.replies),
            "has_position": self.position is not None,
            "age_days": (datetime.now() - self.created_date).days,
            "is_recent": (datetime.now() - self.created_date).days < 7,
            "priority_level": self.priority,
            "tag_count": len(self.tags)
        }
        
        metadata.update(annotation_metadata)
        return metadata
    
    def to_text(self) -> str:
        """Convert annotation to text."""
        text = f"[{self.annotation_type.value.upper()}]"
        if self.author:
            text += f" by {self.author}"
        text += f": {self.content}"
        
        if self.replies:
            text += f" ({len(self.replies)} replies)"
            
        return text
    
    def add_reply(self, content: str, author: Optional[str] = None) -> 'Annotation':
        """Add a reply to this annotation."""
        reply = Annotation(
            content=content,
            annotation_type=AnnotationType.COMMENT,
            author=author,
            target_element_id=self.id
        )
        self.replies.append(reply)
        self.modified_date = datetime.now()
        return reply
    
    def resolve(self) -> None:
        """Mark annotation as resolved."""
        self.status = "resolved"
        self.modified_date = datetime.now()
    
    def _analyze_thread(self) -> Dict[str, Any]:
        """Analyze annotation thread."""
        return {
            "thread_depth": len(self.replies),
            "unique_authors": len(set(reply.author for reply in self.replies if reply.author)),
            "last_activity": max([reply.created_date for reply in self.replies] + [self.created_date]),
            "is_discussion": len(self.replies) > 2,
            "has_unresolved_issues": any(reply.status == "active" for reply in self.replies)
        }


# Utility functions for working with advanced content types

def create_latex_formula(latex_code: str, inline: bool = False, 
                        variables: Optional[Dict[str, str]] = None) -> Formula:
    """Create a LaTeX formula with common defaults."""
    return Formula(
        formula=latex_code,
        notation=FormulaNotation.LATEX,
        inline=inline,
        variables=variables or {}
    )


def create_form_element(element_type: str, properties: Dict[str, Any], 
                       label: Optional[str] = None) -> InteractiveElement:
    """Create a form element with validation."""
    interaction_type = InteractionType(element_type)
    return InteractiveElement(
        element_type=interaction_type,
        properties=properties,
        label=label,
        accessible=True
    )


def create_highlight_annotation(text: str, author: str, 
                               target_id: str, position: Optional[Dict] = None) -> Annotation:
    """Create a highlight annotation."""
    return Annotation(
        content=text,
        annotation_type=AnnotationType.HIGHLIGHT,
        author=author,
        target_element_id=target_id,
        position=position
    )


# Export all classes and utility functions
__all__ = [
    'Formula', 'InteractiveElement', 'Annotation',
    'FormulaNotation', 'InteractionType', 'AnnotationType',
    'create_latex_formula', 'create_form_element', 'create_highlight_annotation'
]