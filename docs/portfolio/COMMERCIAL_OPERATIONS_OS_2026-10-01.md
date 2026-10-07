# Commercial Operations OS — 2026-10-01

Status: DISCOVERY / MODULE UNDER HOLDING

This is not a new standalone company or repository yet. It is a Holding capability for future commercial operations, including transport/logistics services and other projects.

## Business loop

`LEAD -> QUALIFICATION -> CRM -> MEETING -> FOLLOW-UP -> PROPOSAL -> COLLECTION -> OPERATION -> KPI/ALERT`.

Each stage must have owner, due date, state, next action and measurable outcome.

## Reference systems

### Twenty

REFERENCE/POC for:

- programmable CRM objects/fields/views;
- workflows and agents;
- versioned/custom business apps;
- self-hosted architecture.

Do not adopt it if the existing Business OS/ERP/CRM layer already satisfies the validated requirement.

### Comp AI CRM

ADAPT concepts:

- CRM as operational memory for an agent;
- evidence ledger for facts;
- observed fact vs weak suggestion;
- durable work queue;
- autonomous scheduled follow-up;
- research budget;
- sandbox with deny-all egress;
- reason attached to rechecks;
- persistent agent conversation/audit.

Strong principle: an uncertain fact about a customer is not silently written as truth.

## Evidence model

Commercial facts should record:

- source;
- observed_at;
- field/value;
- evidence locator;
- confidence/quality;
- verified_by_human where applicable;
- supersedes/validity where relevant.

## Automation boundaries

Allowed automation can include prioritization, reminders, drafts, internal summaries and scheduled research.

Sending messages, changing external records, financial commitments, collection actions or other consequential operations must use explicit policy/authorization and an audit trail.

## KPI layer

The operating dashboard should cover at minimum:

- lead funnel and aging;
- response/follow-up SLA;
- meetings and next actions;
- proposal conversion;
- receivables/collection status;
- operational handoff;
- customer/service exceptions;
- revenue/margin metrics where source systems permit.

The Commercial Operations OS consumes Hermes/Research/Holding shared capabilities instead of duplicating agent, research, security or knowledge infrastructure.
