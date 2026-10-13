# ZERO_COST — Hermes → Holding real receipt and owner console

This release uses the already merged and audited Hermes event ingestion contract.
No duplicate message bus or project-specific database is added.

## Operator view

The owner console at `/` retains project governance and human actions. It also displays
the read-only event feed `GET /api/v1/holding/control-plane/event-feed`,
backed by `HermesEventReceipt` rows persisted by the canonical Hermes event endpoint.

- This is an authenticated governance read. It has the same access boundary as Owner View.
- Only event ID, type, project key, producer, occurred/received timestamps and receipt age are returned.
- Payload, metadata, secrets and potentially personal messages are **never exposed**.
- `availability_verified=false` explicitly states these are recorded events, not proof of running services.
- No fabricated activity is shown when the database has no events.
- Last 30 events are shown by default; optional project filtering uses an exact project key.

## Full no-runner handoff acceptance

Start Hermes API with its worker on the same authorized local SQLite state, and start
Holding with its real operational PostgreSQL database. The Hermes worker must point
to the local Holding service using its existing `HERMES_HOLDING_URL` configuration.

Execute one genuine authorized project request via Hermes. Record the real
`event_id` from its durable event envelope and the exact `project_key`.
Do not paste provider secrets or personal message payload into the command.

Then, in the Holding repository:

```bash
python scripts/verify_local_handoff.py \
  --hermes http://127.0.0.1:8080 \
  --holding http://127.0.0.1:8001 \
  --event-id <REAL_EVENT_ID> \
  --project-key <REAL_PROJECT_KEY>
```

The verifier checks both live `/ready` endpoints, Hermes worker heartbeat status,
and the matching Holding persisted event via the **authenticated, sanitized read feed**.
It allows only HTTP loopback services, refuses redirects, and fails if no matching
receipt was received. It does not synthesize a success event or mutate state.

**Limitation:** the feed includes at most 100 recent events in this check. If heavily
loaded, inspect the canonical Holding event ledger to select a recent event and rerun.
A PASS here proves an actual event was received, not that every ecosystem E2E path,
all payload semantics, disaster recovery or go-live gates passed.

## Runbook for remaining operator evidence

1. Record exact source and receiving commit SHAs.
2. Run `pytest tests/test_operational_feed.py tests/test_local_handoff.py` in an available local executor.
3. Confirm Hermes worker activity and Holding database persistence.
4. Run an authorized Research AI → Hermes → AgroLog → Holding request.
5. Repeat with a **different real input** and verify distinct event IDs.
6. Run the backup/restore drill for each stateful runtime and report restore evidence separately.
7. Apply release evidence gates only when the preceding steps genuinely pass.

The above requirements intentionally do not depend on GitHub Actions or a paid service.
Do not mark DONE merely because this documentation or code is present.
