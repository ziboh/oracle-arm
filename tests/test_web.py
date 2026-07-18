import io

from oracle_arm_console import create_app
from oracle_arm_console.ssh_keys import SshKeyStore

from test_instance import VALID_FORM


OCI_RESOURCES = {
    "region": "ap-tokyo-1",
    "compartments": [{"id": "ocid1.tenancy.test", "name": "根区间 / Test"}],
    "availability_domains": [{"name": "NAOy:AP-TOKYO-1-AD-1"}],
    "subnets": [{"id": "ocid1.subnet.test", "name": "public", "compartment_name": "根区间 / Test", "availability_domain": None}],
    "images": [{"id": "ocid1.image.test", "name": "Oracle-Linux-9-aarch64", "operating_system": "Oracle Linux", "version": "9"}],
    "storage": {"total_gb": 200.0, "used_gb": 97.0, "available_gb": 103.0, "minimum_boot_volume_gb": 50.0},
}


class FakeCredentialsStore:
    config_file = "/data/oci/config"

    def status(self):
        return {"configured": False, "profile": "DEFAULT", "region": ""}

    def save(self, config_text, private_key):
        assert "[DEFAULT]" in config_text
        assert private_key == b"private-key"
        return {"config_file": "/data/oci/config", "profile": "DEFAULT", "region": "ap-tokyo-1"}


class ConfiguredFakeCredentialsStore(FakeCredentialsStore):
    def status(self):
        return {"configured": True, "profile": "ARM", "region": "ap-tokyo-1"}


class FakeSshKeyStore:
    def generate(self):
        return {
            "id": "abcdefghijklmnopqrstuvwx",
            "public_key": "ssh-ed25519 AAAA generated@example",
            "fingerprint": "SHA256:test",
        }


class FakeJobManager:
    def __init__(self):
        self.started = None
        self.settings = None
        self.stopped = False

    def status(self):
        return {"running": False, "state": "idle", "started_at": None, "finished_at": None, "exit_code": None, "logs": []}

    def start(self, spec, settings):
        self.started = spec
        self.settings = settings

    def stop(self):
        self.stopped = True


def make_client(credentials_store=None, notification_sender=None):
    manager = FakeJobManager()
    app = create_app(
        {
            "TESTING": True,
            "WEB_PASSWORD": "test-password",
            "SECRET_KEY": "test-secret",
            "SECURITY_FILE": None,
        },
        manager,
        resource_loader=lambda settings: OCI_RESOURCES,
        credentials_store=credentials_store or FakeCredentialsStore(),
        ssh_key_store=FakeSshKeyStore(),
        notification_sender=notification_sender,
    )
    return app.test_client(), manager


def login(client, password="test-password"):
    with client.session_transaction() as session:
        session["csrf_token"] = "token"
    return client.post("/login", data={"password": password, "csrf_token": "token"})


def csrf(client):
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_dashboard_requires_login():
    client, _ = make_client()
    assert client.get("/").status_code == 302
    assert client.get("/api/status").status_code == 401
    assert client.get("/healthz").status_code == 200


def test_login_and_dashboard():
    client, _ = make_client()
    assert login(client).status_code == 302
    page = client.get("/").get_data(as_text=True)
    assert "创建 Ampere A1" in page
    assert "读取 OCI 资源" in page
    assert "操作系统分类" in page
    assert "已有公钥" in page
    assert "粘贴公钥" in page
    assert 'id="boot-volume-range"' in page
    assert 'class="storage-meter storage-selector"' in page
    assert "滚动鼠标滚轮" in page
    assert 'id="ssh-public-key-file"' in page
    assert "免费块存储额度" in page
    assert "创建结果通知" in page
    assert "选择接收方式" in page
    assert 'data-channel-option="telegram"' in page
    assert 'id="test-notification-editor"' in page
    assert "/static/favicon.svg" in page
    assert 'class="mobile-menu"' in page
    assert 'class="mobile-nav"' not in page
    assert client.get("/static/favicon.svg").mimetype == "image/svg+xml"
    assert "配置文件<input" not in page
    assert '<option value="" selected disabled hidden>先读取 OCI 资源</option>' in page


def test_logs_page_is_separate_and_requires_login():
    client, _ = make_client()
    assert client.get("/logs").status_code == 302
    login(client)
    page = client.get("/logs")
    assert page.status_code == 200
    assert 'id="logs-page-title"' in page.get_data(as_text=True)
    assert 'class="logs-page-output"' in page.get_data(as_text=True)
    assert "/static/logs.js" in page.get_data(as_text=True)
    assert 'class="mobile-menu"' in page.get_data(as_text=True)


def test_settings_page_is_separate_and_requires_login():
    client, _ = make_client(ConfiguredFakeCredentialsStore())
    assert client.get("/settings").status_code == 302
    login(client)
    page = client.get("/settings")
    content = page.get_data(as_text=True)
    assert page.status_code == 200
    assert 'id="settings-page-title"' in content
    assert "OCI API 凭据" in content
    assert "修改管理密码" in content
    assert "ARM" in content
    assert "ap-tokyo-1" in content
    assert "/static/settings.js" in content
    assert 'class="mobile-menu"' in content
    assert 'id="settings-dialog"' not in client.get("/").get_data(as_text=True)


