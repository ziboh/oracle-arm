import hashlib

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from oracle_arm_console.oci_credentials import OciCredentialsStore


def make_credentials():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_der = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    digest = hashlib.md5(public_der, usedforsecurity=False).hexdigest()
    fingerprint = ":".join(digest[index:index + 2] for index in range(0, len(digest), 2))
    config = """[DEFAULT]
user=ocid1.user.oc1..test
fingerprint={}
tenancy=ocid1.tenancy.oc1..test
region=ap-tokyo-1
key_file=<path to your private keyfile> # TODO
""".format(fingerprint)
    return config, pem


def test_save_oci_credentials(tmp_path):
    config, pem = make_credentials()
    result = OciCredentialsStore(tmp_path).save(config, pem)

    assert result["profile"] == "DEFAULT"
    assert (tmp_path / "oci_api_key.pem").read_bytes().startswith(b"-----BEGIN PRIVATE KEY-----")
    saved_config = (tmp_path / "config").read_text(encoding="utf-8")
    assert "key_file={}".format((tmp_path / "oci_api_key.pem").resolve()) in saved_config
    assert OciCredentialsStore(tmp_path).status() == {
        "configured": True,
        "profile": "DEFAULT",
        "region": "ap-tokyo-1",
    }


def test_existing_credentials_are_replaced(tmp_path):
    first_config, first_pem = make_credentials()
    second_config, second_pem = make_credentials()
    store = OciCredentialsStore(tmp_path)

    store.save(first_config, first_pem)
    store.save(second_config, second_pem)

    assert (tmp_path / "oci_api_key.pem").read_bytes() == second_pem


def test_profile_is_inferred_from_config(tmp_path):
    config, pem = make_credentials()
    config = config.replace("[DEFAULT]", "[ARM]")

    result = OciCredentialsStore(tmp_path).save(config, pem)

    assert result["profile"] == "ARM"


def test_rejects_multiple_profiles(tmp_path):
    config, pem = make_credentials()
    config += "\n[ARM]\nregion=ap-tokyo-1\n"

    with pytest.raises(ValueError, match="exactly one profile"):
        OciCredentialsStore(tmp_path).save(config, pem)


def test_rejects_mismatched_private_key(tmp_path):
    config, _ = make_credentials()
    _, other_pem = make_credentials()
    with pytest.raises(ValueError, match="fingerprint"):
        OciCredentialsStore(tmp_path).save(config, other_pem)
