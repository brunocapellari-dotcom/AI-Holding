# Tainted Cloud Run runtime recovery

Date: 2026-09-02

## Incident

The first production bootstrap created the Cloud Run API service and migration job before the database secret version existed. Google Cloud rejected those revisions with `SECRETS_ACCESS_CHECK_FAILED`. Terraform retained both resource instances in state as tainted.

After the database and secret foundation were created successfully, the next full plan attempted to replace both tainted Cloud Run resources. Their `prevent_destroy` guards correctly blocked the replacement.

## Recovery

The production workflow now detects the two known bootstrap resources as tainted from Terraform state and runs `terraform untaint` only when the state marker is present. This removes the forced-replacement flag; Terraform can then update the existing resources in place with the valid secret and immutable image.

The recovery does not disable deletion protection or `prevent_destroy` and does not delete either runtime resource.

## New production invariant

Every complete production plan is rendered as JSON and rejected if any resource action contains `delete`. Destructive infrastructure changes therefore cannot pass the unattended deployment path. A future intentional replacement or deletion must be reviewed as an explicit exceptional change rather than silently flowing through CI/CD.

## Reusable lesson

A resource that failed during initial creation can remain tainted even after its missing dependency is repaired. Do not remove lifecycle protections to make the plan pass. Repair the dependency, verify the failure mode, clear only the stale taint, and retain a no-delete deployment gate.
