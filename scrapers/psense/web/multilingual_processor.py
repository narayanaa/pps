"""
Multilingual Language Processing Module
Supports Arabic, Chinese, Hindi, Telugu, Japanese, Korean and other international languages
"""

import logging
import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Core dependencies
try:
    import langdetect
    from langdetect import DetectorFactory, detect_langs
    DetectorFactory.seed = 0  # For consistent results
    LANGDETECT_AVAILABLE = True
except ImportError:
    langdetect = None
    LANGDETECT_AVAILABLE = False

try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    chardet = None
    CHARDET_AVAILABLE = False

try:
    import ftfy
    FTFY_AVAILABLE = True
except ImportError:
    ftfy = None
    FTFY_AVAILABLE = False

try:
    from bidi.algorithm import get_display
    BIDI_AVAILABLE = True
except ImportError:
    get_display = None
    BIDI_AVAILABLE = False

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    spacy = None
    SPACY_AVAILABLE = False

logger = logging.getLogger(__name__)


class ScriptType(Enum):
    """Text script types for different writing systems"""
    LATIN = "latin"
    ARABIC = "arabic"
    CJK = "cjk"  # Chinese, Japanese, Korean
    DEVANAGARI = "devanagari"  # Hindi, Sanskrit
    TELUGU = "telugu"
    CYRILLIC = "cyrillic"
    THAI = "thai"
    HEBREW = "hebrew"
    UNKNOWN = "unknown"


@dataclass
class LanguageInfo:
    """Language information structure"""
    code: str
    name: str
    script: ScriptType
    confidence: float
    encoding: str = "utf-8"
    is_rtl: bool = False


@dataclass
class ProcessedText:
    """Processed multilingual text structure"""
    original: str
    normalized: str
    language: LanguageInfo
    cleaned: str
    direction: str  # 'ltr' or 'rtl'
    encoding: str


