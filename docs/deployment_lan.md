# Running the dashboard on your home network (LAN)

Goal: run the trading server on one "server laptop" and open the dashboard from
any other laptop or phone on the same Wi-Fi/router.

> **Security first.** This binds the server to your local network. Do **not**
> port-forward it or expose it to the public internet without a reverse proxy +
> TLS + authentication (or a VPN like Tailscale). Anyone on your LAN who can
> reach the port can use the dashboard — set `ATS_DASHBOARD_TOKEN` if your
> network isn't trusted.

## 1. Configure the bind address

By default the server binds to `127.0.0.1` (this machine only). To serve the
LAN, set the host to `0.0.0.0` via environment variables (or a `.env` file in
the repo root):

```bash
# .env  (repo root)
ATS_HOST=0.0.0.0
ATS_PORT=8000
# optional shared secret for access (recommended on untrusted networks)
# ATS_DASHBOARD_TOKEN=choose-a-long-random-string
```

These map to `host` / `port` / `dashboard_token` in `ats/core/config.py`.

## 2. Find the server laptop's IP

- **Linux:** `ip addr show | grep "inet "` (look for `192.168.x.x` / `10.x.x.x`)
- **macOS:** `ipconfig getifaddr en0` (Wi-Fi) or `en1`
- **Windows:** `ipconfig` → "IPv4 Address"

Say it's `192.168.1.42`.

## 3. Run it

```bash
# from the repo root, with the venv active
python -m ats.server
```

You should see uvicorn listening on `0.0.0.0:8000`. From any other device on
the same network, open:

```
http://192.168.1.42:8000
```

### `.local` hostname (mDNS, no IP needed)

Most networks support mDNS, so you can often use the laptop's hostname instead
of the IP:

```
http://<server-hostname>.local:8000
```

(`hostname` on macOS/Linux; macOS/Linux ship mDNS; on Windows install Bonjour or
enable mDNS.)

## 4. Open the firewall port

- **Linux (ufw):** `sudo ufw allow 8000/tcp`
- **Linux (firewalld):** `sudo firewall-cmd --add-port=8000/tcp --permanent && sudo firewall-cmd --reload`
- **macOS:** System Settings → Network → Firewall → allow incoming for Python, or `Firewall Options…`.
- **Windows:** "Windows Defender Firewall → Advanced → Inbound Rules → New Rule → Port 8000 → Allow", scope to **Private** networks only.

## 5. Run it as an always-on service

### Linux — systemd

`/etc/systemd/system/ats.service`:

```ini
[Unit]
Description=Agentic Trading Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/gsoc
EnvironmentFile=/home/youruser/gsoc/.env
ExecStart=/home/youruser/gsoc/.venv/bin/python -m ats.server
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ats
sudo systemctl status ats
journalctl -u ats -f      # follow logs
```

### macOS — launchd

`~/Library/LaunchAgents/com.ats.server.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.ats.server</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/youruser/gsoc/.venv/bin/python</string>
    <string>-m</string><string>ats.server</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/youruser/gsoc</string>
  <key>EnvironmentVariables</key>
  <dict><key>ATS_HOST</key><string>0.0.0.0</string><key>ATS_PORT</key><string>8000</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.ats.server.plist
launchctl list | grep com.ats.server
```

### Docker Compose (recommended — works on Windows too)

This is the simplest "one command" path and the only one that does **not** care
whether the host is Windows, macOS, or Linux: the app runs inside a Linux
container via Docker Desktop (WSL2 on Windows). You do **not** install Python on
the host.

**One-time setup on the server laptop:**

1. Install Docker Desktop and make sure it's running.
2. Get the code: `git clone <repo>` (or copy the folder) and `cd` into it.
3. Create the secrets file at the **repo root**:
   - copy `deploy/.env.example` to `.env`
   - fill in your `ATS_LLM_*` keys (e.g. the Gemini key) so the SMEs reason for real
   - optionally set `ATS_DASHBOARD_TOKEN` to a long random string

**Launch (lean profile — SQLite + in-memory bus, nothing else to manage):**

```bash
# from the repo root
docker compose -f deploy/docker-compose.lan.yml up -d --build
```

That's it. The container binds to `0.0.0.0:8000` on the host by default, so from
any device on the same Wi-Fi open `http://<server-ip>:8000` (find the IP via
step 2 above). To restrict to this machine only, set `ATS_BIND=127.0.0.1` in
`.env`. Logs: `docker compose -f deploy/docker-compose.lan.yml logs -f`.
Stop: `docker compose -f deploy/docker-compose.lan.yml down`.

**Scaled profile (Postgres/TimescaleDB + Redis)** — only when you outgrow
SQLite. Requires a strong `POSTGRES_PASSWORD` in `.env`; defaults to
localhost-only (front it with a reverse proxy / VPN, or set `ATS_BIND=0.0.0.0`
on a trusted network):

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

## 6. Access securely from anywhere (optional) — Tailscale

For reaching it away from home without exposing a port:

1. Install Tailscale on the server laptop and your client devices, sign in to the same tailnet.
2. Keep `ATS_HOST=0.0.0.0`; reach it at the server's Tailscale IP (`100.x.y.z:8000`)
   or via MagicDNS hostname. Traffic is end-to-end encrypted; nothing is public.

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Works on the server at `localhost:8000` but not from other devices | Still bound to `127.0.0.1` — set `ATS_HOST=0.0.0.0` and restart. |
| Connection refused / times out from another device | Firewall blocking the port (step 4); or devices on different networks/VLANs (guest Wi-Fi often isolates clients). |
| `<host>.local` doesn't resolve | mDNS not available on the client — use the raw IP. |
| Live data is empty | Expected offline; set `ATS_DATA_SOURCE=nse_live` for live, or it falls back to `yfinance`/`synthetic`. |
| Want a login prompt | Set `ATS_DASHBOARD_TOKEN`; open `http://<ip>:8000/?token=...` once. |