def test_dashboard_shows_existing_credentials_as_editable():
    client, _ = make_client(ConfiguredFakeCredentialsStore())
    login(client)
    page = client.get("/").get_data(as_text=True)

    assert "替换 OCI 凭据" in page
    assert 'name="oci_profile"' not in page
    assert "OCI 私钥无法回显或单独编辑" in page


def test_wrong_password_is_rejected():
    client, _ = make_client()
    response = login(client, "wrong")
    assert "密码错误" in response.get_data(as_text=True)


def test_default_admin_password():
    app = create_app(
        {"TESTING": True, "WEB_PASSWORD": "admin", "SECRET_KEY": "test-secret", "SECURITY_FILE": None},
        FakeJobManager(),
        resource_loader=lambda settings: OCI_RESOURCES,
    )
    client = app.test_client()
    assert login(client, "admin").status_code == 302


def test_start_and_stop_task():
    client, manager = make_client()
    login(client)
    form = {
        **VALID_FORM,
        "csrf_token": csrf(client),
        "oci_config_file": "~/.oci/config",
        "oci_profile": "IGNORED",
        "retry_interval": "12",
        "telegram_api_host": "api.telegram.org",
    }
    response = client.post("/api/start", data=form)
    assert response.status_code == 200
    assert manager.started.image_id == "ocid1.image.test"
    assert manager.settings.oci_profile == "DEFAULT"
    assert manager.settings.oci_config_file == "/data/oci/config"
    assert manager.settings.retry_interval == 12
    assert client.post("/api/stop", data={"csrf_token": csrf(client)}).status_code == 200
    assert manager.stopped is True


def test_load_oci_resources():
    client, _ = make_client()
    login(client)
    response = client.post(
        "/api/oci/resources",
        data={
            "csrf_token": csrf(client),
            "oci_config_file": "~/.oci/config",
            "oci_profile": "DEFAULT",
            "retry_interval": "10",
            "telegram_api_host": "api.telegram.org",
        },
    )
    assert response.status_code == 200
    assert response.get_json()["images"][0]["operating_system"] == "Oracle Linux"


def test_import_oci_credentials():
    client, _ = make_client()
    login(client)
    response = client.post(
        "/api/oci/configure",
        data={
            "csrf_token": csrf(client),
            "config_text": "[DEFAULT]\nuser=test",
            "private_key": (io.BytesIO(b"private-key"), "oci.pem"),
        },
    )
    assert response.status_code == 200
    assert response.get_json()["config_file"] == "/data/oci/config"


def test_generate_ssh_key():
    client, _ = make_client()
    login(client)
    response = client.post("/api/ssh-keys", data={"csrf_token": csrf(client)})
    assert response.status_code == 200
    assert response.get_json()["public_key"].startswith("ssh-ed25519 ")
    assert response.get_json()["download_url"].endswith("/download")


def test_notification_test_enables_only_requested_channel():
    sent = []

    def sender(settings, message, emit):
        sent.append((settings, message))
        return [{"channel": "Telegram", "ok": True, "detail": ""}]

    client, _ = make_client(notification_sender=sender)
    login(client)
    response = client.post(
        "/api/notifications/test",
        data={
            "csrf_token": csrf(client),
            "channel": "telegram",
            "telegram_token": "secret-token",
            "telegram_chat_id": "123",
            "telegram_api_host": "api.telegram.org",
            "bark_enabled": "true",
        },
    )

    assert response.status_code == 200
    assert sent[0][0].telegram_enabled is True
    assert sent[0][0].bark_enabled is False
    assert "通知测试" in sent[0][1]


def test_notification_test_rejects_incomplete_configuration():
    client, _ = make_client(notification_sender=lambda *args: [])
    login(client)
    response = client.post(
        "/api/notifications/test",
        data={
            "csrf_token": csrf(client),
            "channel": "webhook",
            "telegram_api_host": "api.telegram.org",
        },
    )
    assert response.status_code == 400
    assert "必须填写通知地址" in response.get_json()["error"]


def test_download_generated_private_key_from_relative_data_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = create_app(
        {"TESTING": True, "WEB_PASSWORD": "admin", "SECRET_KEY": "test-secret", "SECURITY_FILE": None},
        FakeJobManager(),
        resource_loader=lambda settings: OCI_RESOURCES,
        credentials_store=FakeCredentialsStore(),
        ssh_key_store=SshKeyStore("ssh-keys"),
    )
    client = app.test_client()
    login(client, "admin")
    generated = client.post("/api/ssh-keys", data={"csrf_token": csrf(client)}).get_json()
    response = client.get(generated["download_url"])
    assert response.status_code == 200
    assert "oracle-arm-ssh.key" in response.headers["Content-Disposition"]
    assert response.data.startswith(b"-----BEGIN OPENSSH PRIVATE KEY-----")


def test_change_password():
    client, _ = make_client()
    login(client)
    token = csrf(client)
    wrong = client.post(
        "/api/settings/password",
        data={
            "csrf_token": token,
            "current_password": "wrong",
            "new_password": "new-password",
            "confirm_password": "new-password",
        },
    )
    assert wrong.status_code == 400
    changed = client.post(
        "/api/settings/password",
        data={
            "csrf_token": token,
            "current_password": "test-password",
            "new_password": "new-password",
            "confirm_password": "new-password",
        },
    )
    assert changed.status_code == 200
    client.post("/logout", data={"csrf_token": token})
    assert "密码错误" in login(client, "test-password").get_data(as_text=True)
    assert login(client, "new-password").status_code == 302
