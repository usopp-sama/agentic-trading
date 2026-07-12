"""Zerodha Kite login helper — get a daily access token.

Kite access tokens expire every morning (~6 AM IST) — that's Zerodha's rule,
not a bug here — so this is a once-a-day step before using Kite historical
data or a live Kite feed. Prerequisites (one-time):

  1. A Kite Connect app at https://developers.kite.trade/ — gives you an
     API key + API secret. Historical candles need the "Historical Data"
     add-on on the subscription.
  2. pip install kiteconnect
  3. Put the key/secret in .env:
       ATS_KITE_API_KEY=your_api_key
       ATS_KITE_API_SECRET=your_api_secret

Then run this and follow the two prompts:

    .venv/Scripts/python -m scripts.kite_login

It prints a login URL -> open it, log in, and you'll be redirected to your
app's Redirect URL with `?request_token=XXXX` in the address bar. Paste that
token back here; it exchanges it for the day's access_token and writes it to
the SAME DB-backed kv store the running server's /kite/callback route and
scripts/run_backtests.py --kite both read
(``ats.services.market_data.kite_history.set_access_token``).

IMPORTANT: that DB store takes precedence over ATS_KITE_ACCESS_TOKEN in
.env — so editing .env alone will NOT refresh an expired token if a login was
ever done through the dashboard or this script before. Always use this
script (or the dashboard's Kite Login button) to refresh the token; don't
hand-edit .env for it.
"""

from __future__ import annotations

import sys


def main() -> int:
    from ats.core.config import get_settings
    from ats.core.db import init_db
    from ats.services.market_data.kite_history import (
        KiteNotReady,
        exchange_request_token,
        login_url,
        set_access_token,
    )

    init_db()
    s = get_settings()
    if not (s.kite_api_key and s.kite_api_secret):
        print("Set ATS_KITE_API_KEY and ATS_KITE_API_SECRET in .env first "
              "(see this script's header).")
        return 2
    try:
        import kiteconnect  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        print(f"kiteconnect not installed ({exc}). Run: pip install kiteconnect")
        return 1

    print("\n1) Open this URL, log in, and authorise:\n")
    print("   " + login_url() + "\n")
    print("2) You'll be redirected to your app's redirect URL with "
          "?request_token=XXXX in the address bar.\n")
    pasted = input("Paste the request_token (or the whole redirect URL): ").strip()
    if not pasted:
        print("No token entered.")
        return 1

    if "request_token" in pasted:
        from urllib.parse import parse_qs, urlparse

        qs = parse_qs(urlparse(pasted).query)
        request_token = (qs.get("request_token") or [""])[0]
    else:
        request_token = pasted

    if not request_token:
        print("Could not find request_token in that input.")
        return 1

    try:
        access_token = exchange_request_token(request_token)
    except KiteNotReady as exc:
        print(f"Not ready: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Token exchange failed: {exc}")
        return 1

    set_access_token(access_token)
    print("\n✓ Logged in. access_token stored in the DB and active immediately")
    print("  for both the running server and any --kite script/backtest.")
    print("  It's valid until ~6 AM IST tomorrow; re-run this script daily.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
