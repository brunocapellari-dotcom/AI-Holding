# Production identity rollout

The verified-identity deployment is accepted only when all of these gates pass:

1. application unit tests reject forged caller headers in production;
2. Google token verification pins the `holding-control-plane` audience;
3. invalid issuer, unverified email, missing subject and invalid signatures fail closed;
4. Terraform configures the same custom audience on Cloud Run;
5. no `allUsers` or `allAuthenticatedUsers` invoker binding is introduced;
6. the production Terraform plan contains no delete action;
7. the immutable container image passes dependency, static and vulnerability scans;
8. the existing private Cloud SQL migration job remains healthy after deployment.

A dedicated runtime identity and explicit `roles/run.invoker` binding will be created per operational agent before that agent is activated. Shared static credentials are not permitted.
