"""Zerodha Kite login helper — get a daily access token.

Kite access tokens expire every morning (~6 AM IST), so this is a once-a-day
step before using Kite historical data. Prerequisites (one-time):

  1. A Kite Connect app at https://developers.kite.trade/ — gives you an
     API key + API secret. Historical candles need the "Historical Data"
     add-on on the subscription.
  2. pip install kiteconnect
  3. Put the key/secret in .env:
       ATS_KITE_API_KEY=your_api_key
       ATS_KITE_API_SECRET=your_api_secret

Then run this and follow the two prompts:

    .venv/Scripts/python -m scripts.kite_login

It prints a login URL → open it, log in, and you'll be redirected to your
app's redirect URL with `?request_token=XXXX` in the address bar. Paste that
token back here; it exchanges it for an access token and prints the line to add
to .env:  ATS_KITE_ACCESS_TOKEN=...
"""

from __future__ import annotations

import sys

from ats.core.config import get_settings


def main() -> int:
    s = get_settings()
    if not (s.kite_api_key and s.kite_api_secret):
        print("Set ATS_KITE_API_KEY and ATS_KITE_API_SECRET in .env first "
              "(see this script's header).")
        return 2
    try:
        from kiteconnect import KiteConnect
    except Exception as exc:  # noqa: BLE001
        print(f"kiteconnect not installed ({exc}). Run: pip install kiteconnect")
        return 1

    kite = KiteConnect(api_key=s.kite_api_key)
    print("\n1) Open this URL, log in, and authorise:\n")
    print("   " + kite.login_url() + "\n")
    print("2) You'll be redirected to your app's redirect URL with "
          "?request_token=XXXX in the address bar.\n")
    request_token = input("Paste the request_token here: ").strip()
    if not request_token:
        print("No token entered.")
        return 1
    try:
        data = kite.generate_session(request_token, api_secret=s.kite_api_secret)
    except Exception as exc:  # noqa: BLE001
        print(f"Token exchange failed: {exc}")
        return 1
    token = data["access_token"]
    print("\n✓ Success. Add this line to .env (replace any existing one):\n")
    print(f"   ATS_KITE_ACCESS_TOKEN={token}\n")
    print("It's valid until ~6 AM IST tomorrow; re-run this script daily.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
