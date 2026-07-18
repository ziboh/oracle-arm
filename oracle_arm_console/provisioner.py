import base64
import os
import secrets
import string
import time

import oci
from .settings import TaskSettings
from .instance import InstanceSpec
from .notifications import send_notifications


class Provisioner:
    shape = "VM.Standard.A1.Flex"

    def __init__(self, spec: InstanceSpec, settings: TaskSettings, emit=print):
        self.spec = spec
        self.settings = settings
        self.emit = emit
        config_path = os.path.expanduser(settings.oci_config_file)
        self.config = oci.config.from_file(config_path, settings.oci_profile)
        oci.config.validate_config(self.config)
        self.compute = oci.core.ComputeClient(self.config)

    def run(self):
        password = self._password()
        interval = self.settings.retry_interval
        attempts = 0
        self.emit(
            "目标：{} / {} OCPU / {} GB 内存 / {} GB 启动盘".format(
                self.spec.display_name,
                self.spec.ocpus,
                self.spec.memory_in_gbs,
                self.spec.boot_volume_size_in_gbs,
            )
        )
        while True:
            attempts += 1
            try:
                instance = self.compute.launch_instance(self._launch_details(password)).data
            except oci.exceptions.RequestException as exc:
                interval = min(interval + 10, 60)
                self.emit(
                    "OCI 网络请求失败（{}），{} 秒后重试".format(
                        type(exc).__name__, interval
                    )
                )
                time.sleep(interval)
                continue
            except oci.exceptions.ServiceError as exc:
                if self._out_of_capacity(exc):
                    self.emit("第 {} 次请求：暂无可用容量，{} 秒后重试".format(attempts, interval))
                    time.sleep(interval)
                    continue
                if exc.status == 429:
                    interval = min(interval + 10, 60)
                    self.emit("请求受到限速，重试间隔调整为 {} 秒".format(interval))
                    time.sleep(interval)
                    continue
                raise

            public_ip = self._wait_for_public_ip(instance.id)
            result = (
                "实例创建成功\n名称：{}\n公网 IP：{}\nroot 密码：{}\n尝试次数：{}".format(
                    self.spec.display_name, public_ip or "尚未分配", password, attempts
                )
            )
            self.emit(result)
            send_notifications(self.settings, result, self.emit)
            return

    def _launch_details(self, password):
        user_data = base64.b64encode(self._cloud_init(password).encode()).decode()
        return oci.core.models.LaunchInstanceDetails(
            display_name=self.spec.display_name,
            compartment_id=self.spec.compartment_id,
            shape=self.shape,
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=self.spec.ocpus, memory_in_gbs=self.spec.memory_in_gbs
            ),
            availability_domain=self.spec.availability_domain,
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=self.spec.subnet_id, hostname_label=self.spec.display_name
            ),
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                image_id=self.spec.image_id,
                boot_volume_size_in_gbs=self.spec.boot_volume_size_in_gbs,
            ),
            metadata={"ssh_authorized_keys": self.spec.ssh_authorized_keys, "user_data": user_data},
            is_pv_encryption_in_transit_enabled=True,
        )

    def _wait_for_public_ip(self, instance_id):
        network = oci.core.VirtualNetworkClient(self.config)
        for _ in range(100):
            attachments = self.compute.list_vnic_attachments(
                compartment_id=self.spec.compartment_id, instance_id=instance_id
            ).data
            if attachments:
                public_ip = network.get_vnic(attachments[0].vnic_id).data.public_ip
                if public_ip:
                    return public_ip
            time.sleep(5)
        return None

    @staticmethod
    def _out_of_capacity(exc):
        return exc.status == 500 and exc.code == "InternalError" and "host capacity" in exc.message.lower()

    @staticmethod
    def _password():
        alphabet = string.ascii_letters + string.digits + "#@"
        return "".join(secrets.choice(alphabet) for _ in range(16))

    @staticmethod
    def _cloud_init(password):
        return r"""#!/bin/bash
echo 'root:{password}' | chpasswd
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart ssh || systemctl restart sshd
""".format(password=password)
