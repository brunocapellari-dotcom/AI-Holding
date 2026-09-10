# Cloud Run reserved URL paths

## Production incident

The PMO production acceptance reached the authenticated Control Plane, claimed its bounded task and started the run, but an external request to `/healthz` returned HTTP 404 before the application handled it.

Cloud Run reserves several URL paths, including some paths ending in `z`. Google recommends avoiding all paths ending in `z` to prevent collisions with platform routing. The application route existed and internal container probes could reach it, but the public `run.app` frontend intercepted the external `/healthz` request.

Primary platform reference: Google Cloud Run known issues, **Reserved URL paths**.

## Correction

The Control Plane operational endpoints are:

- `/health` for process/service liveness;
- `/ready` for database-backed readiness.

Cloud Run startup and liveness probes, the PMO worker, production acceptance evidence and automated tests must use those exact paths.

## Permanent rule

Do not introduce externally consumed Control Plane paths that end in `z`. In particular, do not use `/healthz`, `/readyz` or `/livez` on Cloud Run. A locally successful route is not sufficient evidence because reserved-path interception happens at the Google frontend before the container.

Production acceptance must continue to exercise the real authenticated `run.app` route from the PMO runtime identity so platform-routing failures are detected before autonomous scheduling is enabled.
