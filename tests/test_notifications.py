import requests

from oracle_arm_console.notifications import send_notifications
from oracle_arm_console.settings import TaskSettings


class Response:
    def __init__(self, status_code=200):
        self.status_code = status_code


def settings(**overrides):
    values = {
        "telegram_enabled": False,
        "bark_enabled": False,
        "webhook_enabled": False,
    }
    values.update(overrides)
    return TaskSettings(**values)


def test_sends_bark_and_feishu_payloads():
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    send_notifications(
        settings(
            bark_enabled=True,
            bark_server="https://bark.example.test",
            bark_device_key="device/key",
            webhook_enabled=True,
            webhook_provider="feishu",
            webhook_url="https://hooks.example.test/robot",
        ),
        "Instance created",
        emit=lambda _: None,
        post=post,
    )

    assert calls[0][0] == "https://bark.example.test/device%2Fkey"
    assert calls[0][1]["json"]["body"] == "Instance created"
    assert calls[1][1]["json"] == {
        "msg_type": "text",
        "content": {"text": "Instance created"},
    }


def test_notification_failure_does_not_stop_other_channels():
    calls = []
    logs = []

    def post(url, **kwargs):
        calls.append(url)
        if "telegram" in url:
            raise requests.ConnectionError("secret URL must not reach logs")
        return Response(204)

    send_notifications(
        settings(
            telegram_enabled=True,
            telegram_token="secret-token",
            telegram_chat_id="123",
            bark_enabled=True,
            bark_device_key="device-key",
        ),
        "done",
        emit=logs.append,
        post=post,
    )

    assert len(calls) == 2
    assert logs == ["Telegram notification failed (ConnectionError)", "Bark notification sent"]
    assert "secret-token" not in "".join(logs)


def test_generic_webhook_payload():
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs)
        return Response()

    send_notifications(
        settings(
            webhook_enabled=True,
            webhook_provider="generic",
            webhook_url="https://hooks.example.test/a1",
        ),
        "done",
        emit=lambda _: None,
        post=post,
    )

    assert calls[0]["json"] == {"title": "A1 Control", "message": "done"}


def test_sends_pushplus_serverchan_gotify_and_ntfy():
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    send_notifications(
        settings(
            pushplus_enabled=True,
            pushplus_token="push-token",
            pushplus_topic="team",
            serverchan_enabled=True,
            serverchan_sendkey="SCT-key",
            gotify_enabled=True,
            gotify_server="https://gotify.example.test",
            gotify_app_token="gotify-token",
            ntfy_enabled=True,
            ntfy_topic="a1 alerts",
        ),
        "done",
        emit=lambda _: None,
        post=post,
    )

    assert calls[0][1]["json"]["topic"] == "team"
    assert calls[1][0].endswith("/SCT-key.send")
    assert calls[2][1]["headers"]["X-Gotify-Key"] == "gotify-token"
    assert calls[3][0].endswith("/a1%20alerts")


def test_sends_email_over_starttls():
    class FakeSMTP:
        instances = []

        def __init__(self, host, port, timeout):
            self.host, self.port, self.timeout = host, port, timeout
            self.actions = []
            self.__class__.instances.append(self)

        def starttls(self):
            self.actions.append("starttls")

        def login(self, username, password):
            self.actions.append(("login", username, password))

        def send_message(self, message):
            self.actions.append(message)

        def quit(self):
            self.actions.append("quit")

    send_notifications(
        settings(
            email_enabled=True,
            email_smtp_host="smtp.example.test",
            email_smtp_port=587,
            email_security="starttls",
            email_username="sender@example.test",
            email_password="secret",
            email_from="sender@example.test",
            email_to="receiver@example.test",
        ),
        "done",
        emit=lambda _: None,
        smtp=FakeSMTP,
    )

    client = FakeSMTP.instances[0]
    assert client.host == "smtp.example.test"
    assert "starttls" in client.actions
    assert client.actions[1] == ("login", "sender@example.test", "secret")
    assert client.actions[2]["Subject"] == "A1 Control job notification"
    assert "done" in client.actions[2].get_content()
