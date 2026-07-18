import smtplib
from email.message import EmailMessage

from urllib.parse import quote

import requests

from .i18n import t


WEBHOOK_PAYLOADS = {
    "generic": lambda message: {"title": "A1 Control", "message": message},
    "feishu": lambda message: {"msg_type": "text", "content": {"text": message}},
    "dingtalk": lambda message: {"msgtype": "text", "text": {"content": message}},
    "wecom": lambda message: {"msgtype": "text", "text": {"content": message}},
    "discord": lambda message: {"content": message},
    "slack": lambda message: {"text": message},
}


def _send_email(settings, message, smtp=smtplib.SMTP, smtp_ssl=smtplib.SMTP_SSL):
    mail = EmailMessage()
    mail["Subject"] = t("job.notify_title")
    mail["From"] = settings.email_from
    mail["To"] = settings.email_to
    mail.set_content(message)
    client = smtp_ssl(settings.email_smtp_host, settings.email_smtp_port, timeout=15) if settings.email_security == "ssl" else smtp(settings.email_smtp_host, settings.email_smtp_port, timeout=15)
    try:
        if settings.email_security == "starttls":
            client.starttls()
        client.login(settings.email_username, settings.email_password)
        client.send_message(mail)
    finally:
        client.quit()


def send_notifications(settings, message, emit=print, post=requests.post, smtp=smtplib.SMTP, smtp_ssl=smtplib.SMTP_SSL):
    deliveries = []
    outcomes = []
    if settings.telegram_enabled:
        deliveries.append(("Telegram", lambda: post(
            "https://{}/bot{}/sendMessage".format(
                settings.telegram_api_host, settings.telegram_token
            ),
            data={"chat_id": settings.telegram_chat_id, "text": message},
            timeout=15,
        )))
    if settings.bark_enabled:
        deliveries.append(("Bark", lambda: post(
            "{}/{}".format(
                settings.bark_server.rstrip("/"), quote(settings.bark_device_key, safe="")
            ),
            json={"title": "A1 Control", "body": message, "group": "A1 Control"},
            timeout=15,
        )))
    if settings.pushplus_enabled:
        deliveries.append(("PushPlus", lambda: post(
            "https://www.pushplus.plus/send",
            json={"token": settings.pushplus_token, "title": "A1 Control", "content": message, "template": "txt", **({"topic": settings.pushplus_topic} if settings.pushplus_topic else {})},
            timeout=15,
        )))
    if settings.serverchan_enabled:
        deliveries.append((t("notify_editor.serverchan_label"), lambda: post(
            "https://sctapi.ftqq.com/{}.send".format(settings.serverchan_sendkey),
            data={"title": "A1 Control", "desp": message},
            timeout=15,
        )))
    if settings.gotify_enabled:
        deliveries.append(("Gotify", lambda: post(
            "{}/message".format(settings.gotify_server.rstrip("/")),
            json={"title": "A1 Control", "message": message, "priority": 5},
            headers={"X-Gotify-Key": settings.gotify_app_token},
            timeout=15,
        )))
    if settings.ntfy_enabled:
        deliveries.append(("ntfy", lambda: post(
            "{}/{}".format(settings.ntfy_server.rstrip("/"), quote(settings.ntfy_topic, safe="")),
            json={"topic": settings.ntfy_topic, "title": "A1 Control", "message": message, "priority": 4},
            timeout=15,
        )))
    if settings.webhook_enabled:
        payload = WEBHOOK_PAYLOADS[settings.webhook_provider](message)
        deliveries.append(("Webhook", lambda: post(
            settings.webhook_url,
            json=payload,
            timeout=15,
        )))
    if settings.email_enabled:
        deliveries.append((t("notify_editor.email_label"), lambda: _send_email(settings, message, smtp=smtp, smtp_ssl=smtp_ssl)))

    for channel, deliver in deliveries:
        try:
            response = deliver()
            if response is not None and response.status_code >= 400:
                emit(t("job.notify_fail_http", channel=channel, status=response.status_code))
                outcomes.append({"channel": channel, "ok": False, "detail": "HTTP {}".format(response.status_code)})
            else:
                emit(t("job.notify_ok", channel=channel))
                outcomes.append({"channel": channel, "ok": True, "detail": ""})
        except (requests.RequestException, OSError, smtplib.SMTPException) as exc:
            emit(t("job.notify_fail", channel=channel, error=type(exc).__name__))
            outcomes.append({"channel": channel, "ok": False, "detail": type(exc).__name__})
    return outcomes
