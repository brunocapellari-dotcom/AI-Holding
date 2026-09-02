# Verified actor identity

Date: 2026-09-02

## Threat

`X-Actor` and `X-Actor-Type` are caller-controlled HTTP headers. They are useful for local tests and attribution during development but are not authentication and must never grant production authority.

A caller with legitimate network access could otherwise claim to be another agent or a human approver, corrupting audit attribution and potentially crossing an autonomy boundary.

A valid Google ID token issued for another service must also be rejected. Signature and issuer checks without an expected audience would leave a token-replay boundary unnecessarily broad.

## Production rule

Production identity is derived only from a Google-signed ID token carried in `Authorization: Bearer <ID_TOKEN>`.

The request has two independent gates:

1. Cloud Run IAM validates that the Google identity is allowed to invoke the service and that the token audience is accepted by Cloud Run.
2. The Control Plane validates the Google-signed token again and derives the actor from verified claims (`email`, `sub`, `iss`, `email_verified`) while requiring the configured audience.

The canonical custom audience is `holding-control-plane`. Terraform configures that audience on the Cloud Run service and provides the same value through `VERIFIED_IDENTITY_AUDIENCE`. This avoids coupling callers to the generated regional service URL while keeping replay protection explicit.

`X-Actor` and `X-Actor-Type` are ignored in production. They remain available only in development and test environments.

## Identity classification

- verified email ending in `.gserviceaccount.com` -> `service-account`
- other verified Google email -> `human`

The Google subject claim is retained in the actor context for immutable identity correlation even if a display email later changes.

## Agent activation gate

A canonical agent row being present in the database does not make the agent active. Activation requires all of the following:

- dedicated runtime/service identity;
- IAM permission scoped to the minimum required resources;
- explicit model route;
- deterministic autonomy ceiling;
- audit attribution to the verified identity;
- tests proving the runtime cannot impersonate a different actor;
- ID tokens minted specifically for the canonical Control Plane audience.

Until these are satisfied, bootstrap-created governance agents remain disabled.

## Key management

No service-account JSON keys are required. Cloud workloads should acquire short-lived Google identity tokens through Application Default Credentials or the metadata server. Static credentials are prohibited for this path.
