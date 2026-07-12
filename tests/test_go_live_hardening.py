"""Tests for L6 go-live hardening: health-transition alerting, the pre-open
GO/NO-GO decision, and the nightly SQLite backup."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ats.services.watchdog.preopen import evaluate_preopen, format_preopen
from ats.services.watchdog.service import diff_health


# --- component-health edge detection ---------------------------------------
def test_diff_health_edge_triggers_bad_and_recovery():
    prev = {"a": "OK", "b": "OK", "c": "DOWN"}
    cur = {"a": "DEGRADED", "b": "OK", "c": "OK"}
    newly_bad, recovered = diff_health(prev, cur)
    assert newly_bad == ["a"]        # OK -> DEGRADED
    assert recovered == ["c"]        # DOWN -> OK
    # b unchanged (OK -> OK) appears in neither list.


def test_diff_health_no_repeat_while_still_bad():
    prev = {"a": "DOWN"}
    cur = {"a": "DEGRADED"}          # still bad — no fresh alert
    newly_bad, recovered = diff_health(prev, cur)
    assert newly_bad == [] and recovered == []


def test_diff_health_first_seen_bad_alerts():
    newly_bad, recovered = diff_health({}, {"x": "DOWN"})
    assert newly_bad == ["x"] and recovered == []


# --- pre-open GO/NO-GO ------------------------------------------------------
def test_evaluate_preopen_go_when_all_hard_pass():
    checks = [
        {"name": "data_feed", "ok": True, "hard": True},
        {"name": "disk", "ok": True, "hard": True},
        {"name": "llm", "ok": False, "hard": False},   # soft failure ignored
    ]
    r = evaluate_preopen(checks)
    assert r["go"] is True and r["failed"] == []


def test_evaluate_preopen_nogo_lists_failed_hard_checks():
    checks = [
        {"name": "data_feed", "ok": False, "hard": True},
        {"name": "kite_token", "ok": False, "hard": True},
        {"name": "disk", "ok": True, "hard": True},
    ]
    r = evaluate_preopen(checks)
    assert r["go"] is False
    assert set(r["failed"]) == {"data_feed", "kite_token"}


def test_format_preopen_subject_reflects_verdict():
    go_msg = format_preopen(evaluate_preopen([{"name": "disk", "ok": True, "hard": True}]))
    assert go_msg.splitlines()[0].startswith("PRE-OPEN GO")
    nogo_msg = format_preopen(evaluate_preopen([{"name": "disk", "ok": False, "hard": True}]))
    assert nogo_msg.splitlines()[0].startswith("PRE-OPEN NO-GO")
    assert "disk" in nogo_msg


# --- nightly backup ---------------------------------------------------------
def test_backup_once_snapshots_and_prunes(tmp_path: Path):
    from scripts.backup import backup_once

    db = tmp_path / "ats.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE t (v INTEGER)")
    con.execute("INSERT INTO t VALUES (42)")
    con.commit()
    con.close()

    dest = tmp_path / "backups"
    # Three snapshots with retention 2 -> oldest pruned, 2 kept.
    made = []
    for _ in range(3):
        made.append(backup_once(db, dest, retention=2))
    kept = sorted(dest.glob("ats-*.db"))
    assert len(kept) == 2
    assert made[0].name not in {p.name for p in kept}   # oldest pruned

    # The snapshot is a real, readable copy of the data.
    latest = sqlite3.connect(kept[-1])
    assert latest.execute("SELECT v FROM t").fetchone()[0] == 42
    latest.close()
