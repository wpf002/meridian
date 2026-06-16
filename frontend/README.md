# Meridian Frontend

A React dashboard for the Meridian financial-intelligence engine. It is a thin
view layer over the [Meridian HTTP API](../api) — all scoring happens in the
Python engine; the frontend only reads and renders.

Stack: **React 18 · Vite · Tailwind · Recharts · axios** (matches the bloomberg
and syntrackr frontends).

## Run

The frontend needs the API running. From the repo root:

```bash
# terminal 1 — the API (defaults to :8800)
python -m api

# terminal 2 — the dev server (defaults to :5173)
cd frontend
npm install      # first time only
npm run dev
```

Open http://localhost:5173. In dev, `/api/*` is proxied to the backend on
`:8800`, so the browser makes same-origin calls. To point at a separately
hosted API, set `VITE_API_BASE` (e.g. `VITE_API_BASE=https://host/api`).

## Screens

| Route | What it shows | API |
|---|---|---|
| `/` | Ranked recommendations | `GET /recommend` |
| `/asset/:ticker` | ACS breakdown, flags, rationale, compare | `GET /scan`, `/compare` |
| `/portfolio` | Sleeve allocation (donut + holdings) | `GET /portfolio` |
| `/scenarios` | Scenario impact + sleeve drawdown | `GET /scenarios`, `POST /scenario/{slug}` |
| `/status` | Weights, accuracy, version history, alerts | `GET /status`, `/alerts` |

## Scripts

```bash
npm run dev       # dev server with API proxy
npm run build     # production build to dist/
npm run preview   # serve the built bundle
npm run test      # Vitest component/unit tests
```
