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

const ui = {
  statusText: document.querySelector("#status-text"),
  statusDot: document.querySelector("#status-dot"),
  startedAt: document.querySelector("#started-at"),
  exitCode: document.querySelector("#exit-code"),
  logs: document.querySelector("#logs"),
  startForm: document.querySelector("#start-form"),
  stopForm: document.querySelector("#stop-form"),
  startButton: document.querySelector("#start-button"),
  stopButton: document.querySelector("#stop-button"),
  loadResources: document.querySelector("#load-resources"),
  resourceStatus: document.querySelector("#resource-status"),
  instanceFields: document.querySelector("#instance-fields"),
  compartment: document.querySelector("#compartment-id"),
  availabilityDomain: document.querySelector("#availability-domain"),
  subnet: document.querySelector("#subnet-id"),
  imageFamily: document.querySelector("#image-family"),
  image: document.querySelector("#image-id"),
  sshKeys: document.querySelector("#ssh-authorized-keys"),
  sshPublicKeyHint: document.querySelector("#ssh-public-key-hint"),
  sshKeyStatus: document.querySelector("#ssh-key-status"),
  regenerateSshKey: document.querySelector("#regenerate-ssh-key"),
  downloadSshKey: document.querySelector("#download-ssh-key"),
  generatedKeyPanel: document.querySelector("#generated-key-panel"),
  uploadKeyPanel: document.querySelector("#upload-key-panel"),
  publicKeyFile: document.querySelector("#ssh-public-key-file"),
  uploadedKeyStatus: document.querySelector("#uploaded-key-status"),
  bootVolumeRange: document.querySelector("#boot-volume-range"),
  bootVolumeSize: document.querySelector("#boot-volume-size"),
  bootVolumeOutput: document.querySelector("#boot-volume-output"),
  bootVolumeHint: document.querySelector("#boot-volume-hint"),
  storageMeter: document.querySelector("#storage-meter"),
  storageAvailable: document.querySelector("#storage-available"),
  storageUsedBar: document.querySelector("#storage-used-bar"),
  storageDetail: document.querySelector("#storage-detail"),
  toast: document.querySelector("#toast"),
  configureOci: document.querySelector("#configure-oci"),
  ociDialog: document.querySelector("#oci-dialog"),
  ociCredentialsForm: document.querySelector("#oci-credentials-form"),
  ociConfigError: document.querySelector("#oci-config-error"),
  ociDialogTitle: document.querySelector("#oci-dialog-title"),
  ociCredentialWarning: document.querySelector("#oci-credential-warning"),
};

let toastTimer;
let loadedImages = [];
let generatedKeyId = null;
let privateKeyDownloaded = false;
let generatedPublicKey = "";
let uploadedPublicKey = "";
let sshKeyMode = "generate";
const resourceCacheKey = "a1-control-oci-resources";
const resourceCacheMaxAge = 24 * 60 * 60 * 1000;

function normalizePublicKey(value) {
  return value.trim().split(/\r?\n/).map((line) => line.trim()).filter(Boolean).join("\n");
}

function isValidPublicKey(value) {
  const key = normalizePublicKey(value);
  return Boolean(key) && key.split("\n").every((line) =>
    line.startsWith("ssh-ed25519 ") || line.startsWith("ssh-rsa ") || line.startsWith("ecdsa-sha2-"),
  );
}

function setUploadKeyStatus(message, valid = false) {
  ui.uploadedKeyStatus.textContent = message;
  ui.uploadedKeyStatus.classList.toggle("is-ready", valid);
}

const configTabs = [...document.querySelectorAll("[data-tab]")];
const configPanels = [...document.querySelectorAll("[data-panel]")];

function activateConfigTab(name, focus = false) {
  configTabs.forEach((tab) => {
    const active = tab.dataset.tab === name;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
    if (active && focus) tab.focus();
  });
  configPanels.forEach((panel) => {
    const active = panel.dataset.panel === name;
    panel.hidden = !active;
    panel.classList.toggle("is-active", active);
  });
}

configTabs.forEach((tab, index) => {
  tab.addEventListener("click", () => activateConfigTab(tab.dataset.tab));
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    let nextIndex = index;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + configTabs.length) % configTabs.length;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % configTabs.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = configTabs.length - 1;
    activateConfigTab(configTabs[nextIndex].dataset.tab, true);
  });
});

ui.startForm.addEventListener("invalid", (event) => {
  const panel = event.target.closest("[data-panel]");
  if (panel) activateConfigTab(panel.dataset.panel);
}, true);

function notify(message) {
  ui.toast.textContent = message;
  ui.toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ui.toast.classList.remove("visible"), 2600);
}

function formatTime(value) {
  return value ? new Date(value).toLocaleString(localeTag(), {timeZone: "Asia/Shanghai"}) : t("dash") || "—";
}

function sshKeyReady() {
  return sshKeyMode === "generate" ? privateKeyDownloaded : Boolean(uploadedPublicKey);
}

