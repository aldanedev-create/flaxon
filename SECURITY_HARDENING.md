# Admin and framework security hardening

This review covers Admin authentication, account permissions, password changes,
cookies, media uploads, remote service requests, CSRF, request body limits,
proxy headers, and the public signed-session manager. The starting revision is
`fec71040ef4318891b0309613261ac183e3bf607`.

## Findings fixed

| Area | Previous behavior | Result |
| --- | --- | --- |
| CSRF | An automatically submitted cookie alone satisfied CSRF validation. Future-dated signed tokens were also accepted. | Unsafe requests require an explicitly submitted header token; future-dated tokens are rejected. Admin forms continue to validate their submitted form token. |
| Request bodies | A small declared Content-Length bypassed actual byte counting. | The middleware counts every received chunk regardless of Content-Length. |
| Proxy trust | An empty trusted-proxy list trusted every client, including requests without a peer address. | Forwarded headers are ignored unless the direct peer is explicitly trusted. Forwarded schemes are restricted to HTTP and HTTPS. |
| Admin authentication | An application-level request.user could substitute for Admin authentication. Session snapshots also retained removed accounts and old permissions. | Admin authenticates through its own backend and requires a matching, active local account ID. Protected requests use the current account roles and permissions. |
| Admin password changes | Previously issued sessions and trusted devices survived a password reset or password change. | Password changes rotate an account session version and revoke trusted devices. Earlier sessions fail the next protected request. |
| Admin MFA | Wrong MFA codes with a correct password did not count toward login throttling. | MFA failures count against the same account/client login failure budget as password failures. |
| Admin cookies | Admin session cookies omitted Secure, including outside debug mode. | Cookies use Secure outside debug mode, alongside HttpOnly and SameSite=Lax. |
| Admin/CMS media | Local uploads were stored before validation; stored filenames could retain active-content extensions; image validation failed open without Pillow. | Bytes are validated before storage, actual byte limits are enforced, extensions match the declared allowed media type, images require Pillow, and PDF uploads require a PDF signature. Normal, CMS, and resumable uploads use consistent extension handling. |
| Remote service credentials | The HTTP client followed redirects while carrying service credentials. | Remote API redirects are rejected instead of forwarding credentials to another target. Direct service requests remain supported. |
| Signed sessions | Expired signed sessions were restored. Splitting at the first dot also broke valid cookies containing fractional timestamps or dotted data. | Decoding splits at the final signature delimiter, validates the payload structure and lifetime, and starts a fresh session when the old session expires. |

The upload findings are particularly relevant when a less-privileged media user
can publish files served from the application's own origin. Declaring a file
as text/plain must not allow it to be stored as an HTML document.

## Upgrade notes

- Applications using CSRFMiddleware must explicitly submit X-CSRF-Token.
  A cookie by itself is no longer accepted as proof of an intentional request.
- Configure ProxyHeadersMiddleware with the actual proxy IPs or CIDRs.
  None and an empty list now mean trust no proxies. The explicit wildcard
  remains available for controlled environments.
- Custom Admin authentication backends must return a locally registered Admin
  account with the matching ID. Application-level request.user does not grant
  access to Admin.
- AdminDashboard derives cookie security from the application's debug flag.
  An explicit cookie_secure option is available; use secure cookies in
  production. Standalone AdminAuth defaults to secure cookies.
- Password resets and password changes require existing sessions to sign in
  again. Trusted-device credentials are revoked at the same time.
- Install Pillow for image uploads, for example through flaxon[admin].
  Filenames with mismatched extensions are normalized to the allowed media
  type. Configure remote service URLs to their final API endpoints because
  redirects are no longer followed.

## Verification

- 22 regression cases exercise the security boundaries, including multipart
  upload rejection without leftover files and a real local HTTP redirect test.
- Full pytest suite: **321 passed, 27 skipped** on Python 3.12.
- The full run included the Redis concurrency test using a temporary local
  Redis server, plus available optional integrations and benchmark tests.
- The test environment used the current Teloce source checkout and
  MinifyJS 0.1.3. It did not validate every published dependency combination.
- The new regression test file passes the repository's Ruff rules.
- Git whitespace validation passes.
- The broken Teloce documentation index link was reproduced on the starting
  revision and corrected as part of completing the full-suite checks.

## Scope and deployment limits

This is a source-level hardening pass, not certification that every deployment
is free of vulnerabilities. The skipped tests and externally hosted services
were not validated by this run.

Admin account checks refresh from the current process's user registry.
Multi-worker deployments must still synchronize account changes across
processes; storing session tokens in Redis alone does not refresh each worker's
account registry. The direct AdminAuth login failure budget is also local to
the process, so distributed deployments need the existing shared request
limiter configured.

This patch does not redesign Admin's dashboard-wide CSRF token into a
per-session token, change the legacy permission defaults, audit every
third-party dependency, or perform a live deployment penetration test.
Applications should use strict permissions, explicit proxy/origin settings,
shared production infrastructure, and the deployment guidance.

## References

- [OWASP CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [Flaxon security guide](docs/security.md)
- [Admin production guide](docs/guides/admin-production.md)
