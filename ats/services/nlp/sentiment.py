"""Sentiment scoring.

Two backends, selected by ``ATS_NLP_SENTIMENT_MODEL`` ("auto" | "finbert" |
"vader"):

- **FinBERT** (``ProsusAI/finbert`` via ``transformers``): a finance-tuned
  transformer that understands market phrasing ("misses estimates", "guidance
  cut") far better than a generic lexicon. Preferred when the extras are
  installed.
- **VADER** (offline, dependency-light): a rule/lexicon scorer used as the
  always-available fallback so the system still runs on a laptop or Pi with no
  ``transformers``/``torch``.

``score()`` returns ``(label, score)`` with the label in
{"positive", "negative", "neutral"} and the score in ``[-1, 1]``. ``name``
reports which backend actually loaded so callers can record provenance.
"""

from __future__ import annotations

from ats.core.logging import get_logger

log = get_logger("ats.nlp.sentiment")

_POS, _NEG = 0.2, -0.2

# Backend selection modes accepted by ``ATS_NLP_SENTIMENT_MODEL``.
AUTO = "auto"
FINBERT = "finbert"
VADER = "vader"

# Cap chars before handing text to the transformer; the tokenizer still
# truncates to its 512-token limit, but this bounds pathological inputs cheaply.
_FINBERT_MAX_CHARS = 2000


class SentimentModel:
    """Sentiment scorer with a FinBERT-preferred, VADER-fallback backend.

    Parameters
    ----------
    model:
        ``"auto"`` (prefer FinBERT, fall back to VADER), ``"finbert"`` (force
        FinBERT; warn + fall back if it cannot load), or ``"vader"``.
    finbert_model:
        Hugging Face model id for the transformer backend.
    """

    def __init__(
        self,
        model: str = AUTO,
        finbert_model: str = "ProsusAI/finbert",
        finbert_download: bool = False,
    ) -> None:
        self._mode = (model or AUTO).strip().lower()
        self._finbert_model = finbert_model
        # When False (default) the transformer is loaded from local cache only
        # and NEVER triggers a network download at construction — critical
        # because the model is built during server startup, and a blocked/slow
        # download (e.g. behind a TLS-inspecting proxy) would otherwise hang the
        # boot. Provision weights out-of-band, then set this true only on a
        # network where the one-time fetch succeeds.
        self._finbert_download = finbert_download
        self._vader = None
        self._finbert = None
        self.name = "neutral"

        if self._mode in (AUTO, FINBERT):
            self._try_load_finbert()
        # VADER is always loaded as the fallback (cheap, no heavy deps), even
        # when FinBERT is the active backend, so a per-call transformer failure
        # can still degrade gracefully.
        self._load_vader()

        if self._finbert is not None:
            self.name = "finbert"
        elif self._vader is not None:
            self.name = "vader"
            if self._mode == FINBERT:
                log.warning("finbert_forced_but_unavailable_using_vader")
        else:  # pragma: no cover - both backends missing is a broken install
            log.warning("no_sentiment_backend_available")

    def _load_vader(self) -> None:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

            self._vader = SentimentIntensityAnalyzer()
        except Exception as exc:  # noqa: BLE001  pragma: no cover
            log.warning("vader_unavailable", extra={"error": str(exc)})

    def _try_load_finbert(self) -> None:  # pragma: no cover - heavy optional dep
        local_only = not self._finbert_download
        try:
            if self._finbert_download:
                # On managed/corporate networks a TLS-inspecting middlebox
                # presents a root CA that lives in the OS trust store but not in
                # the certifi bundle Python ships, so the download fails SSL
                # verification. truststore (when installed) routes Python's SSL
                # through the OS trust store, matching curl/native apps.
                # Best-effort: no-op without it.
                try:
                    import truststore

                    truststore.inject_into_ssl()
                except Exception:  # noqa: BLE001 - download may still work
                    pass

            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
                pipeline,
            )

            # Explicit from_pretrained so we can pin local_files_only on BOTH the
            # tokenizer and the model — pipeline() alone does not forward it.
            tokenizer = AutoTokenizer.from_pretrained(
                self._finbert_model, local_files_only=local_only
            )
            mdl = AutoModelForSequenceClassification.from_pretrained(
                self._finbert_model, local_files_only=local_only
            )
            self._finbert = pipeline(
                "sentiment-analysis", model=mdl, tokenizer=tokenizer
            )
            log.info("finbert_loaded", extra={"model": self._finbert_model})
        except Exception as exc:  # noqa: BLE001
            # Not cached (and download disabled), transformers missing, or a load
            # error — VADER takes over. With local_only this fails fast (no
            # network), so it can't stall server startup.
            log.info(
                "finbert_unavailable_using_vader",
                extra={"error": str(exc), "local_only": local_only},
            )

    def score(self, text: str) -> tuple[str, float]:
        if not text or not text.strip():
            return "neutral", 0.0
        if self._finbert is not None:
            score = self._score_finbert(text)
            if score is not None:
                return score
        if self._vader is not None:
            compound = self._vader.polarity_scores(text)["compound"]
            return self._label(compound), round(compound, 4)
        return "neutral", 0.0

    def _score_finbert(self, text: str) -> tuple[str, float] | None:  # pragma: no cover
        try:
            res = self._finbert(text[:_FINBERT_MAX_CHARS], truncation=True)[0]
        except Exception as exc:  # noqa: BLE001 - one bad item must not abort scoring
            log.warning("finbert_score_failed_falling_back", extra={"error": str(exc)})
            return None
        label = str(res.get("label", "neutral")).lower()
        sign = {"positive": 1.0, "negative": -1.0}.get(label, 0.0)
        return label, round(sign * float(res.get("score", 0.0)), 4)

    @staticmethod
    def _label(score: float) -> str:
        if score >= _POS:
            return "positive"
        if score <= _NEG:
            return "negative"
        return "neutral"


def build_sentiment_model(settings=None) -> SentimentModel:
    """Construct the sentiment model from settings (mirrors the build_* pattern).

    Falls back to defaults when settings are unavailable so callers/tests can
    construct it without a full settings object.
    """
    if settings is None:
        try:
            from ats.core.config import get_settings

            settings = get_settings()
        except Exception:  # noqa: BLE001 - defaults are a safe fallback
            settings = None
    mode = getattr(settings, "nlp_sentiment_model", AUTO)
    finbert_model = getattr(settings, "nlp_finbert_model", "ProsusAI/finbert")
    finbert_download = getattr(settings, "nlp_finbert_download", False)
    return SentimentModel(
        model=mode, finbert_model=finbert_model, finbert_download=finbert_download
    )
