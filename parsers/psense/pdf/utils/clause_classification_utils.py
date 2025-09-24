# clause_classification_utils.py
from __future__ import annotations
from typing import List, Dict, Any
import requests
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline


class ClauseClassificationUtils:
    """Classify each clause (or section) into a legal topic label."""

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.mode = cfg.get("inference_mode", "local")
        model_name = cfg["models"].get("clause_classification", "nlpaueb/legal-bert-small-uncased")
        self.model_name = model_name

        if self.mode == "local":
            tok = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.pipe = pipeline("text-classification", model=model, tokenizer=tok)
        else:
            ep = cfg.get("remote_endpoint", {})
            self.url = ep["url"]
            self.api_key = ep.get("api_key")

    # ------------------------------------------------------------------ #
    def classify(self, clauses: List[str]) -> List[Dict[str, Any]]:
        """
        Each clause -> {'text', 'label', 'score'}
        """
        results = []
        if self.mode == "local":
            preds = self.pipe(clauses, truncation=True)
            for clause, pred in zip(clauses, preds):
                results.append(
                    {"text": clause, "label": pred["label"], "score": float(pred["score"])}
                )
        else:
            payload = {
                "clauses": clauses,
                "task": "clause_classification",
                "model": self.model_name,
            }
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            rsp = requests.post(self.url, json=payload, headers=headers, timeout=60)
            rsp.raise_for_status()
            results = rsp.json().get("predictions", [])
        return results
