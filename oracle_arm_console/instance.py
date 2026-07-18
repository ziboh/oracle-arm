import re
from dataclasses import asdict, dataclass

from .i18n import t


HOSTNAME_PATTERN = re.compile(r"[a-z][a-z0-9-]{0,62}")
SSH_KEY_PREFIXES = ("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")


@dataclass(frozen=True)
class InstanceSpec:
    compartment_id: str
    memory_in_gbs: float
    ocpus: float
    availability_domain: str
    subnet_id: str
    display_name: str
    image_id: str
    ssh_authorized_keys: str
    boot_volume_size_in_gbs: float = 50.0

    @classmethod
    def from_form(cls, form):
        compartment_id = form.get("compartment_id", "").strip()
        availability_domain = form.get("availability_domain", "").strip()
        subnet_id = form.get("subnet_id", "").strip()
        image_id = form.get("image_id", "").strip()
        display_name = form.get("display_name", "arm-server").strip().lower()
        ssh_keys = form.get("ssh_authorized_keys", "").strip()

        if not compartment_id.startswith(("ocid1.compartment.", "ocid1.tenancy.")):
            raise ValueError(t("errors.need_compartment"))
        if not availability_domain:
            raise ValueError(t("errors.need_ad"))
        if not subnet_id.startswith("ocid1.subnet."):
            raise ValueError(t("errors.need_subnet"))
        if not image_id.startswith("ocid1.image."):
            raise ValueError(t("errors.need_image"))
        if not HOSTNAME_PATTERN.fullmatch(display_name) or display_name.endswith("-"):
            raise ValueError(t("errors.display_name_invalid"))

        try:
            ocpus = float(form.get("ocpus", "2"))
            memory = float(form.get("memory_in_gbs", "12"))
            boot_volume = float(form.get("boot_volume_size_in_gbs", "50"))
        except ValueError as exc:
            raise ValueError(t("errors.spec_not_number")) from exc
        if not 1 <= ocpus <= 2:
            raise ValueError(t("errors.ocpu_range"))
        if not max(1, ocpus) <= memory <= 12:
            raise ValueError(t("errors.memory_range"))
        if not 50 <= boot_volume <= 200:
            raise ValueError(t("errors.boot_range"))

        keys = [line.strip() for line in ssh_keys.splitlines() if line.strip()]
        if not keys or any(not line.startswith(SSH_KEY_PREFIXES) for line in keys):
            raise ValueError(t("errors.ssh_public_required"))

        return cls(
            compartment_id=compartment_id,
            memory_in_gbs=memory,
            ocpus=ocpus,
            availability_domain=availability_domain,
            subnet_id=subnet_id,
            display_name=display_name,
            image_id=image_id,
            ssh_authorized_keys="\n".join(keys),
            boot_volume_size_in_gbs=boot_volume,
        )

    @classmethod
    def from_dict(cls, values):
        return cls(**values)

    def as_dict(self):
        return asdict(self)
