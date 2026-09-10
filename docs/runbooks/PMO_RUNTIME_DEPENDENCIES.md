# PMO production runtime dependency gate

## Incident

A production PMO acceptance execution failed immediately with container exit code `1`, while the Control Plane, migrations, bootstrap, IAM checks and the acceptance preparation job were healthy.

The PMO worker already had deterministic exit codes for failures occurring inside its runtime lifecycle. Because none of those codes appeared, the failure boundary was before `app.pmo_worker.main()`.

## Root cause

`app.pmo_worker` imports `httpx` at module import time. `httpx` was declared only in the `dev` optional dependency group, while the production image is built with `pip install .`.

CI installed `.[dev]`, so unit tests, typing and security gates passed. The production image did not contain `httpx`, causing an import-time `ModuleNotFoundError` before the worker lifecycle could emit its structured diagnostic code.

## Correction

- `httpx` is a production dependency because the deployed PMO worker uses it at runtime.
- The duplicate development-only declaration is removed.
- CI now starts the built production image and imports every deployed Python entrypoint after `docker build`, before SBOM and vulnerability gates.

## Permanent rule

A dependency used by any deployed runtime entrypoint must be declared in `[project].dependencies`, not only in a development extra.

The production container, not the developer environment, is the authoritative dependency boundary. Every new deployed entrypoint must be added to the production-image import smoke gate so a dev-only dependency cannot pass CI and fail only after deployment.

This gate does not replace unit, integration, SBOM or vulnerability testing; it verifies that the exact production installation can at minimum load every executable module before release.
