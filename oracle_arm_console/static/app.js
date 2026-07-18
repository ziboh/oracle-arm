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
  return value ? new Date(value).toLocaleString() : "—";
}

function sshKeyReady() {
  return sshKeyMode === "generate" ? privateKeyDownloaded : Boolean(uploadedPublicKey);
}

function syncManualPublicKey() {
  uploadedPublicKey = normalizePublicKey(ui.sshKeys.value);
  const valid = isValidPublicKey(uploadedPublicKey);
  if (uploadedPublicKey && !valid) {
    setUploadKeyStatus("格式无效：请输入 ssh-ed25519、ssh-rsa 或 ECDSA 公钥", false);
  } else if (valid) {
    setUploadKeyStatus("公钥已就绪，可直接开始创建", true);
  } else {
    setUploadKeyStatus("请在上方文本框中粘贴公钥，不要填写私钥");
  }
  updateStartAvailability();
}

function updateStartAvailability(running = false) {
  ui.startButton.disabled = running || ui.instanceFields.disabled || !sshKeyReady();
}

async function refreshStatus() {
  try {
    const response = await fetch("/api/status", {headers: {Accept: "application/json"}});
    if (!response.ok) return;
    const data = await response.json();
    ui.statusText.textContent = data.running ? "抢注进行中" : data.state === "idle" ? "等待启动" : "任务已结束";
    ui.statusDot.classList.toggle("running", data.running);
    document.body.classList.toggle("task-running", data.running);
    ui.startedAt.textContent = formatTime(data.started_at);
    ui.exitCode.textContent = data.exit_code === null ? "—" : String(data.exit_code);
    updateStartAvailability(data.running);
    ui.loadResources.disabled = data.running;
    ui.instanceFields.disabled = data.running || !ui.instanceFields.dataset.ready;
    ui.stopButton.disabled = !data.running;
    const stickToBottom = ui.logs.scrollHeight - ui.logs.scrollTop - ui.logs.clientHeight < 48;
    ui.logs.textContent = data.logs.length ? data.logs.join("\n") : "等待任务启动";
    if (stickToBottom) ui.logs.scrollTop = ui.logs.scrollHeight;
  } catch (_) {
    ui.statusText.textContent = "连接已中断";
    ui.statusDot.classList.remove("running");
  }
}

function setOptions(select, items, valueFor, labelFor, emptyLabel) {
  const placeholder = new Option(emptyLabel, "", true, true);
  placeholder.disabled = true;
  placeholder.hidden = true;
  select.replaceChildren(placeholder);
  items.forEach((item) => select.add(new Option(labelFor(item), valueFor(item))));
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
    "选择具体镜像",
  );
  const preferred = family === "Oracle Linux"
    ? images.findIndex((item) => String(item.version).startsWith("9"))
    : 0;
  ui.image.selectedIndex = images.length ? Math.max(preferred, 0) + 1 : 0;
}

ui.imageFamily.addEventListener("change", () => populateImages(ui.imageFamily.value));

async function generateSshKey() {
  ui.regenerateSshKey.disabled = true;
  ui.downloadSshKey.hidden = true;
  ui.sshKeyStatus.textContent = "正在生成 Ed25519 密钥...";
  privateKeyDownloaded = false;
  ui.startButton.disabled = true;
  try {
    const form = new FormData();
    form.append("csrf_token", ui.startForm.elements.csrf_token.value);
    const response = await fetch("/api/ssh-keys", {method: "POST", body: form});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "生成 SSH 密钥失败");
    generatedKeyId = data.id;
    generatedPublicKey = data.public_key;
    if (sshKeyMode === "generate") ui.sshKeys.value = generatedPublicKey;
    ui.downloadSshKey.href = data.download_url;
    ui.downloadSshKey.hidden = false;
    ui.sshKeyStatus.textContent = `${data.fingerprint} · 请下载私钥`;
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
    notify("无法生成 SSH 密钥");
  }
});

ui.downloadSshKey.addEventListener("click", () => {
  privateKeyDownloaded = true;
  ui.sshKeyStatus.textContent = "私钥已请求下载，请妥善保存";
  updateStartAvailability();
});

