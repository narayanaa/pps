"""Utilities for document‑type classification.

Features
--------
* **Fast heuristics** when a pre‑trained model is absent (works out‑of‑the‑box).
* Optional **scikit‑learn pipeline** (`LogisticRegression`) – just call `train(...)`.
* Pure‑Python; safe to import even if scikit‑learn is not installed.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence
import yaml

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    SKLEARN_AVAILABLE = True
except ModuleNotFoundError:
    SKLEARN_AVAILABLE = False

import pdfplumber  # type: ignore
from ..utils.layout_utils import LayoutUtils

logger = logging.getLogger(__name__)

LABELS: Sequence[str] = ("generic", "research_paper", "report")


@dataclass
class ClassificationResult:
    label: str
    confidence: float | None = None


class ClassificationUtils:
    """Classifies a PDF document into a high-level document type with domain support."""

    def __init__(self, config_path: str = "models_config.yaml"):
        self.config = self._load_config(config_path)
        self.models: Dict[str, Pipeline] = {}
        self._load_domain_models()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load model configuration from YAML."""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found. Using defaults.")
            return {}

    def _load_domain_models(self):
        """Load domain-specific models from config."""
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not installed. Skipping model loading.")
            return
        import joblib
        for domain, model_path in self.config.get("models", {}).items():
            try:
                self.models[domain] = joblib.load(model_path)
                logger.info(f"Loaded model for domain '{domain}' from {model_path}")
            except Exception as e:
                logger.error(f"Failed to load model for domain '{domain}': {e}")

    def extract_features(self, doc: pdfplumber.PDF, domain: str = "generic") -> Dict[str, Any]:
        """Extract features for classification, with domain-specific enhancements."""
        first_page = doc.pages[0]
        text = (first_page.extract_text() or "").lower()
        features = {
            "word_count": len(text.split()),
            "has_references": any(t in text for t in ("references", "bibliography")),
            "column_count": LayoutUtils().detect_columns(first_page),
            "has_abstract": "abstract" in text,
            "has_introduction": "introduction" in text,
        }
        if domain == "ectd":
            features["has_clinical_study"] = "clinical study" in text
        elif domain == "gdpr":
            features["has_data_protection"] = "data protection" in text
        return features

    def classify(self, doc: pdfplumber.PDF, domain: str = "generic") -> ClassificationResult:
        """Classify the document using a domain-specific model or heuristics."""
        if SKLEARN_AVAILABLE and domain in self.models:
            flat_text = "\n".join(p.extract_text() or "" for p in doc.pages)
            pred_proba = self.models[domain].predict_proba([flat_text])[0]
            max_idx = int(pred_proba.argmax())
            label = LABELS[max_idx]
            return ClassificationResult(label=label, confidence=float(pred_proba[max_idx]))
        else:
            features = self.extract_features(doc, domain)
            if features.get("has_abstract") and features.get("has_introduction") and features.get("column_count",
                                                                                                  0) > 1:
                label = "research_paper"
            elif features.get("word_count", 0) > 3000 and features.get("has_references"):
                label = "report"
            else:
                label = "generic"
            return ClassificationResult(label=label)

    def train(self, pdf_paths: List[Path], labels: List[str], domain: str = "generic"):
        """Train a model for a specific domain."""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn must be installed to train the model.")
        texts = []
        for p in pdf_paths:
            with pdfplumber.open(p) as doc:
                texts.append("\n".join(page.extract_text() or "" for page in doc.pages))
        model = Pipeline([
            ("tfidf", TfidfVectorizer(stop_words="english", max_features=50_000)),
            ("clf", LogisticRegression(max_iter=2_000)),
        ])
        model.fit(texts, labels)
        self.models[domain] = model
        logger.info(f"Model trained for domain '{domain}' on {len(pdf_paths)} samples")
