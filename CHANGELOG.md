# Changelog

All notable changes to A1 Control are documented here.

## [Unreleased]

## [1.2.0] - 2026-07-19

- Bump version to 1.2.0.

- Replace the default `admin` / `WEB_PASSWORD` flow with first-visit password setup and a persistent generated session secret.
- Keep notification credentials and task defaults in the browser workflow instead of duplicating them across `.env` and Compose.
- Reduce `.env.example` to the two deployment-level network and cookie options.
- GitHub Actions: build multi-arch Docker images and push to GHCR on version tags (`v*`) using the built-in `GITHUB_TOKEN` (no extra secrets).
- Compose: optional `ORACLE_ARM_IMAGE` to pull a published image instead of building locally.

## [1.1.0] - 2026-07-18

- Fix Console / Logs / Settings freezes: close status SSE on navigation and free Waitress workers within ~2s (keep default `WEB_THREADS=4`).
- Persist notification channel drafts in the browser so refresh no longer drops them.
- Show notification channel credentials as plain text for easier editing.
- Keep separate webhook URLs per provider in the notification editor.
- Raise overall UI type sizes for better readability.
- Default notification channels to enabled when added, while keeping the send toggle.
- File-based i18n with English/Chinese locales and language switcher.
- Soft-console form select styling and notification provider icons.
- Expanded notification providers and settings UI polish.
- Docker package data packaging for locales and static notification icons.

## [1.0.0] - 2026-07-18

- Initial open-source release.
- Password-protected OCI Ampere A1 provisioning console.
- Docker and Docker Compose deployment support.
- OCI credential import, resource discovery, capacity retry, SSH key management, and notifications.
