import re
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

from .i18n import t


HOST_PATTERN = re.compile(r"[A-Za-z0-9.-]+(?::[0-9]{1,5})?")
EMAIL_HOST_PATTERN = re.compile(r"[A-Za-z0-9.-]+")
WEBHOOK_PROVIDERS = {"generic", "feishu", "dingtalk", "wecom", "discord", "slack"}


def _notification_url(value, label):
    if len(value) > 2048:
        raise ValueError(t("errors.field_too_long", field=label))
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(t("errors.field_url", field=label))
    return value


@dataclass(frozen=True)
class TaskSettings:
    oci_config_file: str = "~/.oci/config"
    oci_profile: str = "DEFAULT"
    retry_interval: float = 10.0
    telegram_enabled: bool = False
    telegram_token: str = ""
    telegram_chat_id: str = ""
    telegram_api_host: str = "api.telegram.org"
    bark_enabled: bool = False
    bark_server: str = "https://api.day.app"
    bark_device_key: str = ""
    pushplus_enabled: bool = False
    pushplus_token: str = ""
    pushplus_topic: str = ""
    serverchan_enabled: bool = False
    serverchan_sendkey: str = ""
    gotify_enabled: bool = False
    gotify_server: str = ""
    gotify_app_token: str = ""
    ntfy_enabled: bool = False
    ntfy_server: str = "https://ntfy.sh"
    ntfy_topic: str = ""
    webhook_enabled: bool = False
    webhook_provider: str = "generic"
    webhook_url: str = ""
    email_enabled: bool = False
    email_smtp_host: str = "smtp.example.com"
    email_smtp_port: int = 587
    email_security: str = "starttls"
    email_username: str = ""
    email_password: str = ""
    email_from: str = ""
    email_to: str = ""

    @classmethod
    def from_form(cls, form, oci_config_file=None, oci_profile=None):
        try:
            retry_interval = float(form.get("retry_interval", "10").strip())
        except ValueError as exc:
            raise ValueError(t("errors.retry_not_number")) from exc
        if not 1 <= retry_interval <= 300:
            raise ValueError(t("errors.retry_range"))

        profile = (oci_profile or "DEFAULT").strip()
        api_host = form.get("telegram_api_host", "api.telegram.org").strip()
        enabled = form.get("telegram_enabled") == "true"
        token = form.get("telegram_token", "").strip()
        chat_id = form.get("telegram_chat_id", "").strip()
        bark_enabled = form.get("bark_enabled") == "true"
        bark_server = form.get("bark_server", "https://api.day.app").strip()
        bark_device_key = form.get("bark_device_key", "").strip()
        pushplus_enabled = form.get("pushplus_enabled") == "true"
        pushplus_token = form.get("pushplus_token", "").strip()
        pushplus_topic = form.get("pushplus_topic", "").strip()
        serverchan_enabled = form.get("serverchan_enabled") == "true"
        serverchan_sendkey = form.get("serverchan_sendkey", "").strip()
        gotify_enabled = form.get("gotify_enabled") == "true"
        gotify_server = form.get("gotify_server", "").strip()
        gotify_app_token = form.get("gotify_app_token", "").strip()
        ntfy_enabled = form.get("ntfy_enabled") == "true"
        ntfy_server = form.get("ntfy_server", "https://ntfy.sh").strip()
        ntfy_topic = form.get("ntfy_topic", "").strip()
        webhook_enabled = form.get("webhook_enabled") == "true"
        webhook_provider = form.get("webhook_provider", "generic").strip()
        webhook_url = form.get("webhook_url", "").strip()
        email_enabled = form.get("email_enabled") == "true"
        email_smtp_host = form.get("email_smtp_host", "").strip()
        try:
            email_smtp_port = int(form.get("email_smtp_port", "587").strip())
        except ValueError as exc:
            raise ValueError(t("errors.email_port_number")) from exc
        email_security = form.get("email_security", "starttls").strip()
        email_username = form.get("email_username", "").strip()
        email_password = form.get("email_password", "")
        email_from = form.get("email_from", "").strip()
        email_to = form.get("email_to", "").strip()
        if not profile or len(profile) > 128:
            raise ValueError(t("errors.oci_profile_invalid"))
        if not HOST_PATTERN.fullmatch(api_host):
            raise ValueError(t("errors.tg_host_invalid"))
        if enabled and (not token or not chat_id):
            raise ValueError(t("errors.tg_required"))
        _notification_url(bark_server, t("errors.bark_server_label"))
        if bark_enabled and not bark_device_key:
            raise ValueError(t("errors.bark_required"))
        if pushplus_enabled and not pushplus_token:
            raise ValueError(t("errors.pushplus_required"))
        if serverchan_enabled and not serverchan_sendkey:
            raise ValueError(t("errors.serverchan_required"))
        if gotify_enabled and (not gotify_server or not gotify_app_token):
            raise ValueError(t("errors.gotify_required"))
        if gotify_server:
            _notification_url(gotify_server, t("errors.gotify_server_label"))
        _notification_url(ntfy_server, t("errors.ntfy_server_label"))
        if ntfy_enabled and not ntfy_topic:
            raise ValueError(t("errors.ntfy_required"))
        if webhook_provider not in WEBHOOK_PROVIDERS:
            raise ValueError(t("errors.webhook_provider_invalid"))
        if webhook_enabled:
            if not webhook_url:
                raise ValueError(t("errors.webhook_required"))
            _notification_url(webhook_url, t("errors.webhook_url_label"))
        if email_enabled:
            if not EMAIL_HOST_PATTERN.fullmatch(email_smtp_host) or not 1 <= email_smtp_port <= 65535:
                raise ValueError(t("errors.email_host_port"))
            if email_security not in {"starttls", "ssl", "none"}:
                raise ValueError(t("errors.email_security_invalid"))
            if not email_username or not email_password or not email_from or not email_to:
                raise ValueError(t("errors.email_required"))
        return cls(
            oci_config_file=oci_config_file or "~/.oci/config",
            oci_profile=profile,
            retry_interval=retry_interval,
            telegram_enabled=enabled,
            telegram_token=token,
            telegram_chat_id=chat_id,
            telegram_api_host=api_host,
            bark_enabled=bark_enabled,
            bark_server=bark_server,
            bark_device_key=bark_device_key,
            pushplus_enabled=pushplus_enabled,
            pushplus_token=pushplus_token,
            pushplus_topic=pushplus_topic,
            serverchan_enabled=serverchan_enabled,
            serverchan_sendkey=serverchan_sendkey,
            gotify_enabled=gotify_enabled,
            gotify_server=gotify_server,
            gotify_app_token=gotify_app_token,
            ntfy_enabled=ntfy_enabled,
            ntfy_server=ntfy_server,
            ntfy_topic=ntfy_topic,
            webhook_enabled=webhook_enabled,
            webhook_provider=webhook_provider,
            webhook_url=webhook_url,
            email_enabled=email_enabled,
            email_smtp_host=email_smtp_host,
            email_smtp_port=email_smtp_port,
            email_security=email_security,
            email_username=email_username,
            email_password=email_password,
            email_from=email_from,
            email_to=email_to,
        )

    def as_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, values):
        values = dict(values)
        values["email_smtp_port"] = int(values.get("email_smtp_port", 587))
        return cls(**values)