function syncManualPublicKey() {
  uploadedPublicKey = normalizePublicKey(ui.sshKeys.value);
  const valid = isValidPublicKey(uploadedPublicKey);
  if (uploadedPublicKey && !valid) {
    setUploadKeyStatus(t("invalid_pubkey"), false);
  } else if (valid) {
    setUploadKeyStatus(t("pubkey_ready"), true);
  } else {
    setUploadKeyStatus(t("pubkey_paste"));
  }
  updateStartAvailability();
}

function updateStartAvailability(running = false) {
  ui.startButton.disabled = running || ui.instanceFields.disabled || !sshKeyReady();
}

function applyStatus(data) {
  if (!data || typeof data !== "object") return;
  ui.statusText.textContent = data.running ? t("status_running") : data.state === "idle" ? t("status_idle") : t("status_finished");
  ui.statusDot.classList.toggle("running", !!data.running);
  document.body.classList.toggle("task-running", !!data.running);
  ui.startedAt.textContent = formatTime(data.started_at);
  ui.exitCode.textContent = data.exit_code === null || data.exit_code === undefined ? "—" : String(data.exit_code);
  updateStartAvailability(!!data.running);
  ui.loadResources.disabled = !!data.running;
  ui.instanceFields.disabled = !!data.running || !ui.instanceFields.dataset.ready;
  ui.stopButton.disabled = !data.running;
  const entries = Array.isArray(data.logs) ? data.logs : [];
  const stickToBottom = ui.logs.scrollHeight - ui.logs.scrollTop - ui.logs.clientHeight < 48;
  ui.logs.textContent = entries.length ? entries.join("\n") : t("waiting_start");
  if (stickToBottom) ui.logs.scrollTop = ui.logs.scrollHeight;
}

async function refreshStatus() {
  try {
    const response = await fetch("/api/status", {headers: {Accept: "application/json"}});
    if (!response.ok) return;
    applyStatus(await response.json());
  } catch (_) {
    ui.statusText.textContent = t("status_disconnected");
    ui.statusDot.classList.remove("running");
  }
}

let statusEventSource = null;
let statusPollTimer = null;
let statusReconnectTimer = null;

function stopStatusPolling() {
  if (statusPollTimer) {
    clearInterval(statusPollTimer);
    statusPollTimer = null;
  }
}

function startStatusPolling() {
  stopStatusPolling();
  refreshStatus();
  statusPollTimer = setInterval(refreshStatus, 2000);
}

function connectStatusStream() {
  if (statusEventSource) {
    statusEventSource.close();
    statusEventSource = null;
  }
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
    startStatusPolling();
    if (statusReconnectTimer) clearTimeout(statusReconnectTimer);
    statusReconnectTimer = setTimeout(() => {
      stopStatusPolling();
      connectStatusStream();
    }, 5000);
  };
  source.onopen = () => {
    stopStatusPolling();
  };
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden) return;
  if (!statusEventSource || statusEventSource.readyState === EventSource.CLOSED) {
    stopStatusPolling();
    connectStatusStream();
  }
});

function setOptions(select, items, valueFor, labelFor, emptyLabel) {
  const placeholder = new Option(emptyLabel, "", true, true);
  placeholder.disabled = true;
  placeholder.hidden = true;
  select.replaceChildren(placeholder);
  items.forEach((item) => select.add(new Option(labelFor(item), valueFor(item))));
  if (window.SoftSelect) window.SoftSelect.refresh(select);
}

function refreshSoftSelect(select) {
  if (window.SoftSelect) window.SoftSelect.refresh(select);
}

function imageFamilyLabel(name) {
  return name === "Canonical Ubuntu" ? "Ubuntu" : name;
}

function populateImages(family) {
  const images = loadedImages.filter((item) => item.operating_system === family);
  setOptions(
    ui.image,
    images,
    (item) => item.id,
    (item) => `${item.version} · ${item.name}`,
    t("choose_image"),
  );
  const preferred = family === "Oracle Linux"
    ? images.findIndex((item) => String(item.version).startsWith("9"))
    : 0;
  ui.image.selectedIndex = images.length ? Math.max(preferred, 0) + 1 : 0;
  refreshSoftSelect(ui.image);
}

ui.imageFamily.addEventListener("change", () => populateImages(ui.imageFamily.value));

async function generateSshKey() {
  ui.regenerateSshKey.disabled = true;
  ui.downloadSshKey.hidden = true;
  ui.sshKeyStatus.textContent = t("generating_key");
  privateKeyDownloaded = false;
  ui.startButton.disabled = true;
  try {
    const form = new FormData();
    form.append("csrf_token", ui.startForm.elements.csrf_token.value);
    const response = await fetch("/api/ssh-keys", {method: "POST", body: form});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || t("generate_key_failed"));
    generatedKeyId = data.id;
    generatedPublicKey = data.public_key;
    if (sshKeyMode === "generate") ui.sshKeys.value = generatedPublicKey;
    ui.downloadSshKey.href = data.download_url;
    ui.downloadSshKey.hidden = false;
    ui.sshKeyStatus.textContent = t("download_fingerprint", {fingerprint: data.fingerprint});
  } catch (error) {
    generatedKeyId = null;
    ui.sshKeys.value = "";
    ui.sshKeyStatus.textContent = error.message;
    throw error;
  } finally {
    ui.regenerateSshKey.disabled = false;
  }
}

