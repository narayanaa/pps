# structural_segmentation_utils.py
from __future__ import annotations
import re
from typing import List, Dict, Any
import requests
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline


class StructuralSegmentationUtils:
    """
    A two-step hybrid:
      1.  Rules/regex to propose split points (cheap, domain-specific).
      2.  LM to label each chunk (headings OR context) with a section tag.
    """

    DEFAULT_RULES = [
        r"^\s*WHEREAS\b", r"^\s*NOW\s+THEREFORE\b", r"^\s*WITNESSETH\b",
        r"^\s*SCHEDULE\s+OF\s+THE\s+PROPERTY\b", r"^\s*BOUNDARIES\b"
    ]

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg  = cfg
        self.mode = cfg.get("inference_mode", "local")
        self.rgx  = [re.compile(pat, re.IGNORECASE) for pat in self.DEFAULT_RULES]
        model_name = cfg["models"].get("structural_segmentation", "law-ai/InLegalBERT")
        self.model_name = model_name

        if self.mode == "local":
            tok = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            # we’ll get logits → labels via HF pipeline
            self.pipe = pipeline("text-classification", model=model, tokenizer=tok)
        else:
            ep = cfg.get("remote_endpoint", {})
            self.url = ep["url"]
            self.api_key = ep.get("api_key")

    # ------------------------------------------------------------------ #
    def _split(self, text: str) -> List[str]:
        """Rough paragraph/section splitter using regex cues + blank lines."""
        # primary split on blank line
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        # ensure we split whenever rule matches start of a string
        refined: List[str] = []
        for p in paras:
            # if the rule matches inside (rare), split further
            start_idx = 0
            for m in sorted(
                (rgx.search(p) for rgx in self.rgx if rgx.search(p)),
                key=lambda m: m.start(),
            ):
                if m.start() > start_idx:
                    refined.append(p[start_idx : m.start()].strip())
                refined.append(p[m.start() :].strip())
                start_idx = len(p)  # consumed
            if start_idx == 0:      # no rule inside
                refined.append(p)
        return [x for x in refined if x]

    # ------------------------------------------------------------------ #
    def segment(self, text: str) -> List[Dict[str, Any]]:
        """
        Returns list of {'label', 'text', 'start_char', 'end_char'}
        """
        chunks: List[str] = self._split(text)
        sections: List[Dict[str, Any]] = []
        cursor = 0
        for chunk in chunks:
            if self.mode == "local":
                pred = self.pipe(chunk, truncation=True)[0]["label"]
            else:
                payload = {
                    "text": chunk,
                    "task": "structural_segmentation",
                    "model": self.model_name,
                }
                headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                rsp = requests.post(self.url, json=payload, headers=headers, timeout=30)
                rsp.raise_for_status()
                pred = rsp.json().get("label")
            start = cursor
            end   = cursor + len(chunk)
            sections.append({"label": pred, "text": chunk, "start": start, "end": end})
            cursor = end + 1  # +1 for newline between chunks
        return sections
