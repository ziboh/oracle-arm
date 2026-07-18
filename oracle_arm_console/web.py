import hmac
import json
import os
import secrets
import time

import oci
from flask import (
    Flask,
    Response,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    stream_with_context,
    url_for,
)

from .i18n import (
    DEFAULT_LOCALE,
    LOCALE_COOKIE,
    get_locale,
    html_lang,
    locale_choices,
    normalize_locale,
    reset_locale,
    resolve_locale,
    section,
    set_locale,
    t,
)
from .instance import InstanceSpec
from .jobs import JobManager
from .notifications import send_notifications
from .oci_credentials import OciCredentialsStore
from .oci_resources import load_oci_resources


def _sse_event(payload: dict) -> str:
    return "data: {}\n\n".format(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
from .security import PasswordStore
from .settings import TaskSettings
from .ssh_keys import SshKeyStore


def create_app(
    config=None,
    job_manager=None,
    resource_loader=None,
    password_store=None,
    credentials_store=None,
    ssh_key_store=None,
    notification_sender=None,
):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("WEB_SECRET_KEY") or secrets.token_hex(32),
        WEB_PASSWORD=os.environ.get("WEB_PASSWORD") or "admin",
        SECURITY_FILE=os.environ.get("SECURITY_FILE") or "data/security.json",
        OCI_DATA_DIR=os.environ.get("OCI_DATA_DIR") or "data/oci",
        SSH_KEY_DIR=os.environ.get("SSH_KEY_DIR") or "data/ssh-keys",
        MAX_CONTENT_LENGTH=1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("WEB_SECURE_COOKIE", "false").lower() == "true",
    )
    if config:
        app.config.update(config)
    app.job_manager = job_manager or JobManager()
    app.resource_loader = resource_loader or load_oci_resources
    app.password_store = password_store or PasswordStore(
        app.config["SECURITY_FILE"], app.config["WEB_PASSWORD"]
    )
    app.credentials_store = credentials_store or OciCredentialsStore(app.config["OCI_DATA_DIR"])
    app.ssh_key_store = ssh_key_store or SshKeyStore(app.config["SSH_KEY_DIR"])
    app.notification_sender = notification_sender or send_notifications
    login_failures = {}

    @app.context_processor
    def inject_i18n():
        locale = get_locale()
        return {
            "t": t,
            "locale": locale,
            "html_lang": html_lang(locale),
            "locale_choices": locale_choices(),
            "js_i18n": section("js", locale),
        }

    def _locale_cookie_kwargs():
        return {
            "max_age": 365 * 24 * 3600,
            "path": "/",
            "httponly": False,
            "samesite": "Lax",
            "secure": app.config["SESSION_COOKIE_SECURE"],
        }

    def _safe_next_url(raw: str | None) -> str:
        """Only allow same-site relative paths (no open redirects)."""
        fallback = url_for("dashboard") if session.get("authenticated") else url_for("login")
        if not raw:
            return fallback
        candidate = raw.strip()
        # Drop absolute URLs / protocol-relative / backslash tricks.
        if (
            not candidate.startswith("/")
            or candidate.startswith("//")
            or "\\" in candidate
            or "://" in candidate
        ):
            return fallback
        return candidate

    @app.before_request
    def detect_locale():
        # Priority: explicit ?lang= → saved cookie → Accept-Language (first visit only).
        query_lang = request.args.get("lang")
        cookie_lang = request.cookies.get(LOCALE_COOKIE)
        explicit = query_lang or cookie_lang
        locale = resolve_locale(explicit, request.headers.get("Accept-Language"))
        g.locale_token = set_locale(locale)
        g.locale = locale
        # Persist after first resolve (browser language) and on every explicit switch.
        g.persist_locale_cookie = (
            query_lang is not None
            or cookie_lang is None
            or cookie_lang != locale
        )

    @app.teardown_request
    def teardown_locale(_exc=None):
        token = getattr(g, "locale_token", None)
        if token is None:
            return
        g.locale_token = None
        try:
            reset_locale(token)
        except (RuntimeError, ValueError, LookupError):
            # SSE stream teardown may run after the token was already reset.
            pass

    @app.after_request
    def persist_locale(response):
        if g.get("persist_locale_cookie") and g.get("locale"):
            response.set_cookie(LOCALE_COOKIE, g.locale, **_locale_cookie_kwargs())
        return response

    @app.before_request
    def protect():
        if request.endpoint in {"login", "static", "healthz", "set_language"}:
            return None
        if not session.get("authenticated"):
            if request.path.startswith("/api/"):
                abort(401)
            return redirect(url_for("login"))
        if request.method == "POST" and not hmac.compare_digest(
            request.form.get("csrf_token", ""), session.get("csrf_token", "")
        ):
            abort(400, t("errors.csrf"))
        return None

    @app.get("/locale")
    def set_language():
        """Set language preference cookie and redirect to a clean URL.

        Used by the language dropdown so the choice does not depend on keeping
        ``?lang=`` in the address bar, and works without custom JS navigation.
        """
        locale = normalize_locale(request.args.get("lang")) or DEFAULT_LOCALE
        g.locale = locale
        g.persist_locale_cookie = True
        token = set_locale(locale)
        try:
            target = _safe_next_url(request.args.get("next"))
            response = redirect(target)
            response.set_cookie(LOCALE_COOKIE, locale, **_locale_cookie_kwargs())
            return response
        finally:
            reset_locale(token)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        session.setdefault("csrf_token", secrets.token_urlsafe(24))
        error = None
        if request.method == "POST":
            if not hmac.compare_digest(request.form.get("csrf_token", ""), session["csrf_token"]):
                abort(400, t("errors.csrf"))
            address = request.remote_addr or "unknown"
            attempts, locked_until = login_failures.get(address, (0, 0))
            now = time.time()
            if locked_until > now:
                error = t("login.error_locked")
            elif app.password_store.verify(request.form.get("password", "")):
                login_failures.pop(address, None)
                # Keep locale cookie; only clear server session.
                session.clear()
                session.update(authenticated=True, csrf_token=secrets.token_urlsafe(24))
                return redirect(url_for("dashboard"))
            else:
                attempts += 1
                login_failures[address] = (0, now + 60) if attempts >= 5 else (attempts, 0)
                error = t("login.error_wrong")
        return render_template("login.html", error=error, csrf_token=session["csrf_token"])

    @app.get("/")
    def dashboard():
        defaults = TaskSettings.from_env()
        oci_configuration = app.credentials_store.status()
        return render_template(
            "dashboard.html",
            csrf_token=session["csrf_token"],
            defaults=defaults,
            oci_configuration=oci_configuration,
        )

    @app.get("/logs")
    def logs():
        return render_template("logs.html", csrf_token=session["csrf_token"])

    @app.get("/settings")
    def settings():
        return render_template(
            "settings.html",
            csrf_token=session["csrf_token"],
            oci_configuration=app.credentials_store.status(),
            secure_cookie=app.config["SESSION_COOKIE_SECURE"],
        )

    @app.get("/healthz")
    def healthz():
        return jsonify(ok=True)

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/api/status")
    def status():
        return jsonify(app.job_manager.status())

    @app.get("/api/status/stream")
    def status_stream():
        """Server-Sent Events: push job status/logs as soon as they change."""
        manager = app.job_manager
        # Optional catch-up: client can pass last known seq to skip immediate duplicate.
        try:
            last_seq = int(request.args.get("since", "-1"))
        except (TypeError, ValueError):
            last_seq = -1

        @stream_with_context
        def generate():
            seq = last_seq
            # First event immediately so the page is not blank while waiting.
            snapshot = manager.status()
            yield _sse_event(snapshot)
            seq = int(snapshot.get("seq", seq))
            while True:
                # Long-poll style wait: wake on new log lines, else heartbeat every ~15s.
                snapshot = manager.wait_for_update(seq, timeout=15.0)
                next_seq = int(snapshot.get("seq", seq))
                if next_seq != seq:
                    yield _sse_event(snapshot)
                    seq = next_seq
                else:
                    # Comment heartbeat keeps proxies from closing idle connections.
                    yield ": keepalive\n\n"

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @app.post("/api/oci/resources")
    def oci_resources():
        try:
            configuration = app.credentials_store.status()
            settings = TaskSettings.from_form(
                request.form,
                oci_config_file=app.credentials_store.config_file,
                oci_profile=configuration["profile"],
            )
            return jsonify(app.resource_loader(settings))
        except (KeyError, ValueError, oci.exceptions.ConfigFileNotFound, oci.exceptions.InvalidConfig) as exc:
            return jsonify(error=t("errors.oci_invalid", error=exc)), 400
        except oci.exceptions.ServiceError as exc:
            return jsonify(error=t("errors.oci_request", message=exc.message, status=exc.status)), 400

    @app.post("/api/oci/configure")
    def configure_oci():
        private_key = request.files.get("private_key")
        if private_key is None or not private_key.filename:
            return jsonify(error=t("errors.pem_required")), 400
        try:
            result = app.credentials_store.save(
                request.form.get("config_text", ""),
                private_key.stream.read(128 * 1024 + 1),
            )
            return jsonify(result)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

    @app.post("/api/ssh-keys")
    def generate_ssh_key():
        key = app.ssh_key_store.generate()
        key["download_url"] = url_for("download_ssh_key", key_id=key["id"])
        return jsonify(key)

    @app.get("/api/ssh-keys/<key_id>/download")
    def download_ssh_key(key_id):
        try:
            path = app.ssh_key_store.path_for(key_id)
        except (ValueError, FileNotFoundError):
            abort(404)
        return send_file(
            path,
            mimetype="application/x-pem-file",
            as_attachment=True,
            download_name="oracle-arm-ssh.key",
        )

    @app.post("/api/start")
    def start():
        try:
            spec = InstanceSpec.from_form(request.form)
            configuration = app.credentials_store.status()
            settings = TaskSettings.from_form(
                request.form,
                oci_config_file=app.credentials_store.config_file,
                oci_profile=configuration["profile"],
            )
            app.job_manager.start(spec, settings)
        except (ValueError, RuntimeError) as exc:
            return jsonify(error=str(exc)), 400
        return jsonify(ok=True)

    @app.post("/api/stop")
    def stop():
        try:
            app.job_manager.stop()
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 400
        return jsonify(ok=True)

    @app.post("/api/notifications/test")
    def test_notification():
        channel = request.form.get("channel", "")
        enabled_field = {
            "telegram": "telegram_enabled",
            "bark": "bark_enabled",
            "pushplus": "pushplus_enabled",
            "serverchan": "serverchan_enabled",
            "gotify": "gotify_enabled",
            "ntfy": "ntfy_enabled",
            "webhook": "webhook_enabled",
            "email": "email_enabled",
        }.get(channel)
        if enabled_field is None:
            return jsonify(error=t("errors.channel_unsupported")), 400

        form = request.form.copy()
        for field in (
            "telegram_enabled",
            "bark_enabled",
            "pushplus_enabled",
            "serverchan_enabled",
            "gotify_enabled",
            "ntfy_enabled",
            "webhook_enabled",
            "email_enabled",
        ):
            form.pop(field, None)
        form[enabled_field] = "true"
        try:
            configuration = app.credentials_store.status()
            settings = TaskSettings.from_form(
                form,
                oci_config_file=app.credentials_store.config_file,
                oci_profile=configuration["profile"],
            )
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

        message = t("errors.test_message")
        outcomes = app.notification_sender(settings, message, emit=lambda _: None)
        outcome = outcomes[0] if outcomes else None
        if not outcome or not outcome["ok"]:
            detail = outcome["detail"] if outcome else t("errors.not_sent")
            return jsonify(error=t("errors.test_failed", detail=detail)), 502
        return jsonify(ok=True, message=t("errors.test_sent"))

    @app.post("/api/settings/password")
    def change_password():
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirmation = request.form.get("confirm_password", "")
        if not app.password_store.verify(current_password):
            return jsonify(error=t("errors.password_wrong")), 400
        if len(new_password) < 8:
            return jsonify(error=t("errors.password_short")), 400
        if new_password != confirmation:
            return jsonify(error=t("errors.password_mismatch")), 400
        if current_password == new_password:
            return jsonify(error=t("errors.password_same")), 400
        app.password_store.update(new_password)
        return jsonify(ok=True)

    return app
