"""Tests for news sentiment scoring + backend selection.

These run fully offline: VADER ships as a hard dependency, while the FinBERT
transformer path is exercised by injecting a fake pipeline so the suite never
imports ``transformers``/``torch`` or hits the network.
"""

from __future__ import annotations

from ats.services.nlp.sentiment import (
    AUTO,
    FINBERT,
    VADER,
    SentimentModel,
    build_sentiment_model,
)


def test_vader_scores_positive_negative_neutral():
    model = SentimentModel(model=VADER)
    assert model.name == "vader"

    pos_label, pos_score = model.score("Profits surge to a record high; outlook excellent")
    assert pos_label == "positive"
    assert pos_score > 0

    neg_label, neg_score = model.score("Company collapses amid fraud; catastrophic losses")
    assert neg_label == "negative"
    assert neg_score < 0


def test_empty_text_is_neutral_zero():
    model = SentimentModel(model=VADER)
    assert model.score("") == ("neutral", 0.0)
    assert model.score("   ") == ("neutral", 0.0)


def test_score_in_unit_range():
    model = SentimentModel(model=VADER)
    for text in ["great beat", "terrible miss", "the company exists"]:
        _, score = model.score(text)
        assert -1.0 <= score <= 1.0


def test_forced_finbert_falls_back_to_vader_when_weights_unavailable():
    # Default finbert_download=False -> load is local-cache-only. With no cached
    # weights (and/or no transformers), forcing FinBERT must degrade to VADER
    # rather than crash or hit the network. A bogus model id guarantees the
    # local-only load fails regardless of what's cached on this machine (so the
    # test is deterministic even where real FinBERT weights are provisioned).
    model = SentimentModel(model=FINBERT, finbert_model="ats-test/nonexistent-model")
    assert model.name == "vader"
    label, _ = model.score("Earnings beat expectations")
    assert label in {"positive", "negative", "neutral"}


def test_finbert_load_does_not_download_by_default():
    # Safety invariant: constructing the model must never trigger a network
    # download (which could hang server startup). The default keeps the load
    # local-only.
    model = SentimentModel(model=FINBERT)
    assert model._finbert_download is False


class _FakeFinbert:
    """Stand-in for a transformers sentiment pipeline."""

    def __init__(self, label: str, score: float) -> None:
        self._label, self._score = label, score
        self.calls: list[dict] = []

    def __call__(self, text, **kwargs):
        self.calls.append({"text": text, "kwargs": kwargs})
        return [{"label": self._label, "score": self._score}]


def test_finbert_label_and_sign_mapping():
    model = SentimentModel(model=VADER)  # start with a known-good fallback
    model._finbert = _FakeFinbert("Positive", 0.93)
    model.name = "finbert"
    assert model.score("guidance raised") == ("positive", 0.93)

    model._finbert = _FakeFinbert("Negative", 0.80)
    assert model.score("guidance cut") == ("negative", -0.8)

    model._finbert = _FakeFinbert("Neutral", 0.99)
    assert model.score("the filing was submitted") == ("neutral", 0.0)


def test_finbert_truncates_long_input():
    model = SentimentModel(model=VADER)
    fake = _FakeFinbert("Positive", 0.5)
    model._finbert = fake
    model.score("x" * 10_000)
    assert fake.calls[0]["kwargs"].get("truncation") is True
    assert len(fake.calls[0]["text"]) <= 2000


def test_finbert_failure_falls_back_to_vader_at_call_time():
    class _Boom:
        def __call__(self, *a, **k):
            raise RuntimeError("cuda oom")

    model = SentimentModel(model=VADER)
    model._finbert = _Boom()
    # Should not raise; falls through to the VADER backend.
    label, score = model.score("Profits surge to a record high")
    assert label == "positive"
    assert score > 0


def test_build_from_settings_respects_mode():
    class _S:
        nlp_sentiment_model = VADER
        nlp_finbert_model = "ProsusAI/finbert"

    model = build_sentiment_model(_S())
    assert model.name == "vader"


def test_auto_mode_loads_a_valid_backend():
    model = SentimentModel(model=AUTO)
    # No transformers installed in CI -> VADER; with it -> finbert. Either is a
    # real backend (never the broken "neutral" sentinel).
    assert model.name in {"finbert", "vader"}
