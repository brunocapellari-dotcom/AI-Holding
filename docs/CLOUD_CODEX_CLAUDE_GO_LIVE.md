# Cloud-first go-live: all twelve repositories

This document complements the Windows installer in tools/windows/installer (see its README.md). Developer tools installed locally are NOT a remote deployment.

## Work queue

| Repository | First real delivery target |
|---|---|
| AI-Holding | Authenticated control-plane API, health, project registry, backup and integrations |
| Hermes-AI-Platform | Durable remote worker, retries, human gates and E2E Holding integration |
| Research-AI | Live source discovery, provenance, approved downloads and RESEARCH PACKAGE E2E |
| Second-Brain | Auditable Markdown/Obsidian claim ingestion and restore |
| AgroLogMT | Real crop, weather, logistics, line-up and announced freight end-to-end |
| WHATSAPP_AI | Authorized ingestion, freight deduplication and changes with immutable provenance |
| Geopolitical-Watch | Fix Render 512 MiB memory failures and validate real remote web service |
| Mercado-Financeiro | B3/CVM/BCB historical data, risk tests and paper trading, no real orders |
| Sports-Intelligence | Video to tracking, statistics and scouting with end-to-end validation |
| Content-Factory | Brief to rendered video with QC, copyright and reproducible delivery |
| Game-Studio | WorldWar, racing manager and football manager: P0s and playable builds |
| Personal-Performance-Health-OS | PAUSED: audit/preserve only, do not implement or deploy |

## Install once

On Windows 11, copy the folder tools/windows/installer (or a ZIP of it, fully extracted) and run, in order:

    00-VALIDAR-PACOTE.cmd
    01-INSTALAR-E-SINCRONIZAR.cmd

This only installs light development tools and clones or fast-forward-updates all 12 repositories under the user's AI-Holding-Workspace. It does not install Docker, run databases or provision paid services. It does not overwrite changed repositories.

Log in using the normal official interfaces: gh auth login, codex login and the interactive claude login. Never place credentials in source code or transcripts.

## Execute while the notebook is OFF

1. Open https://chatgpt.com/codex (Codex Cloud) and https://claude.ai/code (Claude Code Remote).
2. Authorize the relevant GitHub repositories separately in each hosted service.
3. Launch independent hosted tasks for all ACTIVE projects, each in a separate branch, starting with P0.
4. Assign Codex implementation and tests; Claude performs independent review, security checks and corrections in a separate branch/PR. Neither overwrites the other's branch.
5. Ask for measurable test output, real data and health checks; use a PR for review, with no automatic merge or production deploy.
6. Preserve backups and evidence. Human approval remains required for billable services, real financial operations, credentials and irreversible changes.
7. Cloud-hosted coding sessions can continue after the notebook is turned off; locally running CLI sessions cannot.

## Reusable mission for every active repository

Audit the actual default branch and existing pull requests. Reuse existing code and prioritize the highest-impact P0 go-live blocker. Implement a concrete functional fix with reproducible tests, then open a pull request. Do not simply write plans or dashboards with mock data. Do not use GitHub Actions or local notebook runners as release dependencies. Do not provision paid cloud services, expose secrets, auto-merge, deploy automatically, delete data or bypass authorization. Show test evidence, the real end-to-end path, measured blockers and rollback. Never claim readiness without independent verification.

## Domain constraints

* AgroLog/WhatsApp: prohibited municipal average freight. Preserve pickup entity, carrier, destination, product, equipment, PF/PJ, price, time and provenance. A published rate is not a confirmed negotiated rate.
* Finance: no real-money trading without separate human authorization.
* Sports: no real-money bets or model validation based on in-sample accuracy alone.
* Geopolitical: fix web process OOM without sacrificing source provenance or audit trails.
* Obsidian: Markdown canonical; graph and search indexes may be rebuilt.
* Health OS: remains PAUSED.

## Real blockers

Codex and Claude hosted logins and GitHub permissions cannot be granted by this script. Agent subscriptions do not pay for production cloud runtime. Sustainable remote hosting, persistent stores, backups, metrics, authentication and verified E2E must be implemented separately; this installer does not claim go-live.
