import json
import os
import subprocess
import sys
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

class JobManager:
    def __init__(self, data_dir=None, max_log_lines=3000):
        self.data_dir = Path(data_dir or Path.cwd() / "data")
        self.logs = deque(maxlen=max_log_lines)
        self.process = None
        self.started_at = None
        self.finished_at = None
        self.exit_code = None
        self._lock = threading.RLock()

    def status(self):
        with self._lock:
            running = self.process is not None and self.process.poll() is None
            state = "running" if running else ("idle" if self.started_at is None else "finished")
            return {
                "running": running,
                "state": state,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "exit_code": self.exit_code,
                "logs": list(self.logs),
            }

    def start(self, spec, settings):
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                raise RuntimeError("已有任务正在运行")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            instance_path = self.data_dir / "instance.json"
            instance_path.write_text(
                json.dumps(spec.as_dict(), ensure_ascii=True, indent=2), encoding="utf-8"
            )
            env = os.environ.copy()
            env.update(settings.as_environment())
            self.logs.clear()
            self.logs.append(self._line("任务已进入队列"))
            self.started_at = self._now()
            self.finished_at = None
            self.exit_code = None
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
                raise RuntimeError("当前没有运行中的任务")
            self.logs.append(self._line("正在停止任务"))
            self.process.terminate()

    def _collect(self, process):
        assert process.stdout is not None
        for line in process.stdout:
            with self._lock:
                self.logs.append(self._line(line.rstrip()))
        exit_code = process.wait()
        with self._lock:
            self.exit_code = exit_code
            self.finished_at = self._now()
            self.logs.append(self._line("任务结束，退出码 {}".format(exit_code)))

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _line(message):
        return "{}  {}".format(datetime.now().strftime("%H:%M:%S"), message)
