# entity_extraction_utils.py
from __future__ import annotations
import requests
from typing import List, Dict, Any, Optional

from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    pipeline,
)


class EntityExtractionUtils:
    """Stateless helper that hides all model-loading / inference details."""

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg  # llm_postprocessing section
        self.mode = cfg.get("inference_mode", "local")
        model_name = cfg["models"].get("entity_extraction", "huyydangg/BERT-LAW")
        self.model_name = model_name

        if self.mode == "local":
            tok = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForTokenClassification.from_pretrained(model_name)
            # group_entities=True merges sub-word pieces into full tokens
            self.pipe = pipeline("ner", model=model, tokenizer=tok, grouped_entities=True)
        else:  # remote – expect a generic JSON API
            ep = cfg.get("remote_endpoint", {})
            self.url = ep["url"]
            self.api_key = ep.get("api_key")

    # ------------------------------------------------------------------ #
    def extract(self, text: str) -> List[Dict[str, Any]]:
        """Return list of {'text', 'type', 'start', 'end'} dicts."""
        if not text.strip():
            return []

        if self.mode == "local":
            preds = self.pipe(text)
        else:
            payload = {
                "text": text,
                "task": "entity_extraction",
                "model": self.model_name,
            }
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            rsp = requests.post(self.url, json=payload, headers=headers, timeout=30)
            rsp.raise_for_status()
            preds = rsp.json().get("entities", [])

        entities: List[Dict[str, Any]] = []
        for ent in preds:
            # HF = {'entity_group': 'ORG', 'word': 'ACME', 'start': 0 …}
            e_type = ent.get("entity") or ent.get("entity_group")
            txt = ent.get("word") or text[ent["start"]: ent["end"]]
            entities.append(
                {"text": txt, "type": e_type, "start": ent.get("start"), "end": ent.get("end")}
            )
        return entities
