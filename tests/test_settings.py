import pytest

from oracle_arm_console.settings import TaskSettings


def test_form_settings_are_validated():
    settings = TaskSettings.from_form(
        {
            "retry_interval": "15",
            "telegram_api_host": "api.telegram.org",
        },
        oci_config_file="~/.oci/custom",
        oci_profile="ARM",
    )
    assert settings.oci_profile == "ARM"
    assert settings.retry_interval == 15


def test_telegram_requires_credentials(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "must-not-be-imported")
    with pytest.raises(ValueError, match="Bot token"):
        TaskSettings.from_form({
            "retry_interval": "10",
            "oci_profile": "DEFAULT",
            "telegram_enabled": "true",
            "telegram_api_host": "api.telegram.org",
        })


def test_form_does_not_import_notification_credentials_from_environment(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "env-token")
    with pytest.raises(ValueError, match="Bot token"):
        TaskSettings.from_form({
            "retry_interval": "10",
            "telegram_enabled": "true",
            "telegram_chat_id": "123",
        })


def test_bark_and_webhook_are_validated():
    with pytest.raises(ValueError, match="Device key"):
        TaskSettings.from_form({
            "retry_interval": "10",
            "telegram_api_host": "api.telegram.org",
            "bark_enabled": "true",
            "bark_server": "https://api.day.app",
        })

    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        TaskSettings.from_form({
            "retry_interval": "10",
            "telegram_api_host": "api.telegram.org",
            "webhook_enabled": "true",
            "webhook_provider": "generic",
            "webhook_url": "file:///tmp/message",
        })


def test_notification_settings_round_trip_through_task_file():
    settings = TaskSettings.from_form({
        "retry_interval": "10",
        "telegram_api_host": "api.telegram.org",
        "bark_enabled": "true",
        "bark_server": "https://bark.example.test",
        "bark_device_key": "device-key",
        "webhook_enabled": "true",
        "webhook_provider": "feishu",
        "webhook_url": "https://hooks.example.test/robot",
    })

    restored = TaskSettings.from_dict(settings.as_dict())
    assert restored.bark_enabled is True
    assert restored.bark_device_key == "device-key"
    assert restored.webhook_provider == "feishu"
    assert restored.webhook_url == "https://hooks.example.test/robot"


def test_email_settings_are_validated_and_round_trip():
    settings = TaskSettings.from_form({
        "retry_interval": "10",
        "email_enabled": "true",
        "email_smtp_host": "smtp.example.test",
        "email_smtp_port": "465",
        "email_security": "ssl",
        "email_username": "sender@example.test",
        "email_password": "secret",
        "email_from": "sender@example.test",
        "email_to": "receiver@example.test",
    })

    assert settings.email_smtp_port == 465
    assert settings.email_security == "ssl"
    assert TaskSettings.from_dict(settings.as_dict()).email_enabled is True


def test_new_push_channels_are_validated_and_round_trip():
    configured = TaskSettings.from_form({
        "retry_interval": "10",
        "pushplus_enabled": "true",
        "pushplus_token": "push-token",
        "serverchan_enabled": "true",
        "serverchan_sendkey": "SCT-key",
        "gotify_enabled": "true",
        "gotify_server": "https://gotify.example.test",
        "gotify_app_token": "gotify-token",
        "ntfy_enabled": "true",
        "ntfy_server": "https://ntfy.example.test",
        "ntfy_topic": "a1",
    })

    restored = TaskSettings.from_dict(configured.as_dict())
    assert restored.pushplus_token == "push-token"
    assert restored.serverchan_sendkey == "SCT-key"
    assert restored.gotify_server == "https://gotify.example.test"
    assert restored.ntfy_topic == "a1"
