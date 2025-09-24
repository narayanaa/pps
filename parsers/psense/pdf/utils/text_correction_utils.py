# text_correction_utils.py
from __future__ import annotations

import unicodedata

from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import os
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

"""text_correction_utils.py
Layered post‑OCR cleaning: regex → numeric guard → SymSpell → Transformer.
"""
import re
import logging
from typing import Dict, Any
from symspellpy import SymSpell, Verbosity
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logger = logging.getLogger(__name__)


class TextCorrectionUtils:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.text_cleaning = cfg.get("text_cleaning", {})
        self._setup_symspell()
        if cfg.get("transformer_correction", {}).get("enabled", False):
            model_name = cfg["transformer_correction"].get("model", "t5-small")
            self.tok = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        else:
            self.tok = self.model = None

    def clean(self, text: str, ocr_conf: float | None = None) -> str:
        # Step 1: Basic cleaning (moved from TextCleaningUtils)
        text = self._basic_clean(text)
        # Step 2: Advanced corrections
        text = self._basic_regex(text)
        text = self._numeric_guard(text)
        if self.symspell and (ocr_conf is None or ocr_conf < 80):
            text = self._symspell_fix(text)
        if self.model and (ocr_conf is None or ocr_conf < 80):
            text = self._transformer_fix(text)
        return text

    def _basic_clean(self, text: str) -> str:
        config = self.cfg.get("text_cleaning", {})
        # Normalize unicode characters
        if config.get("normalize_unicode", True):
            text = unicodedata.normalize("NFKC", text)
        # Replace common ligatures
        if config.get("replace_ligatures", True):
            ligatures = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
            for lig, rep in ligatures.items():
                text = text.replace(lig, rep)
        # Remove non-ASCII characters
        if config.get("remove_non_ascii", True):
            text = ''.join(c for c in text if ord(c) < 128)
        # Collapse multiple newlines into one
        if config.get("collapse_newlines", True):
            text = re.sub(r'\n+', '\n', text)
        # Normalize whitespace
        if config.get("fix_whitespace", True):
            text = re.sub(r'\s+', ' ', text).strip()
        # Remove headers/footers
        if config.get("remove_headers_footers", True):
            lines = text.splitlines()
            cleaned_lines = [line for line in lines if
                             not re.match(r'^Page\s+\d+|^Confidential|^[A-Z]{2,}\s+\d+$', line, re.IGNORECASE)]
            text = '\n'.join(cleaned_lines)
        # Remove repeated characters
        text = re.sub(r'(.)\1{2,}', r'\1', text)
        # Remove OCR artifacts
        text = re.sub(r'\(cid:\d+\)', '', text)
        # Remove random short word sequences
        text = re.sub(r'\b\w{1,3}\s+\w{1,3}\s+\w{1,3}\b', '', text)
        # Keep alphanumeric and basic punctuation
        text = re.sub(r'[^\w\s.,!?₹$:/-]', '', text)
        return text

    # ... (rest of the methods like _basic_regex, _numeric_guard, etc. remain unchanged)

    # ------------------------------------------------------------------
    def _setup_symspell(self):
        if not self.cfg["text_cleaning"].get("fuzzy_spell", False):
            self.symspell = None
            return
        max_edit = 2
        size = 82765
        self.symspell = SymSpell(max_dictionary_edit_distance=max_edit, prefix_length=7)  #, initial_capacity=size)
        dict_path = self.cfg["text_cleaning"].get("dictionary_path")
        if dict_path:
            self.symspell.load_dictionary(dict_path, term_index=0, count_index=1)

    # ------------------------------------------------------------------
    def _basic_regex(self, text: str) -> str:
        # Collapse alphabetic repeats (>=3)
        if self.cfg["text_cleaning"].get("collapse_repeats", True):
            text = re.sub(r"([A-Za-z])\1{2,}", r"\1", text)
        # Allow digits, commas, hyphens, slashes, rupee symbol
        text = re.sub(r"[^\w\s.,₹$:/-]", "", text)
        return text

    def _numeric_guard(self, text: str) -> str:
        def fix(match):
            parts = match.group().split(',')
            if len(parts[-1]) == 1:
                parts[-1] = parts[-1] + "0" * (3 - len(parts[-1]))
            return ','.join(parts)

        return re.sub(r"\b\d{1,3}(,\d{1,3})+\b", fix, text)

    def _symspell_fix(self, text: str) -> str:
        words = text.split()
        corrected = []
        for w in words:
            suggestions = self.symspell.lookup(w, Verbosity.TOP, max_edit_distance=2)
            corrected.append(suggestions[0].term if suggestions else w)
        return " ".join(corrected)

    def _transformer_fix(self, text: str) -> str:
        batch = self.tok(text, return_tensors="pt", truncation=True)
        gen = self.model.generate(**batch, max_new_tokens=512)
        return self.tok.decode(gen[0], skip_special_tokens=True)

    # --- Clean OCR Text: FINAL POLISHED VERSION ---
    @staticmethod
    def clean_ocr_text(text: str, config: Dict[str, Any], ocr_conf: float | None = None) -> str:
        if not text:
            return ""

        text_cleaning = config.get("text_cleaning", {})

        # Step 1: Normalize Unicode
        if text_cleaning.get("normalize_unicode", True):
            text = unicodedata.normalize("NFKC", text)

        # Step 2: Replace ligatures
        if text_cleaning.get("replace_ligatures", True):
            ligatures = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
            for lig, rep in ligatures.items():
                text = text.replace(lig, rep)

        # Step 3: Custom correction replacements
        if text_cleaning.get("corrections"):
            corrections = text_cleaning["corrections"]
            for wrong, right in corrections.items():
                text = text.replace(wrong, right)

        # Step 4: Regex substitutions (from config)
        substitutions = text_cleaning.get("substitutions", {})
        for pattern, repl in substitutions.items():
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

        # Step 5: Remove non-ASCII
        if text_cleaning.get("remove_non_ascii", True):
            text = ''.join(c for c in text if ord(c) < 128)

        # Step 6: Collapse newlines
        if text_cleaning.get("collapse_newlines", True):
            text = re.sub(r'\n+', '\n', text)

        # Step 7: Normalize whitespace
        if text_cleaning.get("fix_whitespace", True):
            text = re.sub(r'\s+', ' ', text).strip()

        # Step 8: Remove headers/footers
        if text_cleaning.get("remove_headers_footers", True):
            lines = text.splitlines()
            cleaned_lines = [
                line for line in lines
                if not re.match(r'^Page\s+\d+|^Confidential|^[A-Z]{2,}\s+\d+$', line, re.IGNORECASE)
            ]
            text = '\n'.join(cleaned_lines)

        # Step 9: Remove repeated characters
        text = re.sub(r'(.)\1{2,}', r'\1', text)

        # Step 10: Remove OCR artifacts
        text = re.sub(r'\(cid:\d+\)', '', text)

        # Step 11: Correct common number formatting errors
        # text = TextCorrectionUtils.correct_numbers(text)

        # Step 12: Remove sequences of short junk words
        text = re.sub(r'\b\w{1,3}\s+\w{1,3}\s+\w{1,3}\b', '', text)

        # Step 13: Restrict to allowed characters
        text = re.sub(r'[^\w\s.,!?₹$:/-]', '', text)

        # Step 14: Remove noise lines (after cleanup)
        text = TextCorrectionUtils.remove_noise_lines(config, text)

        # Step 15: Apply fuzzy replacements if defined
        fuzzy_corr = text_cleaning.get("fuzzy_replacements", {})
        if fuzzy_corr:
            text = TextCorrectionUtils.fuzzy_replace(text, fuzzy_corr, threshold=85)

        # Step 16: Uppercase key phrases
        for phrase in text_cleaning.get("key_phrases", []):
            text = re.sub(rf'\b{re.escape(phrase)}\b', phrase.upper(), text, flags=re.IGNORECASE)

        # Step 17: Add line breaks after known headings
        for heading in text_cleaning.get("add_linebreak_after", []):
            text = re.sub(rf'\b({re.escape(heading)})\b', r'\n\1', text, flags=re.IGNORECASE)

        return text.strip()

    def fuzzy_replace(text, corrections_dict, threshold=80):
        """
        Replace text using fuzzy matching.
        """
        for wrong, right in corrections_dict.items():
            # Check if the wrong word is similar enough to a correct word
            match_ratio = fuzz.ratio(wrong, right)
            if match_ratio >= threshold:
                text = text.replace(wrong, right)
        return text

    # --- Number Correction (unchanged but now called earlier) ---
    @staticmethod
    def correct_numbers(text):
        corrections = {
            r'(?<!\d)[Il](?=\d{2,})': '1',
            r'\bO(?=\d)': '0',
            r'(?<=\d)[Oo](?=\d)': '0',
            r'(?<=\d)\.(?=\d{3})': ',',  # e.g., 1.000 → 1,000
        }
        for pattern, repl in corrections.items():
            text = re.sub(pattern, repl, text)
        return text

    @staticmethod
    def remove_noise_lines(cfg, text: str) -> str:
        threshold = cfg.get("text_cleaning", {}).get("noise_line_threshold", 0.3)
        lines = text.splitlines()
        filtered = []
        for line in lines:
            clean_ratio = len(re.findall(r'\w', line)) / max(len(line), 1)
            if clean_ratio >= 0.3 and len(line.strip()) > 10:
                filtered.append(line)
        return '\n'.join(filtered)
