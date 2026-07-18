from cryptography.hazmat.primitives import serialization

from oracle_arm_console.ssh_keys import SshKeyStore


def test_generates_ed25519_key_pair(tmp_path):
    store = SshKeyStore(tmp_path)
    result = store.generate()

    assert result["public_key"].startswith("ssh-ed25519 ")
    assert result["fingerprint"].startswith("SHA256:")
    path = store.path_for(result["id"])
    private_key = serialization.load_ssh_private_key(path.read_bytes(), password=None)
    assert private_key is not None
