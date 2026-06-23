# WEBESTIPTV Trial Automation — Apify Actor

Automates webestiptv.com account registration, 6-digit OTP email verification, and
free-trial activation, then extracts the Xtream/IPTV credentials and reports them to
the Apify dataset / `OUTPUT` key-value record (and optionally to a webhook and IBO
Player).

## Layout

| Path | Purpose |
| --- | --- |
| `webestiptv_automation.py` | Core Selenium automation (also runnable as a CLI). `run_automation()` returns the credentials or raises `TrialFailedError`. |
| `iptvvcanada_automation.py` | Shared helper module (disposable email, persona/UA generation, Selenium utilities, debug artifacts, `send_webhook_callback`). |
| `src/main.py` | Apify wrapper: input → env vars → `run_automation()` → dataset/OUTPUT/webhook. |
| `src/__main__.py` | Entry point (`python -m src`). |
| `.actor/actor.json` | Actor definition. |
| `.actor/input_schema.json` | Input fields shown in the Apify console. |
| `.actor/dataset_schema.json` | Dataset table view. |
| `Dockerfile` | Built on `apify/actor-python-selenium` (Chrome preinstalled). |
| `requirements.txt` | Python dependencies. |

## Deploy to Apify

```bash
# 1. Install the Apify CLI (once)
npm install -g apify-cli

# 2. Log in (get the token from https://console.apify.com/account/integrations)
apify login

# 3. From this directory, push the Actor (builds the Docker image on Apify)
apify push
```

`apify push` uploads the source, builds the image, and creates/updates the Actor in
your account. After it builds, run it from the console or with
`apify call webestiptv-trial`.

## Input

All fields are optional (see `.actor/input_schema.json`). Common ones:

- `useProxy` — attempt 1 uses the host's public IP, the rest rotate free proxies.
- `maxAttempts` — number of fresh-account attempts before failing.
- `emailBackend` — `tempmaillol` (default) or `mailtm`.
- `callbackUrl` / `webhookAuthToken` — POST the result to your backend.
- `iboPlayerEnabled` + `iboPlayerCookie` + `iboPlayerPlaylistName` — push the playlist
  to IBO Player.

## Output

On success the Actor pushes one dataset item and sets the `OUTPUT` record:

```json
{ "status": "success", "email": "...", "username": "...", "password": "...", "host": "...", "samsung_dns": "...", "m3u_url": "...", "ibo_saved": false }
```

On failure it records `{ "status": "failed", "error": "..." }` and the run is marked
failed.

## Run locally (without Apify)

```bash
pip install -r requirements.txt
python webestiptv_automation.py
```
