const logUi = {
  statusText: document.querySelector("#status-text"),
  statusDot: document.querySelector("#status-dot"),
  startedAt: document.querySelector("#started-at"),
  exitCode: document.querySelector("#exit-code"),
  logs: document.querySelector("#logs"),
  logCount: document.querySelector("#log-count"),
  refreshedAt: document.querySelector("#refreshed-at"),
  follow: document.querySelector("#follow-logs"),
  copy: document.querySelector("#copy-button"),
  toast: document.querySelector("#toast"),
};

let toastTimer;

function formatTime(value) {
  return value ? new Date(value).toLocaleString() : "—";
}

function notify(message) {
  logUi.toast.textContent = message;
  logUi.toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => logUi.toast.classList.remove("visible"), 2400);
}

async function refreshLogs() {
  try {
    const response = await fetch("/api/status", {headers: {Accept: "application/json"}});
    if (!response.ok) throw new Error("status request failed");
    const data = await response.json();
    const entries = Array.isArray(data.logs) ? data.logs : [];
    const wasNearBottom = logUi.logs.scrollHeight - logUi.logs.scrollTop - logUi.logs.clientHeight < 64;

    logUi.statusText.textContent = data.running ? "抢注进行中" : data.state === "idle" ? "等待启动" : "任务已结束";
    logUi.statusDot.classList.toggle("running", data.running);
    document.body.classList.toggle("task-running", data.running);
    logUi.startedAt.textContent = formatTime(data.started_at);
    logUi.exitCode.textContent = data.exit_code === null ? "—" : String(data.exit_code);
    logUi.logs.textContent = entries.length ? entries.join("\n") : "等待任务启动";
    logUi.logCount.textContent = `${entries.length} 条记录`;
    logUi.refreshedAt.textContent = `更新于 ${new Date().toLocaleTimeString()}`;

    if (logUi.follow.checked || wasNearBottom) logUi.logs.scrollTop = logUi.logs.scrollHeight;
  } catch (_) {
    logUi.statusText.textContent = "连接已中断";
    logUi.statusDot.classList.remove("running");
    logUi.refreshedAt.textContent = "刷新失败";
  }
}

logUi.copy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(logUi.logs.textContent);
    notify("运行日志已复制");
  } catch (_) {
    notify("复制失败，请手动选择日志");
  }
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refreshLogs();
});

refreshLogs();
setInterval(refreshLogs, 2000);
