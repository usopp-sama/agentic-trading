"""Service wiring.

Builds the orchestrator and registers all services. This is the single place
that knows the full service graph; it grows as phases are implemented.

Each registration is fault-isolated: a service whose module is not yet present
or whose optional dependency is missing is simply skipped (logged), so the
server always boots and the dashboard always comes up.
"""

from __future__ import annotations

from ats.core.logging import get_logger
from ats.server.orchestrator import Orchestrator

log = get_logger("ats.wiring")

# (module path, class name). Order is for readability only; coordination is via
# the event bus and scheduler.
_SERVICES = [
    ("ats.services.market_data.service", "MarketDataService"),
    ("ats.services.regime.service", "RegimeService"),
    ("ats.services.fundamentals.service", "FundamentalsService"),
    ("ats.services.options_data.service", "OptionsDataService"),
    ("ats.services.scraper.service", "ScraperService"),
    ("ats.services.nlp.service", "NlpService"),
    ("ats.services.strategies.service", "StrategyService"),
    ("ats.services.knowledge.service", "KnowledgeService"),
    ("ats.services.agents.service", "AgentService"),
    ("ats.services.risk.service", "RiskService"),
    ("ats.services.execution.service", "ExecutionService"),
    ("ats.services.learning.service", "LearningService"),
    ("ats.services.rules.service", "RulesService"),
    ("ats.services.dashboard.service", "DashboardService"),
]


def build_orchestrator() -> Orchestrator:
    import importlib

    orch = Orchestrator()
    for module_path, class_name in _SERVICES:
        try:
            module = importlib.import_module(module_path)
            service_cls = getattr(module, class_name)
            orch.register(service_cls())
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "service_not_registered",
                extra={"svc_module": module_path, "error": str(exc)},
            )
    return orch
