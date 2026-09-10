---
name: deploy
description: >-
  Reference for how this project ships: the CI/CD pipeline, the container images, and
  deploying to Azure Container Apps. Use when asked about deploys, GHCR packages, the
  workflow, image platforms, or "why is production showing the old version".
---

# Deploy flow

## Pipeline (`.github/workflows/backend-ci.yml`)

On every push / PR to `main`:

| Job | |
|---|---|
| `lint` | `ruff check .` |
| `test` | `pytest -m "not integration"` (needs `DATABASE_URL`, `JWT_SECRET` secrets) |
| `integration-test` | `pytest -m integration` — LLM smoke tests self-skip without `GEMINI_API_KEY` / `OPENROUTER_API_KEY` |
| `frontend-build` | `npm ci && npm run build` (production) |
| `images` | builds backend + frontend for **`linux/amd64`**; **pushes to GHCR only on push to `main`** |

Published on merge to `main`:

- `ghcr.io/fareselsobky99/customer-support-backend:latest` and `:<sha>`
- `ghcr.io/fareselsobky99/customer-support-frontend:latest` and `:<sha>`

Both packages are **public** — Azure pulls them with no registry credentials.

## The amd64 rule

Azure Container Apps runs `linux/amd64`. **Never `docker build && docker push` from an
Apple-Silicon Mac** — that is arm64 and fails on Azure with `exec format error`. CI (amd64
runners + explicit `--platform linux/amd64`) is the only thing that should push images. To
build locally: `docker buildx build --platform linux/amd64 --push ...`.

## Deploying a new version

1. Merge to `main` → CI publishes `:latest`.
2. Roll the Azure Container Apps:
   ```bash
   az containerapp update -n customer-support-backend  -g <rg> --image ghcr.io/fareselsobky99/customer-support-backend:latest
   az containerapp update -n customer-support-frontend -g <rg> --image ghcr.io/fareselsobky99/customer-support-frontend:latest
   ```

## Backend runtime env (set in the Azure Container App)

| Var | |
|---|---|
| `DATABASE_URL`, `JWT_SECRET` | required (store as secrets) |
| `LLM_PROVIDER` | `gemini` or `openrouter` |
| `OPENROUTER_API_KEY` / `GEMINI_API_KEY` | the matching provider key (secret) |
| `OPENROUTER_MODEL` / `GEMINI_MODEL` | optional model override |
| `AGENT_MAX_STEPS`, `AGENT_RATE_PER_MIN`, `AGENT_RATE_BURST` | optional tuning |

Backend listens on `:8000`, frontend nginx on `:80` — set the Container App ingress target
ports to match.

## Frontend has no runtime env

The API base URL is compiled in from `frontend/src/environments/environment.ts` (the Azure
backend). Change it there, commit to `main`, let CI rebuild.

## "Production still shows the old page"

`index.html` was cached by the browser. `nginx.conf` now sends `Cache-Control: no-cache`
for it (hashed JS/CSS stay cached forever), so this stops happening after that image
deploys. Until then: hard-refresh (Cmd+Shift+R).

## CORS

`backend/app/api_main.py` `allow_origins` must list the frontend's exact URL. If the
frontend URL changes, update that list, commit, redeploy the backend.
