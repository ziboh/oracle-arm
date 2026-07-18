import re
from dataclasses import asdict, dataclass


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
            raise ValueError("请选择实例区间")
        if not availability_domain:
            raise ValueError("请选择可用域")
        if not subnet_id.startswith("ocid1.subnet."):
            raise ValueError("请选择公共子网")
        if not image_id.startswith("ocid1.image."):
            raise ValueError("请选择 ARM 系统镜像")
        if not HOSTNAME_PATTERN.fullmatch(display_name) or display_name.endswith("-"):
            raise ValueError("实例名称必须以字母开头，只能包含小写字母、数字和连字符")

        try:
            ocpus = float(form.get("ocpus", "2"))
            memory = float(form.get("memory_in_gbs", "12"))
            boot_volume = float(form.get("boot_volume_size_in_gbs", "50"))
        except ValueError as exc:
            raise ValueError("实例规格必须是数字") from exc
        if not 1 <= ocpus <= 2:
            raise ValueError("免费 A1 配置的 OCPU 必须在 1 到 2 之间")
        if not max(1, ocpus) <= memory <= 12:
            raise ValueError("免费 A1 配置的内存必须在 OCPU 数量到 12 GB 之间")
        if not 50 <= boot_volume <= 200:
            raise ValueError("启动盘必须在 50 到 200 GB 之间")

        keys = [line.strip() for line in ssh_keys.splitlines() if line.strip()]
        if not keys or any(not line.startswith(SSH_KEY_PREFIXES) for line in keys):
            raise ValueError("请填写有效的 SSH 公钥，不要填写 OCI API 私钥")

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
