import io

from oracle_arm_console import create_app
from oracle_arm_console.ssh_keys import SshKeyStore

from test_instance import VALID_FORM


OCI_RESOURCES = {
    "region": "ap-tokyo-1",
    "compartments": [{"id": "ocid1.tenancy.test", "name": "Root compartment / Test"}],
    "availability_domains": [{"name": "NAOy:AP-TOKYO-1-AD-1"}],
    "subnets": [{"id": "ocid1.subnet.test", "name": "public", "compartment_name": "Root compartment / Test", "availability_domain": None}],
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
        self._seq = 0
        self.logs = []

    def status(self):
        return {
            "running": False,
            "state": "idle",
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "logs": list(self.logs),
            "seq": self._seq,
        }

    def wait_for_update(self, last_seq, timeout=1.0):
        return self.status()

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
    assert "Create Ampere A1" in page
    assert "Load OCI resources" in page
    assert "OS family" in page
    assert "Existing public key" in page
    assert "Paste a public key" in page
    assert 'id="boot-volume-range"' in page
    assert 'class="storage-meter storage-selector"' in page
    assert "mouse wheel" in page
    assert 'id="ssh-public-key-file"' in page
    assert "Free block storage quota" in page
    assert "Creation result notifications" in page
    assert "Choose delivery method" in page
    assert 'data-channel-option="telegram"' in page
    assert 'id="test-notification-editor"' in page
    assert "/static/favicon.svg" in page
    assert 'class="mobile-menu"' in page
    assert 'class="mobile-nav"' not in page
    assert 'class="lang-select"' in page
    assert client.get("/static/favicon.svg").mimetype == "image/svg+xml"
    assert "配置文件<input" not in page
    assert "Load OCI resources first" in page


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


def test_status_stream_requires_login_and_emits_sse():
    client, manager = make_client()
    assert client.get("/api/status/stream").status_code == 401
    login(client)
    manager.logs = ["00:00:01  hello"]
    manager._seq = 3
    response = client.get("/api/status/stream")
    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    # Read first SSE frame only (generator otherwise blocks on wait_for_update).
    chunk = next(response.response)
    if isinstance(chunk, bytes):
        chunk = chunk.decode("utf-8")
    assert chunk.startswith("data: ")
    assert "hello" in chunk
    assert '"seq":3' in chunk or '"seq": 3' in chunk


def test_settings_page_is_separate_and_requires_login():
    client, _ = make_client(ConfiguredFakeCredentialsStore())
    assert client.get("/settings").status_code == 302
    login(client)
    page = client.get("/settings")
    content = page.get_data(as_text=True)
    assert page.status_code == 200
    assert 'id="settings-page-title"' in content
    assert "OCI API credentials" in content
    assert "Change admin password" in content
    assert "ARM" in content
    assert "ap-tokyo-1" in content
    assert "/static/settings.js" in content
    assert 'class="mobile-menu"' in content
    assert 'id="settings-dialog"' not in client.get("/").get_data(as_text=True)


def test_dashboard_shows_existing_credentials_as_editable():
    client, _ = make_client(ConfiguredFakeCredentialsStore())
    login(client)
    page = client.get("/").get_data(as_text=True)

    assert "Replace OCI credentials" in page
    assert 'name="oci_profile"' not in page
    assert "cannot be displayed or edited alone" in page


def test_wrong_password_is_rejected():
    client, _ = make_client()
    response = login(client, "wrong")
    assert "Incorrect password" in response.get_data(as_text=True)


def test_login_uses_chinese_when_accept_language_is_zh():
    client, _ = make_client()
    with client.session_transaction() as session:
        session["csrf_token"] = "token"
    response = client.post(
        "/login",
        data={"password": "wrong", "csrf_token": "token"},
        headers={"Accept-Language": "zh-CN,zh;q=0.9"},
    )
    body = response.get_data(as_text=True)
    assert "密码错误" in body
    assert 'lang="zh-CN"' in body
    # First visit locks browser language into cookie so later Accept-Language changes are ignored.
    assert any("lang=zh" in value for value in response.headers.getlist("Set-Cookie"))


def test_lang_query_overrides_accept_language():
    client, _ = make_client()
    response = client.get("/login?lang=zh", headers={"Accept-Language": "en-US"})
    body = response.get_data(as_text=True)
    assert "进入抢注控制台" in body
    assert any("lang=zh" in value for value in response.headers.getlist("Set-Cookie"))


def test_cookie_language_overrides_accept_language():
    client, _ = make_client()
    client.set_cookie("lang", "zh")
    response = client.get("/login", headers={"Accept-Language": "en-US,en;q=0.9"})
    body = response.get_data(as_text=True)
    assert "进入抢注控制台" in body
    assert 'lang="zh-CN"' in body


def test_manual_lang_switch_updates_cookie():
    client, _ = make_client()
    client.set_cookie("lang", "en")
    response = client.get("/login?lang=zh", headers={"Accept-Language": "en-US"})
    body = response.get_data(as_text=True)
    assert "进入抢注控制台" in body
    assert any("lang=zh" in value for value in response.headers.getlist("Set-Cookie"))
    # Cookie preference sticks even if browser language is English.
    follow = client.get("/login", headers={"Accept-Language": "en-US"})
    assert "进入抢注控制台" in follow.get_data(as_text=True)


def test_locale_endpoint_switches_and_persists():
    client, _ = make_client()
    # Browser is Chinese; first paint would be zh, but user forces English via /locale.
    response = client.get(
        "/locale?lang=en&next=/login",
        headers={"Accept-Language": "zh-CN,zh;q=0.9"},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}
    assert response.headers["Location"].endswith("/login")
    assert any("lang=en" in value for value in response.headers.getlist("Set-Cookie"))

    page = client.get("/login", headers={"Accept-Language": "zh-CN,zh;q=0.9"})
    body = page.get_data(as_text=True)
    assert "Enter the provisioning console" in body
    assert "进入抢注控制台" not in body
    assert 'action="/locale"' in body or 'action="/locale?' in body or 'set_language' not in body
    assert 'name="lang"' in body


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
    assert "notification test" in sent[0][1].lower() or "A1 Control" in sent[0][1]


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
    assert "Webhook URL is required" in response.get_json()["error"]


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
    assert "Incorrect password" in login(client, "test-password").get_data(as_text=True)
    assert login(client, "new-password").status_code == 302
