import base64
import hashlib
import os
import re
import secrets
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


KEY_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{24}")


class SshKeyStore:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir).resolve()

    def generate(self):
        private_key = Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.OpenSSH,
            serialization.NoEncryption(),
        )
        public_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.OpenSSH,
            serialization.PublicFormat.OpenSSH,
        )
        public_key = public_bytes.decode("ascii") + " oracle-arm-console"
        public_blob = base64.b64decode(public_bytes.split()[1])
        fingerprint = "SHA256:" + base64.b64encode(
            hashlib.sha256(public_blob).digest()
        ).decode("ascii").rstrip("=")

        key_id = secrets.token_urlsafe(18)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(key_id)
        path.write_bytes(private_bytes)
        if os.name != "nt":
            path.chmod(0o600)
        return {"id": key_id, "public_key": public_key, "fingerprint": fingerprint}

    def path_for(self, key_id):
        if not KEY_ID_PATTERN.fullmatch(key_id):
            raise ValueError("SSH 密钥编号无效")
        path = self._path(key_id)
        if not path.is_file():
            raise FileNotFoundError("SSH 私钥不存在")
        return path

    def _path(self, key_id):
        return self.data_dir / "{}.key".format(key_id)
