"""NSE trading calendar and market hours (Indian market).

The NSE equity segment trades Monday-Friday, 09:15-15:30 IST, minus the
exchange holiday list published each year. IST is a fixed UTC+5:30 with
no daylight saving, so a fixed-offset timezone is exact.

The holiday list must be refreshed annually from the NSE circular (or
nseindia.com > Market Timings & Holidays). For years we have no list
for, the calendar degrades to weekday+hours checks only and callers can
log the gap.

Pure functions of a datetime, so trivially testable.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), name="IST")

MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)

# NSE equity-segment trading holidays. Source: NSE circular for 2026
# (cross-checked via cleartax.in/s/nse-holidays-2026). Muhurat trading
# (2026-11-08, a Sunday) is intentionally NOT modeled — it is a special
# session announced separately by the exchange.
NSE_HOLIDAYS: dict[int, frozenset[date]] = {
    2026: frozenset(
        {
            date(2026, 1, 15),   # Maharashtra municipal elections
            date(2026, 1, 26),   # Republic Day
            date(2026, 3, 3),    # Holi
            date(2026, 3, 26),   # Shri Ram Navami
            date(2026, 3, 31),   # Shri Mahavir Jayanti
            date(2026, 4, 3),    # Good Friday
            date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
            date(2026, 5, 1),    # Maharashtra Day
            date(2026, 5, 28),   # Bakri Id
            date(2026, 6, 26),   # Muharram
            date(2026, 9, 14),   # Ganesh Chaturthi
            date(2026, 10, 2),   # Mahatma Gandhi Jayanti
            date(2026, 10, 20),  # Dussehra
            date(2026, 11, 10),  # Diwali - Balipratipada
            date(2026, 11, 24),  # Prakash Gurpurb Sri Guru Nanak Dev
            date(2026, 12, 25),  # Christmas
        }
    ),
}


def to_ist(dt: datetime) -> datetime:
    """Convert any aware datetime to IST; naive datetimes are assumed UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def has_holiday_data(year: int) -> bool:
    return year in NSE_HOLIDAYS


def is_trading_day(d: date) -> bool:
    """Weekday and not an exchange holiday (best-effort for unknown years)."""
    if d.weekday() >= 5:  # Saturday/Sunday
        return False
    return d not in NSE_HOLIDAYS.get(d.year, frozenset())


def is_market_open(now: datetime | None = None) -> bool:
    """True during the NSE equity continuous session (09:15-15:30 IST)."""
    ist = to_ist(now if now is not None else datetime.now(timezone.utc))
    if not is_trading_day(ist.date()):
        return False
    return MARKET_OPEN <= ist.time() < MARKET_CLOSE


def is_polling_window(
    now: datetime | None = None, grace_minutes: int = 45
) -> bool:
    """Market hours plus a post-close grace window.

    Live data sources keep polling briefly after the close so the final
    settled bar of the day is captured; outside that, polling a closed
    market is wasted API quota.
    """
    ist = to_ist(now if now is not None else datetime.now(timezone.utc))
    if not is_trading_day(ist.date()):
        return False
    close_dt = datetime.combine(ist.date(), MARKET_CLOSE, tzinfo=IST)
    grace_end = (close_dt + timedelta(minutes=grace_minutes)).time()
    return MARKET_OPEN <= ist.time() < grace_end
