import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .i18n import t


BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


class JobManager:
    def __init__(self, data_dir=None, max_log_lines=3000):
        self.data_dir = Path(data_dir or Path.cwd() / "data")
        self.logs = deque(maxlen=max_log_lines)
        self.process = None
        self.started_at = None
        self.finished_at = None
        self.exit_code = None
        self._seq = 0
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)

    def status(self):
        with self._lock:
            return self._status_unlocked()

    def wait_for_update(self, last_seq: int, timeout: float = 1.0) -> dict:
        """Block until log/state seq advances or timeout, then return a snapshot."""
        deadline = time.monotonic() + max(0.0, timeout)
        with self._cond:
            while self._seq == last_seq:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._cond.wait(timeout=remaining)
            return self._status_unlocked()

    def start(self, spec, settings):
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                raise RuntimeError(t("errors.job_running"))
            self.data_dir.mkdir(parents=True, exist_ok=True)
            instance_path = self.data_dir / "instance.json"
            instance_path.write_text(
                json.dumps(spec.as_dict(), ensure_ascii=True, indent=2), encoding="utf-8"
            )
            env = os.environ.copy()
            env.update(settings.as_environment())
            self.logs.clear()
            self.started_at = self._now()
            self.finished_at = None
            self.exit_code = None
            self._append_unlocked(t("job.queued"))
            self.process = subprocess.Popen(
                [sys.executable, "-u", "-m", "oracle_arm_console.cli", str(instance_path)],
                cwd=str(Path.cwd()),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            threading.Thread(target=self._collect, args=(self.process,), daemon=True).start()

    def stop(self):
        with self._lock:
            if self.process is None or self.process.poll() is not None:
                raise RuntimeError(t("errors.job_not_running"))
            self._append_unlocked(t("job.stopping"))
            self.process.terminate()

    def _collect(self, process):
        assert process.stdout is not None
        for line in process.stdout:
            with self._lock:
                self._append_unlocked(line.rstrip())
        exit_code = process.wait()
        with self._lock:
            self.exit_code = exit_code
            self.finished_at = self._now()
            self._append_unlocked(t("job.finished", code=exit_code))

    def _append_unlocked(self, message):
        self.logs.append(self._line(message))
        self._seq += 1
        self._cond.notify_all()

    def _status_unlocked(self):
        running = self.process is not None and self.process.poll() is None
        state = "running" if running else ("idle" if self.started_at is None else "finished")
        return {
            "running": running,
            "state": state,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "exit_code": self.exit_code,
            "logs": list(self.logs),
            "seq": self._seq,
        }

    @staticmethod
    def _now():
        return datetime.now(BEIJING_TZ).isoformat()

    @staticmethod
    def _line(message):
        return "{}  {}".format(datetime.now(BEIJING_TZ).strftime("%H:%M:%S"), message)
