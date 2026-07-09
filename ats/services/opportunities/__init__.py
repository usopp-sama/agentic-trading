"""Opportunity aggregation: join signals + SME opinions + decisions per symbol
into a ranked, plain-English list of money-making setups the algos found."""

from ats.services.opportunities.aggregator import (
    build_opportunities,
    opportunity_detail,
)

__all__ = ["build_opportunities", "opportunity_detail"]
