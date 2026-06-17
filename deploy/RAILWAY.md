# Deploying Meridian to Railway

Meridian ships as **one Railway service**: a multi-stage `Dockerfile` builds the
React frontend, then a Python image serves both the API and the built UI from the
same origin (so the SPA's relative `/api` calls work with no CORS/proxy).

`railway.json` tells Railway to use the Dockerfile and restart on failure.

## One-time setup (in the Railway dashboard — these steps need your login)

1. **Create the project from GitHub**
   New Project → **Deploy from GitHub repo** → authorize Railway's GitHub app →
   pick **`wpf002/meridian`**. Railway detects `railway.json` + `Dockerfile`.

2. **Auto-deploy is on by default.** Confirm under
   *Service → Settings → Source*: the deployment branch is **`main`** and
   "Auto Deploy" (deploy on push) is enabled. Every push to `main` now rebuilds
   and redeploys.

3. **Set environment variables** (*Service → Variables*). At minimum:
   ```
   ANTHROPIC_API_KEY = <your key>           # enables news sentiment
   AURORA_ENABLED    = true
   AURORA_BASE_URL   = https://backend-production-4975.up.railway.app/api
   UNIVERSE_SCAN_LIMIT = 0
   DB_PATH           = /app/data/meridian.db  # on the volume — see below
   ```
   Optional: `SENTIMENT_MODEL=claude-haiku-4-5`, `OUTCOME_PERIOD_DAYS=90`,
   `UNIVERSE_REFRESH_SECONDS=540`.
   (Do **not** commit these — they live only in Railway. `.env` is gitignored.)

4. **Persist the database** (recommended)
   The container filesystem is wiped on each deploy, so the SQLite DB (track
   record, model versions, alerts) would reset. Add a **Volume** and set
   `DB_PATH` to a file on it. Mount the volume at **`/app/data`** (NOT `/app/db`)
   and set `DB_PATH=/app/data/meridian.db`. Tables are created on first boot;
   the volume keeps history across deploys.
   ⚠️ Do not mount the volume at `/app/db` — that path holds `schema.sql` in the
   image, and an empty volume would hide it and crash startup. Keep the DB in a
   separate dir (`/app/data`).

5. **Expose it**
   *Service → Settings → Networking → Generate Domain*. The app binds `$PORT`
   automatically.

## Verifying a deploy

- `https://<your-domain>/api/health` → `{"status":"ok","signal_source":"AURORA"}`
- `https://<your-domain>/` → the console UI

## Notes

- The background warmer (live-data refresh, outcome grading, weight retune) runs
  inside the service as long as it's up — keep the service on a plan that doesn't
  sleep on idle if you want continuous refresh.
- AURORA must stay reachable at `AURORA_BASE_URL` for live data; without it the
  app falls back to manual signal files.
