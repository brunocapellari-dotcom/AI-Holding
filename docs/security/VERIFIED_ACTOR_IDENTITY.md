# Verified actor identity

Date: 2026-09-08

## Threat

`X-Actor` and `X-Actor-Type` are caller-controlled HTTP headers. They are useful for local tests and attribution during development, but they are not authentication and must never grant production authority.

A caller with legitimate network access could otherwise claim to be another agent or a human approver, corrupting audit attribution and potentially crossing an autonomy boundary. A valid Google ID token issued for another service must also be rejected.

## Production rule

Production identity is derived only from a Google-signed ID token carried in `Authorization: Bearer <ID_TOKEN>`.

The request has two independent gates:

1. Cloud Run IAM decides whether the Google identity may invoke the service.
2. The Control Plane validates the signed token again and derives the actor from verified claims (`email`, `sub`, `iss`, `email_verified`) while requiring the configured audience.

The canonical custom audience is `holding-control-plane`. Terraform configures that audience on the Cloud Run service and provides the same value through `VERIFIED_IDENTITY_AUDIENCE`.

`X-Actor` and `X-Actor-Type` are ignored in production. They remain available only in development and test environments.

If production is ever configured with verified identity disabled, the application fails closed with HTTP 503 rather than falling back to caller-controlled identity.

## Identity classification

- verified email ending in `.gserviceaccount.com` -> `service-account`
- other verified Google email -> `human`

The Google subject claim is retained in the actor context for immutable identity correlation even if a display email later changes.

## Agent activation gate

A canonical agent row being present in the database does not make the agent operational. Activation requires:

- dedicated runtime/service identity;
- IAM permission scoped to the minimum required resources;
- explicit model route;
- deterministic autonomy ceiling;
- audit attribution to the verified identity;
- tests proving the runtime cannot impersonate another actor;
- ID tokens minted specifically for the canonical Control Plane audience.

Until these conditions are satisfied, bootstrap-created governance agents remain disabled.

## Key management

No service-account JSON keys are required. Cloud workloads acquire short-lived Google identity tokens through workload identity, Application Default Credentials or the metadata server. Static service-account keys are prohibited for this path.
