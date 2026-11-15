# Security Policy

## Supported Versions

Flaxon is pre-1.0. Security fixes are made for the latest release series and
published to PyPI as a new patch version.

| Version | Supported |
| ------- | --------- |
| 0.3.x   | ✅ Fully supported |
| < 0.3   | ❌ Unsupported: upgrade to the latest 0.3.x |

Security fixes will be prioritized for the actively supported release series.

## Reporting a Vulnerability

We take security vulnerabilities seriously.

If you discover a security vulnerability in Flaxon:

1. **DO NOT** open a public GitHub issue.
2. Email the maintainer at **aldanehutchinson5@gmail.com**.
3. Include as much of the following information as possible:
   - Flaxon version
   - Python version
   - Operating system
   - Step-by-step reproduction
   - Expected behavior
   - Actual behavior
   - Potential security impact
   - Suggested fix, if available

We aim to acknowledge vulnerability reports within **48 hours** and will
investigate and address confirmed vulnerabilities as quickly as practical.

## Security Best Practices

### Production Deployment

When deploying a Flaxon application to production:

- **Never** enable `debug=True` in production.
- Use a strong `SECRET_KEY` generated from a secure random source.
- Configure `ALLOWED_HOSTS` for the application's expected domains.
- Terminate TLS using HTTPS at a trusted reverse proxy or load balancer.
- Store secrets in environment variables or an appropriate secrets manager.
- Keep Flaxon and its dependencies updated.
- Run production applications with the minimum required permissions.

### Environment Variables

Example production configuration:

```env
FLAXON_ENV=production
FLAXON_DEBUG=false
FLAXON_SECRET_KEY=<secure-random-secret>
FLAXON_ALLOWED_HOSTS=api.example.com,example.com