ui.regenerateSshKey.addEventListener("click", async () => {
  try {
    await generateSshKey();
  } catch (_) {
    notify(t("cannot_generate_key"));
  }
});

ui.downloadSshKey.addEventListener("click", () => {
  privateKeyDownloaded = true;
  ui.sshKeyStatus.textContent = t("key_download_requested");
  updateStartAvailability();
});

document.querySelectorAll('input[name="ssh_key_mode"]').forEach((input) => {
  input.addEventListener("change", async () => {
    sshKeyMode = input.value;
    ui.generatedKeyPanel.hidden = sshKeyMode !== "generate";
    ui.uploadKeyPanel.hidden = sshKeyMode !== "upload";
    ui.sshKeys.value = sshKeyMode === "generate" ? generatedPublicKey : uploadedPublicKey;
    ui.sshKeys.readOnly = sshKeyMode === "generate";
    ui.sshKeys.placeholder = sshKeyMode === "generate" ? t("ssh_ph_generate") : t("ssh_ph_upload");
    ui.sshPublicKeyHint.textContent = sshKeyMode === "generate" ? t("ssh_hint_generate") : t("ssh_hint_upload");
    if (sshKeyMode === "generate" && !generatedKeyId && ui.instanceFields.dataset.ready) {
      try {
        await generateSshKey();
      } catch (_) {
        notify(t("cannot_generate_key"));
      }
    }
    updateStartAvailability();
  });
});

ui.sshKeys.addEventListener("input", () => {
  if (sshKeyMode === "upload") syncManualPublicKey();
});

ui.publicKeyFile.addEventListener("change", async () => {
  const file = ui.publicKeyFile.files[0];
  if (!file) return;
  if (file.size > 64 * 1024) {
    setUploadKeyStatus(t("pubkey_too_large"), false);
    updateStartAvailability();
    return;
  }
  const content = normalizePublicKey(await file.text());
  if (!isValidPublicKey(content)) {
    setUploadKeyStatus(t("pubkey_file_invalid"), false);
    updateStartAvailability();
    return;
  }
  uploadedPublicKey = content;
  ui.sshKeys.value = uploadedPublicKey;
  setUploadKeyStatus(`${file.name} · 公钥已就绪`, true);
  updateStartAvailability();
});

function syncBootVolume(value, updateNumberInput = true) {
  const min = Number(ui.bootVolumeSize.min);
  const max = Number(ui.bootVolumeSize.max);
  const numeric = Number(value);
  const next = Math.min(max, Math.max(min, Number.isFinite(numeric) ? numeric : min));
  const selection = max === min ? 100 : ((next - min) / (max - min)) * 100;
  ui.bootVolumeRange.value = String(next);
  if (updateNumberInput) ui.bootVolumeSize.value = String(next);
  ui.bootVolumeOutput.textContent = `${next} GB`;
  ui.bootVolumeRange.style.setProperty("--selection", `${selection}%`);
}

function previewBootVolumeInput() {
  const raw = ui.bootVolumeSize.value;
  if (raw === "") return;
  const next = Number(raw);
  const min = Number(ui.bootVolumeSize.min);
  const max = Number(ui.bootVolumeSize.max);
  if (!Number.isFinite(next) || next < min || next > max) return;
  syncBootVolume(next, false);
}

ui.bootVolumeRange.addEventListener("input", () => syncBootVolume(ui.bootVolumeRange.value));
ui.bootVolumeRange.addEventListener("wheel", (event) => {
  event.preventDefault();
  const step = Number(ui.bootVolumeRange.step) || 1;
  const direction = event.deltaY > 0 || event.deltaX > 0 ? -1 : 1;
  syncBootVolume(Number(ui.bootVolumeRange.value) + direction * step);
}, {passive: false});
ui.bootVolumeSize.addEventListener("input", previewBootVolumeInput);
ui.bootVolumeSize.addEventListener("change", () => {
  if (ui.bootVolumeSize.value !== "") syncBootVolume(ui.bootVolumeSize.value);
});

function markResourcesStale() {
  clearResourceCache();
  delete ui.instanceFields.dataset.ready;
  ui.instanceFields.disabled = true;
  ui.startButton.disabled = true;
  ui.resourceStatus.textContent = t("config_changed");
  ui.resourceStatus.className = "resource-status";
}

function clearResourceCache() {
  localStorage.removeItem(resourceCacheKey);
}

