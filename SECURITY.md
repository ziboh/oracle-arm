# Security policy

## Reporting a vulnerability

Please do not report security vulnerabilities in public issues. Contact the project maintainers privately with a concise description, reproduction steps, affected versions, and a safe contact address.

Until a private contact address is published, use the repository owner's private security reporting feature.

## Deployment requirements

- Change the default `admin` password immediately.
- Set a long, random `WEB_SECRET_KEY`.
- Use HTTPS and `WEB_SECURE_COOKIE=true` behind a reverse proxy.
- Keep OCI credentials and generated SSH private keys in the persistent data volume only.
- Do not expose port 8080 directly to the public internet.
