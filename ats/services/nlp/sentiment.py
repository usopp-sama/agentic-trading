"""Sentiment scoring.

Default: VADER (offline, fast). Optional: FinBERT via transformers if installed
and enabled (``ATS_*`` not required; controlled by availability). Returns a
label and a score in [-1, 1].
"""

from __future__ import annotations

from ats.core.logging import get_logger

log = get_logger("ats.nlp.sentiment")

_POS, _NEG = 0.2, -0.2


class SentimentModel:
    def __init__(self, prefer_finbert: bool = False) -> None:
        self._vader = None
        self._finbert = None
        if prefer_finbert:
            self._try_load_finbert()
        self._load_vader()

    def _load_vader(self) -> None:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

            self._vader = SentimentIntensityAnalyzer()
        except Exception as exc:  # noqa: BLE001  pragma: no cover
            log.warning("vader_unavailable", extra={"error": str(exc)})

    def _try_load_finbert(self) -> None:  # pragma: no cover - heavy optional dep
        try:
            from transformers import pipeline

            self._finbert = pipeline("sentiment-analysis", model="ProsusAI/finbert")
            log.info("finbert_loaded")
        except Exception as exc:  # noqa: BLE001
            log.info("finbert_unavailable_using_vader", extra={"error": str(exc)})

    def score(self, text: str) -> tuple[str, float]:
        if not text or not text.strip():
            return "neutral", 0.0
        if self._finbert is not None:  # pragma: no cover
            res = self._finbert(text[:512])[0]
            label = res["label"].lower()
            sign = {"positive": 1.0, "negative": -1.0}.get(label, 0.0)
            return label, round(sign * float(res["score"]), 4)
        if self._vader is not None:
            compound = self._vader.polarity_scores(text)["compound"]
            return self._label(compound), round(compound, 4)
        return "neutral", 0.0

    @staticmethod
    def _label(score: float) -> str:
        if score >= _POS:
            return "positive"
        if score <= _NEG:
            return "negative"
        return "neutral"
