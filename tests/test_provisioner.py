from types import SimpleNamespace

import oci

from oracle_arm_console.instance import InstanceSpec
from oracle_arm_console.provisioner import Provisioner
from oracle_arm_console.settings import TaskSettings


def _spec():
    return InstanceSpec(
        compartment_id="ocid1.tenancy.test",
        memory_in_gbs=12,
        ocpus=2,
        availability_domain="AD-1",
        subnet_id="ocid1.subnet.test",
        display_name="arm-server",
        image_id="ocid1.image.test",
        ssh_authorized_keys="ssh-ed25519 AAAA test@example",
    )


def test_run_retries_transport_failure(monkeypatch):
    provisioner = Provisioner.__new__(Provisioner)
    provisioner.spec = _spec()
    provisioner.settings = TaskSettings(retry_interval=10)
    logs = []
    provisioner.emit = logs.append

    failure = oci.exceptions.RequestException("proxy disconnected")
    calls = []

    class Compute:
        def launch_instance(self, details):
            calls.append(details)
            if len(calls) == 1:
                raise failure
            return SimpleNamespace(data=SimpleNamespace(id="instance-id"))

    provisioner.compute = Compute()
    provisioner._wait_for_public_ip = lambda instance_id: "203.0.113.10"
    monkeypatch.setattr("oracle_arm_console.provisioner.time.sleep", lambda seconds: None)
    monkeypatch.setattr("oracle_arm_console.provisioner.send_notifications", lambda *args: None)

    provisioner.run()

    assert len(calls) == 2
    assert any("OCI 网络请求失败" in message for message in logs)
    assert any("实例创建成功" in message for message in logs)