function saveResourceCache(data) {
  localStorage.setItem(resourceCacheKey, JSON.stringify({saved_at: Date.now(), data}));
}

function readResourceCache() {
  try {
    const cached = JSON.parse(localStorage.getItem(resourceCacheKey) || "null");
    if (!cached || Date.now() - cached.saved_at > resourceCacheMaxAge) return null;
    return cached.data;
  } catch (_) {
    return null;
  }
}

async function applyResources(data, fromCache = false) {
  setOptions(ui.compartment, data.compartments, (item) => item.id, (item) => item.name, t("choose_compartment"));
  setOptions(ui.availabilityDomain, data.availability_domains, (item) => item.name, (item) => item.name, t("choose_ad"));
  setOptions(ui.subnet, data.subnets, (item) => item.id, (item) => `${item.name} · ${item.compartment_name}`, t("choose_subnet"));
  loadedImages = data.images;
  const preferredOrder = ["Oracle Linux", "Canonical Ubuntu", "Ubuntu"];
  const families = [...new Set(data.images.map((item) => item.operating_system))].sort((left, right) => {
    const leftIndex = preferredOrder.indexOf(left);
    const rightIndex = preferredOrder.indexOf(right);
    if (leftIndex >= 0 || rightIndex >= 0) {
      return (leftIndex < 0 ? 999 : leftIndex) - (rightIndex < 0 ? 999 : rightIndex);
    }
    return left.localeCompare(right);
  });
  setOptions(ui.imageFamily, families, (item) => item, imageFamilyLabel, t("choose_os"));
  ui.compartment.selectedIndex = data.compartments.length ? 1 : 0;
  ui.availabilityDomain.selectedIndex = data.availability_domains.length ? 1 : 0;
  ui.subnet.selectedIndex = data.subnets.length ? 1 : 0;
  ui.imageFamily.value = families.includes("Oracle Linux") ? "Oracle Linux" : (families[0] || "");
  refreshSoftSelect(ui.compartment);
  refreshSoftSelect(ui.availabilityDomain);
  refreshSoftSelect(ui.subnet);
  refreshSoftSelect(ui.imageFamily);
  populateImages(ui.imageFamily.value);

  const storage = data.storage;
  const availableBootSize = Math.floor(storage.available_gb);
  const usedPercent = Math.min(100, (storage.used_gb / storage.total_gb) * 100);
  ui.storageMeter.hidden = false;
  ui.storageAvailable.textContent = t("storage_available", {gb: storage.available_gb});
  ui.storageUsedBar.style.width = `${usedPercent}%`;
  ui.storageDetail.textContent = t("storage_detail", {used: storage.used_gb, total: storage.total_gb});
  const maxBootSize = Math.max(50, Math.min(200, availableBootSize));
  ui.bootVolumeSize.max = String(maxBootSize);
  ui.bootVolumeRange.max = String(maxBootSize);
  ui.bootVolumeHint.textContent = t("boot_hint", {max: maxBootSize});
  syncBootVolume(ui.bootVolumeSize.value);

  const ready = data.compartments.length && data.availability_domains.length && data.subnets.length && data.images.length;
  if (!ready) throw new Error(t("load_failed"));
  if (storage.available_gb < storage.minimum_boot_volume_gb) {
    throw new Error(t("storage_insufficient", {available: storage.available_gb, minimum: storage.minimum_boot_volume_gb}));
  }
  ui.instanceFields.dataset.ready = "true";
  ui.instanceFields.disabled = false;
  if (sshKeyMode === "generate" && !generatedKeyId) await generateSshKey();
  updateStartAvailability();
  ui.resourceStatus.textContent = t("resources_summary", {cache: fromCache ? t("cache_prefix") : "", region: data.region, subnets: data.subnets.length, families: families.length, storage: storage.available_gb});
  ui.resourceStatus.className = "resource-status ready";
  activateConfigTab("instance");
}

