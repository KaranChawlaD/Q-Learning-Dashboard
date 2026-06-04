# Deploying to Fly.io (Phase 1)

Public demo with **per-browser session isolation** (HttpOnly cookie), **no login**, and **client-side run export**. Each visitor gets their own trainer; idle sessions are removed after 30 minutes.

## Prerequisites

1. [Fly.io account](https://fly.io/app/sign-up)
2. [flyctl](https://fly.io/docs/hands-on/install-flyctl/) installed and logged in (`fly auth login`)
3. This repository pushed to GitHub (optional; you can deploy from local source)

## First deploy

From the project root:

```bash
fly launch
```

When prompted:

- **App name** — pick a unique name (updates `fly.toml`).
- **Region** — choose one close to your users.
- **Postgres / Redis** — decline (not needed for Phase 1).
- **Deploy now** — yes.

`fly launch` detects the `Dockerfile`, sets `QLEARNING_ENV=production`, and binds internal port **8080** (Fly sets `$PORT=8080` automatically).

## Subsequent deploys

```bash
fly deploy
```

## Verify

```bash
fly open
```

Check:

- Connection indicator shows **Connected**.
- Two browser profiles (or normal + incognito) can train **independently**.
- **Export run to disk** (`E`) downloads a JSON file with layout, config, lengths, and full Q-table.

## Environment

| Variable | Default (Fly) | Purpose |
|----------|---------------|---------|
| `PORT` | `8080` | HTTP bind port (set by Fly; do not hard-code in `fly.toml`) |
| `QLEARNING_ENV` | `production` | Disables auto-open browser and server-side writes to `assets/` |

Local development is unchanged:

```bash
python run.py web
```

## Production vs local behavior

| Feature | Local | Production (`QLEARNING_ENV=production`) |
|---------|-------|----------------------------------------|
| Bind host | `127.0.0.1` | `0.0.0.0` |
| Auto-open browser | yes | no |
| Auto-save to `assets/` on finish | yes | no (use Export instead) |
| Session isolation | yes | yes |

## Scaling notes

- **WebSockets** work on Fly’s `http_service`; no extra config.
- **`auto_stop_machines`** stops the VM when idle (good for demos; cold start ~ few seconds).
- For heavier public traffic, raise `min_machines_running` in `fly.toml` or add rate limits in a later phase.

## Troubleshooting

**App won't start** — `fly logs` and confirm `$PORT` matches `internal_port` in `fly.toml` (8080).

**WebSocket disconnects** — ensure you are on `https://`; Fly forces HTTPS.

**Sessions lost on redeploy** — expected; runs live in memory only (Phase 1). Use **Export run** before closing the tab.

## Custom domain (optional)

```bash
fly certs add your-domain.example
```

Then add the DNS records Fly prints. HTTPS is provisioned automatically.
