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
    assert any("OCI network request failed" in message for message in logs)
    assert any("Instance created" in message for message in logs)


def test_run_caps_rate_limit_retry_interval_at_120_seconds(monkeypatch):
    provisioner = Provisioner.__new__(Provisioner)
    provisioner.spec = _spec()
    provisioner.settings = TaskSettings(retry_interval=110)
    logs = []
    provisioner.emit = logs.append

    calls = []

    class Compute:
        def launch_instance(self, details):
            calls.append(details)
            if len(calls) == 1:
                raise oci.exceptions.ServiceError(429, "TooManyRequests", {}, "rate limited")
            return SimpleNamespace(data=SimpleNamespace(id="instance-id"))

    provisioner.compute = Compute()
    provisioner._wait_for_public_ip = lambda instance_id: "203.0.113.10"
    monkeypatch.setattr("oracle_arm_console.provisioner.time.sleep", lambda seconds: None)
    monkeypatch.setattr("oracle_arm_console.provisioner.send_notifications", lambda *args: None)

    provisioner.run()

    assert len(calls) == 2
    assert any("retry interval set to 120" in message for message in logs)


def test_run_uses_user_retry_interval_as_larger_maximum(monkeypatch):
    provisioner = Provisioner.__new__(Provisioner)
    provisioner.spec = _spec()
    provisioner.settings = TaskSettings(retry_interval=150)
    logs = []
    provisioner.emit = logs.append

    calls = []

    class Compute:
        def launch_instance(self, details):
            calls.append(details)
            if len(calls) == 1:
                raise oci.exceptions.ServiceError(429, "TooManyRequests", {}, "rate limited")
            return SimpleNamespace(data=SimpleNamespace(id="instance-id"))

    provisioner.compute = Compute()
    provisioner._wait_for_public_ip = lambda instance_id: "203.0.113.10"
    monkeypatch.setattr("oracle_arm_console.provisioner.time.sleep", lambda seconds: None)
    monkeypatch.setattr("oracle_arm_console.provisioner.send_notifications", lambda *args: None)

    provisioner.run()

    assert len(calls) == 2
    assert any("retry interval set to 150" in message for message in logs)