async function loadResources(force = false) {
  ui.loadResources.disabled = true;
  ui.loadResources.textContent = t("loading");
  ui.resourceStatus.textContent = t("loading_resources");
  ui.resourceStatus.className = "resource-status loading";
  try {
    if (!force) {
      const cached = readResourceCache();
      if (cached) {
        await applyResources(cached, true);
        return;
      }
    }
    const response = await fetch("/api/oci/resources", {method: "POST", body: new FormData(ui.startForm)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || t("load_failed"));
    saveResourceCache(data);
    await applyResources(data);
  } catch (error) {
    delete ui.instanceFields.dataset.ready;
    ui.instanceFields.disabled = true;
    ui.startButton.disabled = true;
    ui.resourceStatus.textContent = error.message;
    ui.resourceStatus.className = "resource-status error";
  } finally {
    ui.loadResources.disabled = false;
    ui.loadResources.textContent = t("load_resources");
  }
}

ui.loadResources.addEventListener("click", () => loadResources(true));

const notificationRequirements = {telegram: ["telegram_token", "telegram_chat_id"], bark: ["bark_device_key"], pushplus: ["pushplus_token"], serverchan: ["serverchan_sendkey"], gotify: ["gotify_server", "gotify_app_token"], ntfy: ["ntfy_topic"], email: ["email_smtp_host", "email_username", "email_password", "email_from", "email_to"], webhook: ["webhook_url"]};
const notificationFieldNames = {telegram: ["telegram_token", "telegram_chat_id", "telegram_api_host"], bark: ["bark_device_key", "bark_server"], pushplus: ["pushplus_token", "pushplus_topic"], serverchan: ["serverchan_sendkey"], gotify: ["gotify_server", "gotify_app_token"], ntfy: ["ntfy_server", "ntfy_topic"], email: ["email_smtp_host", "email_smtp_port", "email_security", "email_username", "email_password", "email_from", "email_to"], webhook: ["webhook_provider", "webhook_url"]};
const webhookTypes = ["feishu", "dingtalk", "wecom", "discord", "slack", "generic"];
const notificationLabels = {telegram: "Telegram", bark: "Bark", pushplus: "PushPlus", serverchan: t("serverchan_label") || "ServerChan", gotify: "Gotify", ntfy: "ntfy", email: t("email_label") || "Email", feishu: t("feishu_label") || "Feishu", dingtalk: t("dingtalk_label") || "DingTalk", wecom: t("wecom_label") || "WeCom", discord: "Discord", slack: "Slack", generic: t("generic_label") || "Webhook"};
const notificationDescriptions = {telegram: t("telegram_desc"), bark: t("bark_desc"), pushplus: t("pushplus_desc"), serverchan: t("serverchan_desc"), gotify: t("gotify_desc"), ntfy: t("ntfy_desc"), email: t("email_desc"), feishu: t("feishu_desc"), dingtalk: t("dingtalk_desc"), wecom: t("wecom_desc"), discord: t("discord_desc"), slack: t("slack_desc"), generic: t("generic_desc")};
const notificationIcons = {
  telegram: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 3-18 7 7 2 2 7 3-5 4 3 2-14Z"/><path d="m10 12 8-5-6 7"/></svg>', bark: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4"/></svg>', pushplus: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/><circle cx="12" cy="12" r="9"/></svg>', serverchan: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 18h3v-4h3v4h3V9h3v9h4"/><path d="M4 6h16"/></svg>', gotify: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m13 2-8 12h6l-1 8 8-12h-6l1-8Z"/></svg>', ntfy: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 10a7 7 0 0 1 14 0M8 13a4 4 0 0 1 8 0M11 16a1 1 0 0 1 2 0"/><path d="M12 19v2"/></svg>', email: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/></svg>', feishu: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 5 9 2 7 12-8-3-4 3 1-7-5-7Z"/></svg>', dingtalk: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h14v10a6 6 0 0 1-6 6H9l-4-4V4Z"/><path d="M8 9h8M8 13h5"/></svg>', wecom: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12a6 6 0 0 1 11-3 5 5 0 0 1 5 5 5 5 0 0 1-5 5H9l-5 2 1-4a6 6 0 0 1-1-5Z"/><path d="M8 12h.01M12 12h.01"/></svg>', discord: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 7a16 16 0 0 1 12 0l2 10a16 16 0 0 1-5 2l-1-2H10l-1 2a16 16 0 0 1-5-2L6 7Z"/><path d="M8 13h.01M16 13h.01"/></svg>', slack: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4a2 2 0 1 0 0 4h3V5a2 2 0 0 0-3-1ZM20 9a2 2 0 1 0-4 0v3h3a2 2 0 0 0 1-3ZM15 20a2 2 0 1 0 0-4h-3v3a2 2 0 0 0 3 1ZM4 15a2 2 0 1 0 4 0v-3H5a2 2 0 0 0-1 3Z"/></svg>', generic: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1"/></svg>'
};
const notificationIconUrls = {telegram: "telegram.webp", bark: "bark.webp", pushplus: "pushplus.webp", serverchan: "serverchan.webp", gotify: "gotify.webp", ntfy: "ntfy.png", email: "email.webp", feishu: "feishu.webp", dingtalk: "dingtalk.webp", wecom: "wework_robot.webp", discord: "discord.png", slack: "slack.png", generic: "webhook.webp"};
Object.keys(notificationIconUrls).forEach((name) => { notificationIcons[name] = `<img src="/static/notification-icons/${notificationIconUrls[name]}" alt="">`; });
const notificationOrder = ["telegram", "bark", "pushplus", "serverchan", "gotify", "ntfy", "email", ...webhookTypes];
const notificationList = document.querySelector("#notification-list");
const notificationEmpty = document.querySelector("#notification-empty");
const notificationSummaryText = document.querySelector("#notification-summary-text");
const notificationCount = document.querySelector("#notification-count");
const notificationEditor = document.querySelector("#notification-editor");
const notificationEditorForm = document.querySelector("#notification-editor-form");
const notificationPicker = document.querySelector("#notification-channel-picker");
const channelOptions = [...document.querySelectorAll("[data-channel-option]")];
const editorFields = [...document.querySelectorAll(".editor-channel-fields")];
const editorEnabled = document.querySelector("#notification-editor-enabled");
const editorError = document.querySelector("#notification-editor-error");
const editorTestButton = document.querySelector("#test-notification-editor");
const selectedChannelGlyph = document.querySelector("#selected-channel-glyph");
const selectedChannelName = document.querySelector("#selected-channel-name");
const selectedChannelDescription = document.querySelector("#selected-channel-description");
let editingNotification = null;

channelOptions.forEach((option) => { const icon = option.querySelector(".channel-option-icon"); icon.classList.add(`channel-icon-${option.dataset.channelOption}`); icon.innerHTML = notificationIcons[option.dataset.channelOption]; });
selectedChannelGlyph.innerHTML = notificationIcons.telegram;

function notificationFieldReady(field) { return field.dataset.provided === "true" || Boolean(field.value.trim()); }
function internalChannel(name) { return webhookTypes.includes(name) ? "webhook" : name; }
function fieldsFor(name) { return editorFields.find((group) => group.dataset.editorChannel === internalChannel(name)); }
function notificationReady(name) { const channel = internalChannel(name); return notificationRequirements[channel].every((fieldName) => notificationEditorForm.elements[fieldName] && notificationFieldReady(notificationEditorForm.elements[fieldName])); }
function notificationChannels() { return (notificationList.dataset.channels || "").split(",").filter(Boolean); }
function notificationExists(name) { return notificationChannels().includes(name); }
function syncNotificationFields(name) {
  const channel = internalChannel(name);
  const names = notificationFieldNames[channel];
  names.concat(`${channel}_enabled`).forEach((fieldName) => {
    const source = notificationEditorForm.elements[fieldName];
    let target = ui.startForm.elements[fieldName];
    if (!target) { target = document.createElement("input"); target.type = "hidden"; target.name = fieldName; ui.startForm.append(target); }
    if (source.type === "checkbox") target.value = source.checked ? "true" : "false";
    else target.value = source.value;
  });
}
function setEditorChannel(name) {
  notificationPicker.value = name;
  const channel = internalChannel(name);
  editorFields.forEach((group) => { group.hidden = group.dataset.editorChannel !== channel; group.disabled = group.dataset.editorChannel !== channel; });
  if (channel === "webhook") notificationEditorForm.elements.webhook_provider.value = name;
  channelOptions.forEach((option) => {
    const active = option.dataset.channelOption === name;
    option.classList.toggle("is-active", active);
    option.setAttribute("aria-pressed", String(active));
    option.classList.toggle("is-configured", notificationExists(option.dataset.channelOption));
    option.querySelector("i").textContent = notificationExists(option.dataset.channelOption) ? t("added") : "";
  });
  selectedChannelGlyph.className = `selected-channel-glyph channel-glyph-${name}`;
  selectedChannelGlyph.innerHTML = notificationIcons[name];
  selectedChannelName.textContent = notificationLabels[name];
  selectedChannelDescription.textContent = notificationDescriptions[name];
  editorError.textContent = "";
}
function selectNotificationChannel(name) {
  editingNotification = name;
  setEditorChannel(name);
  const exists = notificationExists(name);
  document.querySelector("#notification-editor-title").textContent = exists ? t("title_edit") : t("title_add");
  document.querySelector("#notification-editor-copy").textContent = exists ? t("copy_edit", {name: notificationLabels[name]}) : t("copy_add", {name: notificationLabels[name]});
  document.querySelector("#save-notification").textContent = exists ? t("save") : t("add_to_job");
  editorEnabled.checked = notificationEditorForm.elements[`${internalChannel(name)}_enabled`]?.checked || false;
}
function renderNotificationCards() {
  notificationList.replaceChildren();
  const activeNames = [...new Set(notificationChannels())];
  let enabledCount = 0;
  activeNames.forEach((name) => {
    const card = document.createElement("article");
    card.className = "notification-channel";
    card.dataset.notificationChannel = name;
    const enabled = notificationEditorForm.elements[`${internalChannel(name)}_enabled`]?.checked;
    const ready = notificationReady(name);
    if (ready && enabled) enabledCount += 1;
    card.classList.toggle("is-enabled", ready && enabled);
    const state = ready ? (enabled ? t("state_sending") : t("state_paused")) : t("state_incomplete");
    card.innerHTML = `<div class="notification-card-main"><span class="channel-glyph channel-glyph-${name}">${notificationIcons[name]}</span><div class="channel-copy"><div><b>${notificationLabels[name]}</b><span class="channel-state ${ready && enabled ? "is-on" : ""}">${state}</span></div><small>${notificationDescriptions[name]}</small></div><button class="notification-edit" type="button">${t("edit")}</button></div><div class="notification-card-footer"><label class="channel-toggle"><input type="checkbox" ${enabled ? "checked" : ""} ${ready ? "" : "disabled"}><span class="toggle-switch" aria-hidden="true"><i></i></span><span class="toggle-label"><b>${t("send_with_job")}</b><small>${ready ? t("send_when_ready") : t("finish_channel_first")}</small></span></label><button class="button ghost notification-test" type="button" ${ready ? "" : "disabled"}>${t("send_test")}</button></div>`;
    card.querySelector("input").addEventListener("change", (event) => {
      notificationEditorForm.elements[`${internalChannel(name)}_enabled`].checked = event.target.checked;
      syncNotificationFields(name);
      renderNotificationCards();
    });
    card.querySelector(".notification-test").addEventListener("click", () => testNotification(name));
    card.querySelector(".notification-edit").addEventListener("click", () => openNotificationEditor(name));
    notificationList.append(card);
  });
  notificationEmpty.hidden = activeNames.length > 0;
  notificationList.hidden = activeNames.length === 0;
  notificationCount.textContent = t("channel_count", {count: activeNames.length});
  notificationSummaryText.textContent = !activeNames.length ? t("notify_none") : enabledCount ? t("notify_enabled", {count: enabledCount}) : t("notify_paused");
  channelOptions.forEach((option) => {
    const configured = activeNames.includes(option.dataset.channelOption);
    option.classList.toggle("is-configured", configured);
    option.querySelector("i").textContent = configured ? t("added") : "";
  });
}
function openNotificationEditor(name = "telegram") {
  selectNotificationChannel(name);
  notificationEditor.showModal();
}
function closeNotificationEditor() { notificationEditor.close(); editorError.textContent = ""; }
document.querySelector("#add-notification").addEventListener("click", () => {
  const existing = notificationChannels();
  const next = notificationOrder.find((name) => !existing.includes(name)) || existing[0] || "telegram";
  openNotificationEditor(next);
});
document.querySelector("#empty-add-notification").addEventListener("click", () => document.querySelector("#add-notification").click());

async function testNotification(name, useEditorValues = false) {
  const form = new FormData(ui.startForm);
  const channel = internalChannel(name);
  if (useEditorValues) {
    notificationFieldNames[channel].forEach((fieldName) => {
      const source = notificationEditorForm.elements[fieldName];
      if (source) form.set(fieldName, source.value);
    });
  }
  form.set("channel", channel);
  try {
    const response = await fetch("/api/notifications/test", {method: "POST", body: form});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || t("test_failed"));
    notify(data.message || t("test_sent"));
    return true;
  } catch (error) {
    if (useEditorValues) editorError.textContent = error.message;
    else notify(error.message);
    return false;
  }
}
editorTestButton.addEventListener("click", async () => {
  const name = notificationPicker.value;
  editorError.textContent = "";
  if (!notificationReady(name)) {
    editorError.textContent = t("fill_before_test");
    fieldsFor(name).querySelector("input").focus();
    return;
  }
  const originalText = editorTestButton.textContent;
  editorTestButton.disabled = true;
  editorTestButton.textContent = t("sending");
  await testNotification(name, true);
  editorTestButton.disabled = false;
  editorTestButton.textContent = originalText;
});
channelOptions.forEach((option) => option.addEventListener("click", () => selectNotificationChannel(option.dataset.channelOption)));
notificationEditorForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const name = notificationPicker.value;
  const existed = notificationExists(name);
  if (!notificationReady(name)) { editorError.textContent = t("fill_required"); fieldsFor(name).querySelector("input").focus(); return; }
  notificationEditorForm.elements[`${internalChannel(name)}_enabled`].checked = editorEnabled.checked;
  syncNotificationFields(name);
  const channels = new Set(notificationChannels());
  if (internalChannel(name) === "webhook") [...channels].filter((item) => webhookTypes.includes(item)).forEach((item) => channels.delete(item));
  channels.add(name);
  notificationList.dataset.channels = [...channels].join(",");
  renderNotificationCards();
  closeNotificationEditor();
  notify(existed ? t("channel_updated", {name: notificationLabels[name]}) : t("channel_added", {name: notificationLabels[name]}));
});
document.querySelector("#close-notification-editor").addEventListener("click", closeNotificationEditor);
document.querySelector("#cancel-notification-editor").addEventListener("click", closeNotificationEditor);
notificationEditor.addEventListener("click", (event) => { if (event.target === notificationEditor) closeNotificationEditor(); });

