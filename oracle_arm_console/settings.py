import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse


HOST_PATTERN = re.compile(r"[A-Za-z0-9.-]+(?::[0-9]{1,5})?")
EMAIL_HOST_PATTERN = re.compile(r"[A-Za-z0-9.-]+")
WEBHOOK_PROVIDERS = {"generic", "feishu", "dingtalk", "wecom", "discord", "slack"}


def _notification_url(value, label):
    if len(value) > 2048:
        raise ValueError("{}过长".format(label))
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("{}必须是有效的 HTTP 或 HTTPS 地址".format(label))
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
            raise ValueError("重试间隔必须是数字") from exc
        if not 1 <= retry_interval <= 300:
            raise ValueError("重试间隔必须在 1 到 300 秒之间")

        profile = (oci_profile or os.environ.get("OCI_PROFILE", "DEFAULT")).strip()
        api_host = form.get("telegram_api_host", "api.telegram.org").strip()
        enabled = form.get("telegram_enabled") == "true"
        token = form.get("telegram_token", "").strip() or os.environ.get("TELEGRAM_TOKEN", "")
        chat_id = form.get("telegram_chat_id", "").strip() or os.environ.get("TELEGRAM_CHAT_ID", "")
        bark_enabled = form.get("bark_enabled") == "true"
        bark_server = form.get("bark_server", "https://api.day.app").strip()
        bark_device_key = form.get("bark_device_key", "").strip() or os.environ.get("BARK_DEVICE_KEY", "")
        webhook_enabled = form.get("webhook_enabled") == "true"
        webhook_provider = form.get("webhook_provider", "generic").strip()
        webhook_url = form.get("webhook_url", "").strip() or os.environ.get("WEBHOOK_URL", "")
        email_enabled = form.get("email_enabled") == "true"
        email_smtp_host = form.get("email_smtp_host", "").strip() or os.environ.get("EMAIL_SMTP_HOST", "")
        try:
            email_smtp_port = int(form.get("email_smtp_port", "587").strip())
        except ValueError as exc:
            raise ValueError("邮箱 SMTP 端口必须是数字") from exc
        email_security = form.get("email_security", "starttls").strip()
        email_username = form.get("email_username", "").strip() or os.environ.get("EMAIL_USERNAME", "")
        email_password = form.get("email_password", "") or os.environ.get("EMAIL_PASSWORD", "")
        email_from = form.get("email_from", "").strip() or os.environ.get("EMAIL_FROM", "")
        email_to = form.get("email_to", "").strip() or os.environ.get("EMAIL_TO", "")
        if not profile or len(profile) > 128:
            raise ValueError("OCI Profile 格式不正确")
        if not HOST_PATTERN.fullmatch(api_host):
            raise ValueError("Telegram API 地址不能包含协议或路径")
        if enabled and (not token or not chat_id):
            raise ValueError("启用 Telegram 后必须填写 Bot Token 和 Chat ID")
        _notification_url(bark_server, "Bark 服务地址")
        if bark_enabled and not bark_device_key:
            raise ValueError("启用 Bark 后必须填写设备密钥")
        if webhook_provider not in WEBHOOK_PROVIDERS:
            raise ValueError("Webhook 类型不受支持")
        if webhook_enabled:
            if not webhook_url:
                raise ValueError("启用 Webhook 后必须填写通知地址")
            _notification_url(webhook_url, "Webhook 地址")
        if email_enabled:
            if not EMAIL_HOST_PATTERN.fullmatch(email_smtp_host) or not 1 <= email_smtp_port <= 65535:
                raise ValueError("邮箱 SMTP 服务器或端口不正确")
            if email_security not in {"starttls", "ssl", "none"}:
                raise ValueError("邮箱加密方式不受支持")
            if not email_username or not email_password or not email_from or not email_to:
                raise ValueError("启用邮箱通知后必须填写 SMTP 账号、密码、发件人和收件人")
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
