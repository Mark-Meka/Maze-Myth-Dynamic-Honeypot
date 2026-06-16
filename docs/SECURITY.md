# Security Policy

## Overview

Maze Myth is a deception platform intended for isolated testing and red-team environments. It is not designed to be exposed as a generic production application without adequate isolation, monitoring, and access controls.

## Deployment Safety

- Run the platform in a dedicated VM or container host.
- Use a separate network segment for attacker-facing traffic.
- Do not expose internal services (`honeypot` on 8001, `real-app` on 8080) to the public internet.
- Only expose the proxy on port `80` and the dashboard on port `8002` when necessary.

## Dashboard Access

- The dashboard is operator-only. Prefer SSH tunneling when accessing `http://localhost:8002` remotely.
- Do not publish the dashboard publicly.
- If using Docker Compose, ensure the dashboard container is only reachable from trusted management hosts.

## Secrets Handling

- Keep `.env` out of version control.
- Never commit `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or other credentials.
- Use environment variables or a secrets manager in production deployments.

## Network Segmentation

- `proxy` routes attacker traffic internally to `real-app` and `honeypot`.
- `real-app` and `honeypot` run on the private Docker network `deception-net`.
- The dashboard reads data from shared volumes and should not be part of the public attack surface.

## Logging & Audit

- All honeypot events are written to `log_files/api_audit.log` and `databases/honeypot.db`.
- Use the audit log for tamper-evident review.
- Do not expose logs or the dashboard UI to untrusted networks.

## Vulnerability Reporting

Report security issues to the project owner via GitHub issues or the repository contact information. Include:
- affected component (`proxy`, `honeypot`, `dashboard`, `real-app`)
- reproduction steps
- any relevant environment details

## Responsible Use

This project is for testing, red-team evaluation, and research. It must not be used to harm third parties or to deploy actual malicious tools.
