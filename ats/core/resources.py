"""Process + host resource sampling for the Ops Console (P4.3).

Honest about what Python can measure: process RSS/CPU come from ``psutil`` when
it is installed (``pip install psutil``); otherwise we report the always-
available filesystem metrics (DB + WAL + log sizes) and flag RSS/CPU as
unavailable. No per-module RAM attribution is invented — the total is measured,
the estimates are labelled.
"""

from __future__ import annotations

import os


def _mb(path: str | None) -> float | None:
    if not path:
        return None
    try:
        return round(os.path.getsize(path) / 1e6, 2)
    except OSError:
        return None


def _dir_mb(path: str) -> float | None:
    try:
        total = 0
        for root, _dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
        return round(total / 1e6, 2)
    except OSError:
        return None


def resource_sample() -> dict:
    """A point sample of process + host resources (best-effort, honest)."""
    from ats.core.config import get_settings

    out: dict = {"psutil": False}

    try:
        import psutil

        p = psutil.Process(os.getpid())
        with p.oneshot():
            out.update(
                psutil=True,
                rss_mb=round(p.memory_info().rss / 1e6, 1),
                cpu_pct=round(p.cpu_percent(interval=0.0), 1),
                threads=p.num_threads(),
            )
        vm = psutil.virtual_memory()
        out["host_mem_used_pct"] = vm.percent
        out["host_mem_total_gb"] = round(vm.total / 1e9, 1)
    except Exception:  # noqa: BLE001 — psutil absent/blocked: filesystem metrics still work
        out["note"] = "install psutil for process RSS/CPU (pip install psutil)"

    s = get_settings()
    db_path = s.db_url[len("sqlite:///"):] if s.db_url.startswith("sqlite:///") else None
    out["db_mb"] = _mb(db_path)
    out["wal_mb"] = _mb((db_path + "-wal") if db_path else None)
    try:
        out["log_dir_mb"] = _dir_mb(s.log_dir) if getattr(s, "log_dir", None) else None
    except Exception:  # noqa: BLE001
        out["log_dir_mb"] = None
    return out