document.querySelectorAll('input[name="ssh_key_mode"]').forEach((input) => {
  input.addEventListener("change", async () => {
    sshKeyMode = input.value;
    ui.generatedKeyPanel.hidden = sshKeyMode !== "generate";
    ui.uploadKeyPanel.hidden = sshKeyMode !== "upload";
    ui.sshKeys.value = sshKeyMode === "generate" ? generatedPublicKey : uploadedPublicKey;
    ui.sshKeys.readOnly = sshKeyMode === "generate";
    ui.sshKeys.placeholder = sshKeyMode === "generate" ? "读取资源后自动生成" : "粘贴一行或多行 SSH 公钥，例如 ssh-ed25519 AAAA...";
    ui.sshPublicKeyHint.textContent = sshKeyMode === "generate" ? "自动生成模式下，读取资源后会自动填充" : "直接粘贴一行或多行 SSH 公钥，不要填写私钥";
    if (sshKeyMode === "generate" && !generatedKeyId && ui.instanceFields.dataset.ready) {
      try {
        await generateSshKey();
      } catch (_) {
        notify("无法生成 SSH 密钥");
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
    setUploadKeyStatus("公钥文件不能超过 64 KB", false);
    updateStartAvailability();
    return;
  }
  const content = normalizePublicKey(await file.text());
  if (!isValidPublicKey(content)) {
    setUploadKeyStatus("文件不是有效的 SSH 公钥，请选择 .pub 文件", false);
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
  ui.resourceStatus.textContent = "连接配置已更改，请重新读取 OCI 资源。";
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
  setOptions(ui.compartment, data.compartments, (item) => item.id, (item) => item.name, "选择实例区间");
  setOptions(ui.availabilityDomain, data.availability_domains, (item) => item.name, (item) => item.name, "选择可用域");
  setOptions(ui.subnet, data.subnets, (item) => item.id, (item) => `${item.name} · ${item.compartment_name}`, "选择公共子网");
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
  setOptions(ui.imageFamily, families, (item) => item, imageFamilyLabel, "选择操作系统");
  ui.compartment.selectedIndex = data.compartments.length ? 1 : 0;
  ui.availabilityDomain.selectedIndex = data.availability_domains.length ? 1 : 0;
  ui.subnet.selectedIndex = data.subnets.length ? 1 : 0;
  ui.imageFamily.value = families.includes("Oracle Linux") ? "Oracle Linux" : (families[0] || "");
  populateImages(ui.imageFamily.value);

  const storage = data.storage;
  const availableBootSize = Math.floor(storage.available_gb);
  const usedPercent = Math.min(100, (storage.used_gb / storage.total_gb) * 100);
  ui.storageMeter.hidden = false;
  ui.storageAvailable.textContent = `可用 ${storage.available_gb} GB`;
  ui.storageUsedBar.style.width = `${usedPercent}%`;
  ui.storageDetail.textContent = `已用 ${storage.used_gb} GB / 免费总额 ${storage.total_gb} GB`;
  const maxBootSize = Math.max(50, Math.min(200, availableBootSize));
  ui.bootVolumeSize.max = String(maxBootSize);
  ui.bootVolumeRange.max = String(maxBootSize);
  ui.bootVolumeHint.textContent = `可选 50–${maxBootSize} GB · 滑动、滚轮或输入数值`;
  syncBootVolume(ui.bootVolumeSize.value);

  const ready = data.compartments.length && data.availability_domains.length && data.subnets.length && data.images.length;
  if (!ready) throw new Error("OCI 账户中没有找到完整的区间、公共子网或 A1 镜像");
  if (storage.available_gb < storage.minimum_boot_volume_gb) {
    throw new Error(`免费块存储仅剩 ${storage.available_gb} GB，不足以创建 ${storage.minimum_boot_volume_gb} GB 启动盘`);
  }
  ui.instanceFields.dataset.ready = "true";
  ui.instanceFields.disabled = false;
  if (sshKeyMode === "generate" && !generatedKeyId) await generateSshKey();
  updateStartAvailability();
  ui.resourceStatus.textContent = `${fromCache ? "已使用缓存 · " : ""}${data.region} · ${data.subnets.length} 个公共子网 · ${families.length} 类系统 · 可用存储 ${storage.available_gb} GB`;
  ui.resourceStatus.className = "resource-status ready";
  activateConfigTab("instance");
}

async function loadResources(force = false) {
  ui.loadResources.disabled = true;
  ui.loadResources.textContent = "正在读取";
  ui.resourceStatus.textContent = "正在验证 API 配置并查询东京区域资源...";
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
    if (!response.ok) throw new Error(data.error || "读取 OCI 资源失败");
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
    ui.loadResources.textContent = "读取 OCI 资源";
  }
}

ui.loadResources.addEventListener("click", () => loadResources(true));

const notificationRequirements = {telegram: ["telegram_token", "telegram_chat_id"], bark: ["bark_device_key"], email: ["email_smtp_host", "email_username", "email_password", "email_from", "email_to"], webhook: ["webhook_url"]};
const notificationFieldNames = {telegram: ["telegram_token", "telegram_chat_id", "telegram_api_host"], bark: ["bark_device_key", "bark_server"], email: ["email_smtp_host", "email_smtp_port", "email_security", "email_username", "email_password", "email_from", "email_to"], webhook: ["webhook_provider", "webhook_url"]};
const webhookTypes = ["feishu", "dingtalk", "wecom", "discord", "slack", "generic"];
const notificationLabels = {telegram: "Telegram", bark: "Bark", email: "电子邮件", feishu: "飞书机器人", dingtalk: "钉钉机器人", wecom: "企业微信", discord: "Discord", slack: "Slack", generic: "通用 Webhook"};
const notificationDescriptions = {telegram: "通过 Telegram Bot 接收任务结果", bark: "推送到 iPhone 或 macOS", email: "通过 SMTP 发送结果邮件", feishu: "发送到飞书群机器人", dingtalk: "发送到钉钉群机器人", wecom: "发送到企业微信群机器人", discord: "发送到 Discord 频道", slack: "发送到 Slack 频道", generic: "向自定义地址发送 JSON 请求"};
const notificationGlyphs = {telegram: "TG", bark: "BK", email: "@", feishu: "FS", dingtalk: "DT", wecom: "WX", discord: "DC", slack: "SL", generic: "WH"};
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
    option.querySelector("i").textContent = notificationExists(option.dataset.channelOption) ? "已添加" : "";
  });
  selectedChannelGlyph.textContent = notificationGlyphs[name];
  selectedChannelName.textContent = notificationLabels[name];
  selectedChannelDescription.textContent = notificationDescriptions[name];
  editorError.textContent = "";
}
function selectNotificationChannel(name) {
  editingNotification = name;
  setEditorChannel(name);
  const exists = notificationExists(name);
  document.querySelector("#notification-editor-title").textContent = exists ? "编辑通知渠道" : "添加通知渠道";
  document.querySelector("#notification-editor-copy").textContent = exists ? `更新 ${notificationLabels[name]} 的连接信息和发送状态。` : `配置 ${notificationLabels[name]}，任务成功后自动发送结果。`;
  document.querySelector("#save-notification").textContent = exists ? "保存渠道设置" : "添加到任务";
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
    const state = ready ? (enabled ? "发送中" : "已暂停") : "需完善";
    card.innerHTML = `<div class="notification-card-main"><span class="channel-glyph">${notificationGlyphs[name]}</span><div class="channel-copy"><div><b>${notificationLabels[name]}</b><span class="channel-state ${ready && enabled ? "is-on" : ""}">${state}</span></div><small>${notificationDescriptions[name]}</small></div><button class="notification-edit" type="button">编辑</button></div><div class="notification-card-footer"><label class="channel-toggle"><input type="checkbox" ${enabled ? "checked" : ""} ${ready ? "" : "disabled"}><span class="toggle-switch" aria-hidden="true"><i></i></span><span class="toggle-label"><b>随当前任务发送</b><small>${ready ? "实例创建成功后立即通知" : "先完成渠道连接信息"}</small></span></label><button class="button ghost notification-test" type="button" ${ready ? "" : "disabled"}>发送测试</button></div>`;
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
  notificationCount.textContent = `${activeNames.length} 个渠道`;
  notificationSummaryText.textContent = !activeNames.length ? "尚未配置通知" : enabledCount ? `${enabledCount} 个渠道会在成功后发送` : "渠道已保存，当前均未启用";
  channelOptions.forEach((option) => {
    const configured = activeNames.includes(option.dataset.channelOption);
    option.classList.toggle("is-configured", configured);
    option.querySelector("i").textContent = configured ? "已添加" : "";
  });
}
function openNotificationEditor(name = "telegram") {
  selectNotificationChannel(name);
  notificationEditor.showModal();
}
function closeNotificationEditor() { notificationEditor.close(); editorError.textContent = ""; }
document.querySelector("#add-notification").addEventListener("click", () => {
  const existing = notificationChannels();
  const next = ["telegram", "bark", "email", ...webhookTypes].find((name) => !existing.includes(name)) || existing[0] || "telegram";
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
    if (!response.ok) throw new Error(data.error || "测试通知失败");
    notify(data.message || "测试通知已发送");
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
    editorError.textContent = "请先填写当前渠道的必填连接信息，再发送测试。";
    fieldsFor(name).querySelector("input").focus();
    return;
  }
  const originalText = editorTestButton.textContent;
  editorTestButton.disabled = true;
  editorTestButton.textContent = "正在发送…";
  await testNotification(name, true);
  editorTestButton.disabled = false;
  editorTestButton.textContent = originalText;
});
channelOptions.forEach((option) => option.addEventListener("click", () => selectNotificationChannel(option.dataset.channelOption)));
notificationEditorForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const name = notificationPicker.value;
  const existed = notificationExists(name);
  if (!notificationReady(name)) { editorError.textContent = "请填写当前渠道的必填连接信息。"; fieldsFor(name).querySelector("input").focus(); return; }
  notificationEditorForm.elements[`${internalChannel(name)}_enabled`].checked = editorEnabled.checked;
  syncNotificationFields(name);
  const channels = new Set(notificationChannels());
  if (internalChannel(name) === "webhook") [...channels].filter((item) => webhookTypes.includes(item)).forEach((item) => channels.delete(item));
  channels.add(name);
  notificationList.dataset.channels = [...channels].join(",");
  renderNotificationCards();
  closeNotificationEditor();
  notify(existed ? `${notificationLabels[name]} 设置已更新` : `${notificationLabels[name]} 已添加到任务`);
});
document.querySelector("#close-notification-editor").addEventListener("click", closeNotificationEditor);
document.querySelector("#cancel-notification-editor").addEventListener("click", closeNotificationEditor);
notificationEditor.addEventListener("click", (event) => { if (event.target === notificationEditor) closeNotificationEditor(); });

