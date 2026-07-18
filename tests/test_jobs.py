import threading
import time
from datetime import datetime

from oracle_arm_console.jobs import JobManager


def test_job_timestamps_use_beijing_time():
    timestamp = datetime.fromisoformat(JobManager._now())

    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset().total_seconds() == 8 * 60 * 60


def test_log_lines_use_beijing_clock_format():
    line = JobManager._line("测试日志")

    assert line.endswith("  测试日志")
    assert len(line.split("  ", 1)[0]) == 8


def test_wait_for_update_wakes_when_log_appended():
    manager = JobManager()
    with manager._lock:
        before = manager._seq
        manager._append_unlocked("line-a")
        first = manager._status_unlocked()
    assert first["seq"] == before + 1
    assert any("line-a" in item for item in first["logs"])

    result = {}

    def waiter():
        result["snapshot"] = manager.wait_for_update(first["seq"], timeout=2.0)

    thread = threading.Thread(target=waiter)
    thread.start()
    time.sleep(0.05)
    with manager._lock:
        manager._append_unlocked("line-b")
    thread.join(timeout=2.0)
    assert not thread.is_alive()
    assert any("line-b" in item for item in result["snapshot"]["logs"])
    assert result["snapshot"]["seq"] == first["seq"] + 1
