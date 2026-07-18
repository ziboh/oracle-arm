import os
import re
from dataclasses import dataclass
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

        profile = (oci_profile or os.environ.get("OCI_PROFILE", "DEFAULT")).strip()
        api_host = form.get("telegram_api_host", "api.telegram.org").strip()
        enabled = form.get("telegram_enabled") == "true"
        token = form.get("telegram_token", "").strip() or os.environ.get("TELEGRAM_TOKEN", "")
        chat_id = form.get("telegram_chat_id", "").strip() or os.environ.get("TELEGRAM_CHAT_ID", "")
        bark_enabled = form.get("bark_enabled") == "true"
        bark_server = form.get("bark_server", "https://api.day.app").strip()
        bark_device_key = form.get("bark_device_key", "").strip() or os.environ.get("BARK_DEVICE_KEY", "")
        pushplus_enabled = form.get("pushplus_enabled") == "true"
        pushplus_token = form.get("pushplus_token", "").strip() or os.environ.get("PUSHPLUS_TOKEN", "")
        pushplus_topic = form.get("pushplus_topic", "").strip() or os.environ.get("PUSHPLUS_TOPIC", "")
        serverchan_enabled = form.get("serverchan_enabled") == "true"
        serverchan_sendkey = form.get("serverchan_sendkey", "").strip() or os.environ.get("SERVERCHAN_SENDKEY", "")
        gotify_enabled = form.get("gotify_enabled") == "true"
        gotify_server = form.get("gotify_server", "").strip() or os.environ.get("GOTIFY_SERVER", "")
        gotify_app_token = form.get("gotify_app_token", "").strip() or os.environ.get("GOTIFY_APP_TOKEN", "")
        ntfy_enabled = form.get("ntfy_enabled") == "true"
        ntfy_server = form.get("ntfy_server", "https://ntfy.sh").strip()
        ntfy_topic = form.get("ntfy_topic", "").strip() or os.environ.get("NTFY_TOPIC", "")
        webhook_enabled = form.get("webhook_enabled") == "true"
        webhook_provider = form.get("webhook_provider", "generic").strip()
        webhook_url = form.get("webhook_url", "").strip() or os.environ.get("WEBHOOK_URL", "")
        email_enabled = form.get("email_enabled") == "true"
        email_smtp_host = form.get("email_smtp_host", "").strip() or os.environ.get("EMAIL_SMTP_HOST", "")
        try:
            email_smtp_port = int(form.get("email_smtp_port", "587").strip())
        except ValueError as exc:
            raise ValueError(t("errors.email_port_number")) from exc
        email_security = form.get("email_security", "starttls").strip()
        email_username = form.get("email_username", "").strip() or os.environ.get("EMAIL_USERNAME", "")
        email_password = form.get("email_password", "") or os.environ.get("EMAIL_PASSWORD", "")
        email_from = form.get("email_from", "").strip() or os.environ.get("EMAIL_FROM", "")
        email_to = form.get("email_to", "").strip() or os.environ.get("EMAIL_TO", "")
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
            oci_config_file=oci_config_file or os.environ.get("OCI_CONFIG_FILE", "~/.oci/config"),
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

    @classmethod
    def from_env(cls):
        return cls(
            oci_config_file=os.environ.get("OCI_CONFIG_FILE", "~/.oci/config"),
            oci_profile=os.environ.get("OCI_PROFILE", "DEFAULT"),
            retry_interval=float(os.environ.get("RETRY_INTERVAL", "10")),
            telegram_enabled=os.environ.get("TELEGRAM_ENABLED", "false").lower() == "true",
            telegram_token=os.environ.get("TELEGRAM_TOKEN", ""),
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
            telegram_api_host=os.environ.get("TELEGRAM_API_HOST", "api.telegram.org"),
            bark_enabled=os.environ.get("BARK_ENABLED", "false").lower() == "true",
            bark_server=os.environ.get("BARK_SERVER", "https://api.day.app"),
            bark_device_key=os.environ.get("BARK_DEVICE_KEY", ""),
            pushplus_enabled=os.environ.get("PUSHPLUS_ENABLED", "false").lower() == "true",
            pushplus_token=os.environ.get("PUSHPLUS_TOKEN", ""),
            pushplus_topic=os.environ.get("PUSHPLUS_TOPIC", ""),
            serverchan_enabled=os.environ.get("SERVERCHAN_ENABLED", "false").lower() == "true",
            serverchan_sendkey=os.environ.get("SERVERCHAN_SENDKEY", ""),
            gotify_enabled=os.environ.get("GOTIFY_ENABLED", "false").lower() == "true",
            gotify_server=os.environ.get("GOTIFY_SERVER", ""),
            gotify_app_token=os.environ.get("GOTIFY_APP_TOKEN", ""),
            ntfy_enabled=os.environ.get("NTFY_ENABLED", "false").lower() == "true",
            ntfy_server=os.environ.get("NTFY_SERVER", "https://ntfy.sh"),
            ntfy_topic=os.environ.get("NTFY_TOPIC", ""),
            webhook_enabled=os.environ.get("WEBHOOK_ENABLED", "false").lower() == "true",
            webhook_provider=os.environ.get("WEBHOOK_PROVIDER", "generic"),
            webhook_url=os.environ.get("WEBHOOK_URL", ""),
            email_enabled=os.environ.get("EMAIL_ENABLED", "false").lower() == "true",
            email_smtp_host=os.environ.get("EMAIL_SMTP_HOST", "smtp.example.com"),
            email_smtp_port=int(os.environ.get("EMAIL_SMTP_PORT", "587")),
            email_security=os.environ.get("EMAIL_SECURITY", "starttls"),
            email_username=os.environ.get("EMAIL_USERNAME", ""),
            email_password=os.environ.get("EMAIL_PASSWORD", ""),
            email_from=os.environ.get("EMAIL_FROM", ""),
            email_to=os.environ.get("EMAIL_TO", ""),
        )

    def as_environment(self):
        return {
            "OCI_CONFIG_FILE": self.oci_config_file,
            "OCI_PROFILE": self.oci_profile,
            "RETRY_INTERVAL": str(self.retry_interval),
            "TELEGRAM_ENABLED": str(self.telegram_enabled).lower(),
            "TELEGRAM_TOKEN": self.telegram_token,
            "TELEGRAM_CHAT_ID": self.telegram_chat_id,
            "TELEGRAM_API_HOST": self.telegram_api_host,
            "BARK_ENABLED": str(self.bark_enabled).lower(),
            "BARK_SERVER": self.bark_server,
            "BARK_DEVICE_KEY": self.bark_device_key,
            "PUSHPLUS_ENABLED": str(self.pushplus_enabled).lower(),
            "PUSHPLUS_TOKEN": self.pushplus_token,
            "PUSHPLUS_TOPIC": self.pushplus_topic,
            "SERVERCHAN_ENABLED": str(self.serverchan_enabled).lower(),
            "SERVERCHAN_SENDKEY": self.serverchan_sendkey,
            "GOTIFY_ENABLED": str(self.gotify_enabled).lower(),
            "GOTIFY_SERVER": self.gotify_server,
            "GOTIFY_APP_TOKEN": self.gotify_app_token,
            "NTFY_ENABLED": str(self.ntfy_enabled).lower(),
            "NTFY_SERVER": self.ntfy_server,
            "NTFY_TOPIC": self.ntfy_topic,
            "WEBHOOK_ENABLED": str(self.webhook_enabled).lower(),
            "WEBHOOK_PROVIDER": self.webhook_provider,
            "WEBHOOK_URL": self.webhook_url,
            "EMAIL_ENABLED": str(self.email_enabled).lower(),
            "EMAIL_SMTP_HOST": self.email_smtp_host,
            "EMAIL_SMTP_PORT": str(self.email_smtp_port),
            "EMAIL_SECURITY": self.email_security,
            "EMAIL_USERNAME": self.email_username,
            "EMAIL_PASSWORD": self.email_password,
            "EMAIL_FROM": self.email_from,
            "EMAIL_TO": self.email_to,
        }