["telegram", "bark", "email", "webhook"].forEach((name) => {
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
if (notificationList.dataset.initialEmail === "true") notificationList.dataset.channels = `${notificationList.dataset.channels ? `${notificationList.dataset.channels},` : ""}email`;
if (notificationList.dataset.initialWebhook === "true") notificationList.dataset.channels = `${notificationList.dataset.channels ? `${notificationList.dataset.channels},` : ""}${notificationList.dataset.initialWebhookProvider || "generic"}`;
renderNotificationCards();

ui.startForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!sshKeyReady()) {
    notify(sshKeyMode === "generate" ? "请先下载实例登录私钥" : "请粘贴或选择有效的 SSH 公钥");
    return;
  }
  ui.startButton.disabled = true;
  try {
    const response = await fetch("/api/start", {method: "POST", body: new FormData(ui.startForm)});
    const data = await response.json();
    notify(response.ok ? "已开始等待 A1 容量" : data.error);
  } catch (_) {
    notify("无法连接到控制台");
  }
  await refreshStatus();
});

ui.stopForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const response = await fetch("/api/stop", {method: "POST", body: new FormData(ui.stopForm)});
  const data = await response.json();
  notify(response.ok ? "停止请求已发送" : data.error);
  await refreshStatus();
});

document.querySelector("#copy-button").addEventListener("click", async () => {
  await navigator.clipboard.writeText(ui.logs.textContent);
  notify("运行日志已复制");
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
  if (replacing && !window.confirm("将替换现有 OCI 配置和 API 私钥，是否继续？")) return;
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
    ui.configureOci.textContent = "替换 OCI 凭据";
    ui.ociDialogTitle.textContent = "替换 OCI 凭据";
    ui.ociCredentialWarning.textContent = "OCI 私钥无法回显或单独编辑。请重新提交完整配置片段和配套私钥，保存后将整体替换现有凭据。";
    submit.textContent = "确认替换并读取资源";
    markResourcesStale();
    closeOciDialog();
    notify(replacing ? "OCI 凭据已更新" : "OCI 凭据已保存");
    loadResources(true);
  } catch (_) {
    ui.ociConfigError.textContent = "无法连接到控制台";
  } finally {
    submit.disabled = false;
  }
});

refreshStatus();
if (document.querySelector("main.page-shell").dataset.ociConfigured === "true") loadResources();
setInterval(refreshStatus, 2000);
