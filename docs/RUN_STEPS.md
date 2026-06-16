# Run Steps

This guide explains how to run each component of the Maze Myth Dynamic Honeypot project alone, how to connect them, and how to run the whole platform together.

## Prerequisites

- Python 3.10+ installed and available as `python`
- `pip` installed for Python package installation
- Docker Desktop or Docker Engine installed for full platform deployment
- A valid `.env` file with `GEMINI_API_KEY` configured

## Run each program alone

### 1. Honeypot

The honeypot service is the core deception backend and can be started directly from the repo root.

```bash
python honeypot.py
```

- Default listening port: `8001`
- Connect to it at: `http://localhost:8001`
- Uses local storage paths:
  - `databases/honeypot.db`
  - `log_files/api_audit.log`
  - `generated_files/`

> If this is the first run, create `.env` from `.env.template` and add `GEMINI_API_KEY` before starting.

### 2. Dashboard

The dashboard reads the honeypot state and audit logs, and exposes operator APIs.

```bash
python dashboard/monitor.py
```

- Default listening port: `8002`
- Connect to it at: `http://localhost:8002`
- The dashboard reads shared local data from:
  - `databases/honeypot.db`
  - `log_files/api_audit.log`
- If those files do not yet exist, run the honeypot first.

### 3. Real App (decoy banking service)

The real-app decoy service is a Flask app used by the platform as a believable target.

```bash
python real-app/app.py
```

- Default listening port: `8080`
- Connect to it at: `http://localhost:8080`

### 4. Windows helper: `scripts/run_honeypot.bat`

This helper is a convenience launcher for Windows.

- It creates a `venv` if needed
- Installs Python dependencies from `requirements.txt`
- Starts the dashboard in a new window
- Starts the honeypot in the current window

Run it by double-clicking or from PowerShell:

```powershell
.\scripts\run_honeypot.bat
```

### 5. Proxy

The proxy service is not designed to be run directly as a standalone Python module. Instead, it is launched as part of the Docker Compose platform.

- The full proxy definition is in: `docker-compose.yaml`
- It routes attacker traffic to `real-app` or `honeypot`
- It listens on port `80`

## Connecting programs when running alone

If you run the components individually, use the following host URLs:

- Honeypot: `http://localhost:8001`
- Dashboard: `http://localhost:8002`
- Real App: `http://localhost:8080`

For the dashboard to work with the honeypot in standalone mode, keep both services running locally so the dashboard can read the shared `databases` and `log_files` files.

If you want the dashboard to call the honeypot API directly, set the internal honeypot URL in `.env` as:

```ini
HONEYPOT_INTERNAL_URL=http://127.0.0.1:8001
```

## Run the whole project together

The complete platform includes:

- `proxy` (attacker-facing on port `80`)
- `real-app` (internal decoy on `8080`)
- `honeypot` (internal trap on `8001`)
- `dashboard` (operator UI on `8002`)

Use the root Compose file:

```bash
docker compose -f docker-compose.yaml up -d
```

Check the running containers:

```bash
docker compose -f docker-compose.yaml ps
```

Follow logs if needed:

```bash
docker compose -f docker-compose.yaml logs -f vm1-proxy
```

### Access after full startup

- Attacker-facing proxy: `http://localhost`
- Operator dashboard: `http://localhost:8002`

### Stop the full platform

```bash
docker compose -f docker-compose.yaml down
```

To remove named volumes too:

```bash
docker compose -f docker-compose.yaml down -v
```

## Notes

- Do not expose `honeypot` or `real-app` directly to the public internet in production.
- Only expose the proxy on port `80` and the dashboard on port `8002` when needed.
- For a full production-like setup, use `docker compose -f docker-compose.yaml up -d`.
