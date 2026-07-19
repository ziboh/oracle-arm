const i18n = window.I18N || {};
function t(key, vars) {
  let text = i18n[key] || key;
  if (vars) {
    Object.keys(vars).forEach((name) => {
      text = text.split(`{${name}}`).join(String(vars[name]));
    });
  }
  return text;
}
function localeTag() {
  return document.documentElement.lang || "en";
}

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
let statusEventSource = null;
let statusPollTimer = null;
let statusReconnectTimer = null;
let authenticationExpired = false;

const beijingTimeOptions = {timeZone: "Asia/Shanghai"};

function formatTime(value) {
  return value ? new Date(value).toLocaleString(localeTag(), beijingTimeOptions) : (t("dash") || "—");
}

function notify(message) {
  logUi.toast.textContent = message;
  logUi.toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => logUi.toast.classList.remove("visible"), 2400);
}

function redirectToLogin() {
  if (authenticationExpired) return;
  authenticationExpired = true;
  disconnectStatusStream();
  const next = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  window.location.replace(`/login?next=${encodeURIComponent(next)}`);
}

function applyStatus(data) {
  if (!data || typeof data !== "object") return;
  const entries = Array.isArray(data.logs) ? data.logs : [];
  const wasNearBottom = logUi.logs.scrollHeight - logUi.logs.scrollTop - logUi.logs.clientHeight < 64;

  logUi.statusText.textContent = data.running
    ? t("status_running")
    : data.state === "idle"
      ? t("status_idle")
      : t("status_finished");
  logUi.statusDot.classList.toggle("running", !!data.running);
  document.body.classList.toggle("task-running", !!data.running);
  logUi.startedAt.textContent = formatTime(data.started_at);
  logUi.exitCode.textContent =
    data.exit_code === null || data.exit_code === undefined ? "—" : String(data.exit_code);
  logUi.logs.textContent = entries.length ? entries.join("\n") : t("waiting_start");
  logUi.logCount.textContent = t("record_count", {count: entries.length});
  logUi.refreshedAt.textContent = t("updated_at", {
    time: new Date().toLocaleTimeString(localeTag(), beijingTimeOptions),
  });

  if (logUi.follow.checked || wasNearBottom) logUi.logs.scrollTop = logUi.logs.scrollHeight;
}

async function refreshLogs() {
  try {
    const response = await fetch("/api/status", {headers: {Accept: "application/json"}});
    if (response.status === 401) {
      redirectToLogin();
      return;
    }
    if (!response.ok) throw new Error("status request failed");
    applyStatus(await response.json());
  } catch (_) {
    logUi.statusText.textContent = t("status_disconnected");
    logUi.statusDot.classList.remove("running");
    logUi.refreshedAt.textContent = t("refresh_failed");
  }
}

function stopStatusPolling() {
  if (statusPollTimer) {
    clearInterval(statusPollTimer);
    statusPollTimer = null;
  }
}

function clearStatusReconnect() {
  if (statusReconnectTimer) {
    clearTimeout(statusReconnectTimer);
    statusReconnectTimer = null;
  }
}

function disconnectStatusStream() {
  clearStatusReconnect();
  stopStatusPolling();
  if (statusEventSource) {
    statusEventSource.onmessage = null;
    statusEventSource.onerror = null;
    statusEventSource.onopen = null;
    statusEventSource.close();
    statusEventSource = null;
  }
}

function startStatusPolling() {
  if (authenticationExpired) return;
  stopStatusPolling();
  refreshLogs();
  statusPollTimer = setInterval(refreshLogs, 2000);
}

function connectStatusStream() {
  if (authenticationExpired) return;
  disconnectStatusStream();
  if (typeof EventSource === "undefined") {
    startStatusPolling();
    return;
  }
  const source = new EventSource("/api/status/stream");
  statusEventSource = source;
  source.onmessage = (event) => {
    try {
      applyStatus(JSON.parse(event.data));
    } catch (_) {
      /* ignore malformed frames */
    }
  };
  source.onerror = () => {
    source.close();
    if (statusEventSource === source) statusEventSource = null;
    if (authenticationExpired) return;
    startStatusPolling();
    clearStatusReconnect();
    statusReconnectTimer = setTimeout(() => {
      stopStatusPolling();
      connectStatusStream();
    }, 5000);
  };
  source.onopen = () => {
    stopStatusPolling();
  };
}

logUi.copy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(logUi.logs.textContent);
    notify(t("logs_copied"));
  } catch (_) {
    notify(t("copy_failed"));
  }
});

document.addEventListener("visibilitychange", () => {
  if (document.hidden) return;
  if (!statusEventSource || statusEventSource.readyState === EventSource.CLOSED) {
    stopStatusPolling();
    connectStatusStream();
  } else {
    refreshLogs();
  }
});

// Close the long-lived SSE before navigation so Waitress workers are not held
// by abandoned streams when switching Console / Logs / Settings.
window.addEventListener("pagehide", disconnectStatusStream);
window.addEventListener("pageshow", (event) => {
  if (event.persisted) connectStatusStream();
});

connectStatusStream();
