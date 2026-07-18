import smtplib
from email.message import EmailMessage

from urllib.parse import quote

import requests


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
    mail["Subject"] = "A1 Control 任务通知"
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
    if settings.webhook_enabled:
        payload = WEBHOOK_PAYLOADS[settings.webhook_provider](message)
        deliveries.append(("Webhook", lambda: post(
            settings.webhook_url,
            json=payload,
            timeout=15,
        )))
    if settings.email_enabled:
        deliveries.append(("邮箱", lambda: _send_email(settings, message, smtp=smtp, smtp_ssl=smtp_ssl)))

    for channel, deliver in deliveries:
        try:
            response = deliver()
            if response is not None and response.status_code >= 400:
                emit("{} 通知发送失败（HTTP {}）".format(channel, response.status_code))
                outcomes.append({"channel": channel, "ok": False, "detail": "HTTP {}".format(response.status_code)})
            else:
                emit("{} 通知已发送".format(channel))
                outcomes.append({"channel": channel, "ok": True, "detail": ""})
        except (requests.RequestException, OSError, smtplib.SMTPException) as exc:
            emit("{} 通知发送失败（{}）".format(channel, type(exc).__name__))
            outcomes.append({"channel": channel, "ok": False, "detail": type(exc).__name__})
    return outcomes