[
  "telegram", "bark", "pushplus", "serverchan", "gotify", "ntfy", "email", "webhook"
].forEach((name) => {
  notificationRequirements[internalChannel(name)].forEach((fieldName) => notificationEditorForm.elements[fieldName]?.addEventListener("input", () => {
    const channelNames = internalChannel(name) === "webhook" ? webhookTypes : [name];
    channelNames.forEach((channelName) => {
      const toggle = notificationList.querySelector(`[data-notification-channel="${channelName}"] input[type="checkbox"]`);
      if (toggle) toggle.disabled = !notificationReady(channelName);
    });
  }));
  const enabled = document.createElement("input");
  enabled.type = "checkbox"; enabled.name = `${name}_enabled`; enabled.value = "true"; enabled.hidden = true; enabled.checked = notificationList.dataset[`initial${name[0].toUpperCase()}${name.slice(1)}Enabled`] === "true";
  notificationEditorForm.append(enabled);
  syncNotificationFields(name);
});
if (notificationList.dataset.initialTelegram === "true") notificationList.dataset.channels = "telegram";
if (notificationList.dataset.initialBark === "true") notificationList.dataset.channels = `${notificationList.dataset.channels ? `${notificationList.dataset.channels},` : ""}bark`;
if (notificationList.dataset.initialPushplus === "true") notificationList.dataset.channels = `${notificationList.dataset.channels ? `${notificationList.dataset.channels},` : ""}pushplus`;
if (notificationList.dataset.initialServerchan === "true") notificationList.dataset.channels = `${notificationList.dataset.channels ? `${notificationList.dataset.channels},` : ""}serverchan`;
if (notificationList.dataset.initialGotify === "true") notificationList.dataset.channels = `${notificationList.dataset.channels ? `${notificationList.dataset.channels},` : ""}gotify`;
if (notificationList.dataset.initialNtfy === "true") notificationList.dataset.channels = `${notificationList.dataset.channels ? `${notificationList.dataset.channels},` : ""}ntfy`;
if (notificationList.dataset.initialEmail === "true") notificationList.dataset.channels = `${notificationList.dataset.channels ? `${notificationList.dataset.channels},` : ""}email`;
if (notificationList.dataset.initialWebhook === "true") notificationList.dataset.channels = `${notificationList.dataset.channels ? `${notificationList.dataset.channels},` : ""}${notificationList.dataset.initialWebhookProvider || "generic"}`;
renderNotificationCards();

