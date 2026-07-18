from oracle_arm_console.security import PasswordStore


def test_password_hash_is_persisted(tmp_path):
    path = tmp_path / "security.json"
    store = PasswordStore(path, "admin")
    store.update("new-password")

    content = path.read_text(encoding="utf-8")
    assert "new-password" not in content
    assert PasswordStore(path, "admin").verify("new-password")
