import configparser
import hashlib
import os
from pathlib import Path

import oci
from cryptography.hazmat.primitives import serialization


REQUIRED_FIELDS = ("user", "fingerprint", "tenancy", "region")


class OciCredentialsStore:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)

    @property
    def config_file(self):
        return str((self.data_dir / "config").resolve())

    def status(self):
        config_path = Path(self.config_file)
        key_path = (self.data_dir / "oci_api_key.pem").resolve()
        if not config_path.is_file() or not key_path.is_file():
            return {"configured": False, "profile": "DEFAULT", "region": ""}

        parser = configparser.RawConfigParser()
        try:
            parser.read(config_path, encoding="utf-8")
            if parser.defaults():
                profile = parser.default_section
                values = parser.defaults()
            else:
                profile = parser.sections()[0]
                values = parser[profile]
            return {
                "configured": True,
                "profile": profile,
                "region": values.get("region", ""),
            }
        except (configparser.Error, IndexError, OSError):
            return {"configured": False, "profile": "DEFAULT", "region": ""}

    def save(self, config_text, private_key_bytes):
        profile, values = self._parse_config(config_text)
        private_key = self._load_private_key(private_key_bytes)
        actual_fingerprint = self._fingerprint(private_key)
        expected_fingerprint = values["fingerprint"].strip().lower()
        if actual_fingerprint != expected_fingerprint:
            raise ValueError("PEM 私钥与 OCI 配置中的 fingerprint 不匹配")

        self.data_dir.mkdir(parents=True, exist_ok=True)
        key_path = (self.data_dir / "oci_api_key.pem").resolve()
        config_path = Path(self.config_file)
        self._atomic_write(key_path, private_key_bytes.strip() + b"\n")

        lines = ["[{}]".format(profile)]
        for field in REQUIRED_FIELDS:
            lines.append("{}={}".format(field, values[field].strip()))
        lines.append("key_file={}".format(key_path))
        self._atomic_write(config_path, ("\n".join(lines) + "\n").encode("utf-8"))

        config = oci.config.from_file(str(config_path), profile)
        oci.config.validate_config(config)
        return {"config_file": str(config_path), "profile": profile, "region": config["region"]}

    @staticmethod
    def _parse_config(content):
        parser = configparser.RawConfigParser(inline_comment_prefixes=("#", ";"))
        try:
            parser.read_string(content)
        except configparser.Error as exc:
            raise ValueError("配置片段格式无效，请粘贴包含 [DEFAULT] 或 [Profile 名称] 的多行内容") from exc

        profiles = []
        if parser.defaults():
            profiles.append(parser.default_section)
        profiles.extend(parser.sections())
        if len(profiles) != 1:
            raise ValueError("配置片段必须且只能包含一个 Profile")

        profile = profiles[0]
        values = parser.defaults() if profile == parser.default_section else parser[profile]
        missing = [field for field in REQUIRED_FIELDS if not values.get(field, "").strip()]
        if missing:
            raise ValueError("OCI 配置缺少字段：{}".format(", ".join(missing)))
        return profile, values

    @staticmethod
    def _load_private_key(content):
        if not content or len(content) > 128 * 1024:
            raise ValueError("请选择有效的 PEM 私钥文件")
        try:
            return serialization.load_pem_private_key(content, password=None)
        except (TypeError, ValueError) as exc:
            raise ValueError("无法读取 PEM 私钥，请使用创建 OCI API Key 时下载的未加密私钥") from exc

    @staticmethod
    def _fingerprint(private_key):
        public_der = private_key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        digest = hashlib.md5(public_der, usedforsecurity=False).hexdigest()
        return ":".join(digest[index:index + 2] for index in range(0, len(digest), 2))

    @staticmethod
    def _atomic_write(path, content):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(content)
        if os.name != "nt":
            temporary.chmod(0o600)
        temporary.replace(path)
