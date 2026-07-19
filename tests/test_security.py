from oracle_arm_console.security import PasswordStore


def test_password_hash_is_persisted(tmp_path):
    path = tmp_path / "security.json"
    store = PasswordStore(path, "admin")
    store.update("new-password")

    content = path.read_text(encoding="utf-8")
    assert "new-password" not in content
    assert PasswordStore(path, "admin").verify("new-password")
    assert PasswordStore(path).session_secret


def test_new_store_is_uninitialized_without_an_explicit_password(tmp_path):
    path = tmp_path / "security.json"
    store = PasswordStore(path)

    assert store.is_initialized is False
    assert not store.verify("admin")
    assert len(store.session_secret) >= 32
