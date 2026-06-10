"""A lightweight, rule-based screener.

Screens a universe of symbols (each described by a row of metrics)
against a set of declarative filters, and ranks the survivors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

# A filter maps a metrics DataFrame to a boolean mask.
Filter = Callable[[pd.DataFrame], "pd.Series[bool]"]


def min_filter(column: str, threshold: float) -> Filter:
    return lambda df: df[column] >= threshold


def max_filter(column: str, threshold: float) -> Filter:
    return lambda df: df[column] <= threshold


def between_filter(column: str, low: float, high: float) -> Filter:
    return lambda df: df[column].between(low, high)


@dataclass
class Screener:
    """Apply a chain of filters and rank the results.

    Example
    -------
    >>> s = Screener(filters=[max_filter("pe", 25), min_filter("roe", 0.15)])
    >>> result = s.run(metrics_df, rank_by="roe", ascending=False)
    """

    filters: list[Filter]

    def run(
        self,
        metrics: pd.DataFrame,
        rank_by: str | None = None,
        ascending: bool = True,
        top: int | None = None,
    ) -> pd.DataFrame:
        if metrics.empty:
            return metrics
        mask = pd.Series(True, index=metrics.index)
        for f in self.filters:
            mask &= f(metrics).fillna(False)
        result = metrics[mask].copy()
        if rank_by and rank_by in result.columns:
            result = result.sort_values(rank_by, ascending=ascending)
        if top is not None:
            result = result.head(top)
        return result
