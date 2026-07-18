import pytest

from oracle_arm_console.instance import InstanceSpec


VALID_FORM = {
    "compartment_id": "ocid1.tenancy.test",
    "availability_domain": "NAOy:AP-TOKYO-1-AD-1",
    "subnet_id": "ocid1.subnet.test",
    "image_id": "ocid1.image.test",
    "display_name": "arm-server",
    "ocpus": "2",
    "memory_in_gbs": "12",
    "boot_volume_size_in_gbs": "50",
    "ssh_authorized_keys": "ssh-ed25519 AAAA test@example",
}


def test_instance_spec_from_form():
    spec = InstanceSpec.from_form(VALID_FORM)
    assert spec.display_name == "arm-server"
    assert spec.ocpus == 2
    assert spec.memory_in_gbs == 12
    assert spec.boot_volume_size_in_gbs == 50


def test_instance_spec_rejects_paid_size():
    with pytest.raises(ValueError, match="OCPU"):
        InstanceSpec.from_form({**VALID_FORM, "ocpus": "4"})


def test_instance_spec_rejects_api_private_key():
    with pytest.raises(ValueError, match="SSH 公钥"):
        InstanceSpec.from_form({**VALID_FORM, "ssh_authorized_keys": "-----BEGIN PRIVATE KEY-----"})