class MultilingualProcessor:
    """
    Advanced multilingual text processing for web scraping
    Handles Arabic, Chinese, Hindi, Telugu, Japanese, Korean, and other languages
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.language_support = self.config.get("language_support", {})
        self.supported_languages = self.language_support.get("supported_languages", {})
        self.detection_config = self.language_support.get("language_detection", {})
        self.text_config = self.language_support.get("text_processing", {})
        
        # Language models cache
        self.spacy_models = {}
        
        # Unicode script ranges for script detection
        self.script_ranges = {
            ScriptType.ARABIC: [(0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF)],
            ScriptType.CJK: [(0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0x3040, 0x309F), (0x30A0, 0x30FF)],
            ScriptType.DEVANAGARI: [(0x0900, 0x097F)],
            ScriptType.TELUGU: [(0x0C00, 0x0C7F)],
            ScriptType.CYRILLIC: [(0x0400, 0x04FF)],
            ScriptType.THAI: [(0x0E00, 0x0E7F)],
            ScriptType.HEBREW: [(0x0590, 0x05FF)],
        }
        
        # RTL scripts
        self.rtl_scripts = {ScriptType.ARABIC, ScriptType.HEBREW}
        
        logger.info(f"MultilingualProcessor initialized with {len(self.supported_languages)} supported languages")
    
    def detect_language(self, text: str) -> LanguageInfo:
        """
        Detect language of text using multiple methods
        
        Args:
            text (str): Text to analyze
            
        Returns:
            LanguageInfo: Detected language information
        """
        if not text or len(text.strip()) < 10:
            return LanguageInfo("en", "English", ScriptType.LATIN, 0.0)
        
        # Clean text for detection
        clean_text = self._clean_for_detection(text)
        
        # Primary: langdetect
        if LANGDETECT_AVAILABLE and detect_langs:
            try:
                detections = detect_langs(clean_text)
                if detections:
                    primary = detections[0]
                    lang_code = primary.lang
                    confidence = primary.prob
                    
                    # Map to our supported languages
                    lang_info = self._map_language_code(lang_code, confidence)
                    if lang_info:
                        return lang_info
            except Exception as e:
                logger.debug(f"Language detection failed: {e}")
        
        # Fallback: Script-based detection
        script_type = self.detect_script(clean_text)
        return self._script_to_language(script_type, 0.6)
    
    def detect_script(self, text: str) -> ScriptType:
        """
        Detect script type based on Unicode ranges
        
        Args:
            text (str): Text to analyze
            
        Returns:
            ScriptType: Detected script type
        """
        if not text:
            return ScriptType.UNKNOWN
        
        script_counts = {script: 0 for script in ScriptType}
        
        for char in text:
            code_point = ord(char)
            
            for script_type, ranges in self.script_ranges.items():
                for start, end in ranges:
                    if start <= code_point <= end:
                        script_counts[script_type] += 1
                        break
            
            # Latin detection
            if 0x0000 <= code_point <= 0x007F or 0x0080 <= code_point <= 0x00FF:
                script_counts[ScriptType.LATIN] += 1
        
        # Find most common script
        max_script = max(script_counts.items(), key=lambda x: x[1])
        return max_script[0] if max_script[1] > 0 else ScriptType.UNKNOWN
    
    def process_text(self, text: str, detected_language: Optional[LanguageInfo] = None) -> ProcessedText:
        """
        Process multilingual text with normalization and cleaning
        
        Args:
            text (str): Raw text to process
            detected_language (LanguageInfo): Pre-detected language info
            
        Returns:
            ProcessedText: Processed text with metadata
        """
        if not text:
            return ProcessedText("", "", LanguageInfo("en", "English", ScriptType.LATIN, 0.0), "", "ltr", "utf-8")
        
        # Detect language if not provided
        if not detected_language:
            detected_language = self.detect_language(text)
        
        # Normalize text
        normalized = self._normalize_text(text, detected_language)
        
        # Clean text
        cleaned = self._clean_text(normalized, detected_language)
        
        # Determine text direction
        direction = "rtl" if detected_language.script in self.rtl_scripts else "ltr"
        
        # Handle RTL text if needed
        if direction == "rtl" and BIDI_AVAILABLE and get_display and self.text_config.get("rtl_support", True):
            try:
                cleaned = get_display(cleaned)
            except Exception as e:
                logger.debug(f"RTL processing failed: {e}")
        
        return ProcessedText(
            original=text,
            normalized=normalized,
            language=detected_language,
            cleaned=cleaned,
            direction=direction,
            encoding=detected_language.encoding
        )
    
    def extract_multilingual_content(self, html_content: str, soup) -> Dict[str, Any]:
        """
        Extract and process multilingual content from HTML
        
        Args:
            html_content (str): Raw HTML content
            soup: BeautifulSoup object
            
        Returns:
            Dict[str, Any]: Extracted multilingual content
        """
        content_by_language = {}
        
        # Extract main text
        main_text = soup.get_text(separator=" ", strip=True)
        if main_text:
            processed = self.process_text(main_text)
            lang_code = processed.language.code
            
            if lang_code not in content_by_language:
                content_by_language[lang_code] = {
                    "language": processed.language,
                    "texts": [],
                    "direction": processed.direction,
                    "script": processed.language.script.value
                }
            
            content_by_language[lang_code]["texts"].append(processed.cleaned)
        
        # Extract language-specific elements
        for lang_code, lang_config in self.supported_languages.items():
            selectors = lang_config.get("content_selectors", [])
            url_patterns = lang_config.get("url_patterns", [])
            
            # Find language-specific content by CSS selectors
            for selector in selectors:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        text = element.get_text(strip=True)
                        if text and len(text) > 20:  # Minimum content length
                            processed = self.process_text(text)
                            
                            if processed.language.code not in content_by_language:
                                content_by_language[processed.language.code] = {
                                    "language": processed.language,
                                    "texts": [],
                                    "direction": processed.direction,
                                    "script": processed.language.script.value
                                }
                            
                            content_by_language[processed.language.code]["texts"].append(processed.cleaned)
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
        
        # Detect content by lang attributes
        lang_elements = soup.find_all(attrs={"lang": True})
        for element in lang_elements:
            lang_attr = element.get("lang", "").lower()
            text = element.get_text(strip=True)
            
            if text and len(text) > 20:
                # Map HTML lang attribute to our language codes
                mapped_lang = self._map_html_lang(lang_attr)
                if mapped_lang:
                    processed = self.process_text(text)
                    processed.language.code = mapped_lang
                    
                    if mapped_lang not in content_by_language:
                        content_by_language[mapped_lang] = {
                            "language": processed.language,
                            "texts": [],
                            "direction": processed.direction,
                            "script": processed.language.script.value
                        }
                    
                    content_by_language[mapped_lang]["texts"].append(processed.cleaned)
        
        return content_by_language
    
    def should_process_url(self, url: str, allowed_languages: Optional[List[str]] = None) -> bool:
        """
        Determine if URL should be processed based on language patterns
        
        Args:
            url (str): URL to check
            allowed_languages (List[str]): List of allowed language codes
            
        Returns:
            bool: Whether URL should be processed
        """
        if not allowed_languages:
            return True
        
        url_lower = url.lower()
        
        for lang_code in allowed_languages:
            if lang_code in self.supported_languages:
                patterns = self.supported_languages[lang_code].get("url_patterns", [])
                if any(pattern in url_lower for pattern in patterns):
                    return True
            
            # Direct language code match
            if f"/{lang_code}/" in url_lower:
                return True
        
        return False
    
    def get_language_specific_config(self, detected_language: str) -> Dict[str, Any]:
        """
        Get language-specific configuration
        
        Args:
            detected_language (str): Language code
            
        Returns:
            Dict[str, Any]: Language-specific configuration
        """
        if detected_language in self.supported_languages:
            return self.supported_languages[detected_language]
        
        # Return default configuration
        return {
            "code": detected_language,
            "name": detected_language.title(),
            "script": "ltr",
            "encoding": "utf-8"
        }
    
    def _clean_for_detection(self, text: str) -> str:
        """Clean text for language detection"""
        # Remove URLs, emails, numbers
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        text = re.sub(r'\b\d+\b', '', text)
        
        # Keep only letters and spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _normalize_text(self, text: str, language_info: LanguageInfo) -> str:
        """Normalize text based on language"""
        if not self.text_config.get("normalize_unicode", True):
            return text
        
        # Fix encoding issues
        if FTFY_AVAILABLE and ftfy:
            try:
                text = ftfy.fix_text(text)
            except Exception:
                pass
        
        # Unicode normalization
        try:
            text = unicodedata.normalize('NFKC', text)
        except Exception:
            pass
        
        return text
    
    def _clean_text(self, text: str, language_info: LanguageInfo) -> str:
        """Clean text based on language-specific rules"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Language-specific cleaning
        if language_info.script == ScriptType.ARABIC:
            # Remove Arabic diacritics if needed
            text = re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06ED]', '', text)
        
        elif language_info.script == ScriptType.CJK:
            # Normalize CJK whitespace
            text = re.sub(r'[\u3000\ufeff]+', ' ', text)
        
        return text.strip()
    
    def _map_language_code(self, lang_code: str, confidence: float) -> Optional[LanguageInfo]:
        """Map langdetect codes to our language info"""
        mapping = {
            "ar": ("ar", "Arabic", ScriptType.ARABIC, True),
            "zh-cn": ("zh", "Chinese", ScriptType.CJK, False),
            "zh-tw": ("zh", "Chinese", ScriptType.CJK, False),
            "hi": ("hi", "Hindi", ScriptType.DEVANAGARI, False),
            "te": ("te", "Telugu", ScriptType.TELUGU, False),
            "ja": ("ja", "Japanese", ScriptType.CJK, False),
            "ko": ("ko", "Korean", ScriptType.CJK, False),
            "en": ("en", "English", ScriptType.LATIN, False),
        }
        
        if lang_code in mapping:
            code, name, script, is_rtl = mapping[lang_code]
            return LanguageInfo(code, name, script, confidence, "utf-8", is_rtl)
        
        return None
    
    def _script_to_language(self, script: ScriptType, confidence: float) -> LanguageInfo:
        """Convert script type to language info"""
        script_to_lang = {
            ScriptType.ARABIC: ("ar", "Arabic", True),
            ScriptType.CJK: ("zh", "Chinese", False),
            ScriptType.DEVANAGARI: ("hi", "Hindi", False),
            ScriptType.TELUGU: ("te", "Telugu", False),
            ScriptType.LATIN: ("en", "English", False),
        }
        
        if script in script_to_lang:
            code, name, is_rtl = script_to_lang[script]
            return LanguageInfo(code, name, script, confidence, "utf-8", is_rtl)
        
        return LanguageInfo("en", "English", ScriptType.LATIN, 0.0)
    
    def _map_html_lang(self, html_lang: str) -> Optional[str]:
        """Map HTML lang attribute to our language codes"""
        mapping = {
            "ar": "ar",
            "ar-ae": "ar",
            "ar-sa": "ar",
            "zh": "zh",
            "zh-cn": "zh",
            "zh-tw": "zh",
            "hi": "hi",
            "hi-in": "hi",
            "te": "te",
            "te-in": "te",
            "ja": "ja",
            "ja-jp": "ja",
            "ko": "ko",
            "ko-kr": "ko",
            "en": "en",
            "en-us": "en",
            "en-gb": "en",
        }
        
        return mapping.get(html_lang.lower())


def create_multilingual_processor(config: Optional[Dict[str, Any]] = None) -> MultilingualProcessor:
    """Factory function to create multilingual processor"""
    return MultilingualProcessor(config)