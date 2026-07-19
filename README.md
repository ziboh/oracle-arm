<h1 align="center">A1 Control</h1>

<p align="center">
  <strong>A self-hosted web console for creating OCI Ampere A1 Always Free instances</strong>
</p>

<p align="center">
  English | <a href="./README.zh-CN.md">简体中文</a>
</p>

A1 Control discovers your OCI resources, retries when A1 capacity is unavailable, and keeps the whole workflow in a password-protected browser UI.

## What it does

- Discovers compartments, availability domains, public subnets, and ARM images
- Configures A1 shape, OCPUs, memory, boot volume, and SSH access in the browser
- Retries automatically when OCI reports insufficient capacity
- Shows task status, live logs, public IP, and the generated root password
- Tracks the 200 GB Always Free block-volume quota
- Sends optional success notifications through Telegram, Bark, PushPlus, ServerChan, Gotify, ntfy, webhooks, or SMTP
- Supports English and Chinese from the login page and the top navigation bar

## Quick start with Docker

You need Docker Compose and OCI API credentials (a config snippet and its unencrypted PEM private key).

```bash
git clone https://github.com/ziboh/oracle-arm.git
cd oracle-arm
docker compose pull
docker compose up -d
```

No `.env` file is required for a local-only deployment. Open `http://127.0.0.1:8080` and create the admin password on the first page. The session signing secret is generated automatically and stored in the persistent data volume.

To allow access from another machine, copy `.env.example` to `.env`, change `BIND_ADDRESS`, enable secure cookies, and place the console behind an HTTPS reverse proxy.

The default image is `ghcr.io/ziboh/oracle-arm:latest` and supports `linux/amd64` and `linux/arm64`. Set `ORACLE_ARM_IMAGE` in `.env` if you want to pin a version.

## First setup

1. Create the admin password on the first visit. There is no default password.
2. Open **Settings** and import the OCI config snippet and matching PEM private key.
3. Return to **Console**, choose the discovered OCI resources, and set the instance size.
4. Start the task and follow its progress under **Logs**.

The interface follows your browser language on the first visit. Use the language menu on the login page or in the top bar to switch between English and Chinese at any time.

## Common settings

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Host address exposed by Docker Compose |
| `WEB_SECURE_COOKIE` | `false` | Set to `true` when the public URL uses HTTPS |
| `ORACLE_ARM_IMAGE` | `ghcr.io/ziboh/oracle-arm:latest` | Optional image tag override |

OCI credentials, task options, retry timing, and notification channels are configured in the browser rather than `.env`.

## Local development

Python 3.10+ and [uv](https://docs.astral.sh/uv/) are recommended:

```bash
uv sync
uv run dev
```

Run the test suite with:

```bash
uv run pytest
```

## Security

- Use HTTPS and set `WEB_SECURE_COOKIE=true` for internet-facing deployments.
- Keep port `8080` private; expose the console through a reverse proxy instead.
- Protect the data volume: it contains OCI credentials, generated SSH keys, and task data.
- Restrict console access because task logs can contain the generated root password.

## Project links

[Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security policy](SECURITY.md) · [License](LICENSE)