ui.startForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!sshKeyReady()) {
    notify(sshKeyMode === "generate" ? t("download_key_first") : t("paste_pubkey_first"));
    return;
  }
  ui.startButton.disabled = true;
  try {
    const response = await fetch("/api/start", {method: "POST", body: new FormData(ui.startForm)});
    const data = await response.json();
    notify(response.ok ? t("job_started") : data.error);
  } catch (_) {
    notify(t("connect_failed"));
  }
  await refreshStatus();
});

ui.stopForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const response = await fetch("/api/stop", {method: "POST", body: new FormData(ui.stopForm)});
  const data = await response.json();
  notify(response.ok ? t("stop_sent") : data.error);
  await refreshStatus();
});

document.querySelector("#copy-button").addEventListener("click", async () => {
  await navigator.clipboard.writeText(ui.logs.textContent);
  notify(t("logs_copied"));
});

function closeOciDialog() {
  ui.ociDialog.close();
  ui.ociCredentialsForm.reset();
  ui.ociConfigError.textContent = "";
}

ui.configureOci.addEventListener("click", () => ui.ociDialog.showModal());
document.querySelector("#close-oci-dialog").addEventListener("click", closeOciDialog);
document.querySelector("#cancel-oci-dialog").addEventListener("click", closeOciDialog);
ui.ociDialog.addEventListener("click", (event) => {
  if (event.target === ui.ociDialog) closeOciDialog();
});
ui.ociCredentialsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const replacing = ui.ociCredentialsForm.dataset.configured === "true";
  if (replacing && !window.confirm(t("confirm_replace_oci"))) return;
  ui.ociConfigError.textContent = "";
  const submit = ui.ociCredentialsForm.querySelector('button[type="submit"]');
  submit.disabled = true;
  try {
    const response = await fetch("/api/oci/configure", {
      method: "POST",
      body: new FormData(ui.ociCredentialsForm),
    });
    const data = await response.json();
    if (!response.ok) {
      ui.ociConfigError.textContent = data.error;
      return;
    }
    ui.ociCredentialsForm.dataset.configured = "true";
    ui.configureOci.textContent = t("replace_oci");
    ui.ociDialogTitle.textContent = t("replace_oci");
    ui.ociCredentialWarning.textContent = t("oci_warning_replace");
    submit.textContent = t("confirm_replace_load");
    markResourcesStale();
    closeOciDialog();
    notify(replacing ? t("channel_updated", {name: "OCI"}) : t("channel_added", {name: "OCI"}));
    loadResources(true);
  } catch (_) {
    ui.ociConfigError.textContent = t("connect_failed");
  } finally {
    submit.disabled = false;
  }
});

connectStatusStream();
if (document.querySelector("main.page-shell").dataset.ociConfigured === "true") loadResources();
