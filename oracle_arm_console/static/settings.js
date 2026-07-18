const settingsUi = {
  toast: document.querySelector("#toast"),
  passwordForm: document.querySelector("#settings-password-form"),
  passwordError: document.querySelector("#settings-password-error"),
  ociForm: document.querySelector("#settings-oci-form"),
  ociError: document.querySelector("#settings-oci-error"),
  ociWarning: document.querySelector("#settings-oci-warning"),
  ociBadge: document.querySelector("#oci-status-badge"),
  ociHealthItem: document.querySelector("#oci-health-item"),
  ociHealthText: document.querySelector("#oci-health-text"),
  ociProfile: document.querySelector("#oci-profile-name"),
  ociRegion: document.querySelector("#oci-region-name"),
};

let settingsToastTimer;

function settingsNotify(message) {
  settingsUi.toast.textContent = message;
  settingsUi.toast.classList.add("visible");
  clearTimeout(settingsToastTimer);
  settingsToastTimer = setTimeout(() => settingsUi.toast.classList.remove("visible"), 2600);
}

settingsUi.passwordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  settingsUi.passwordError.textContent = "";
  const submit = settingsUi.passwordForm.querySelector('button[type="submit"]');
  submit.disabled = true;
  try {
    const response = await fetch("/api/settings/password", {
      method: "POST",
      body: new FormData(settingsUi.passwordForm),
    });
    const data = await response.json();
    if (!response.ok) {
      settingsUi.passwordError.textContent = data.error;
      return;
    }
    settingsUi.passwordForm.reset();
    settingsNotify("管理密码已更新");
  } catch (_) {
    settingsUi.passwordError.textContent = "无法连接到控制台";
  } finally {
    submit.disabled = false;
  }
});

settingsUi.ociForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const replacing = settingsUi.ociForm.dataset.configured === "true";
  if (replacing && !window.confirm("将替换现有 OCI 配置和 API 私钥，是否继续？")) return;
  settingsUi.ociError.textContent = "";
  const submit = settingsUi.ociForm.querySelector('button[type="submit"]');
  submit.disabled = true;
  try {
    const response = await fetch("/api/oci/configure", {
      method: "POST",
      body: new FormData(settingsUi.ociForm),
    });
    const data = await response.json();
    if (!response.ok) {
      settingsUi.ociError.textContent = data.error;
      return;
    }
    settingsUi.ociForm.dataset.configured = "true";
    settingsUi.ociForm.reset();
    settingsUi.ociBadge.textContent = "已配置";
    settingsUi.ociBadge.className = "settings-badge is-ready";
    settingsUi.ociHealthItem.className = "health-item is-ready";
    settingsUi.ociHealthText.textContent = "已连接";
    settingsUi.ociProfile.textContent = data.profile;
    settingsUi.ociRegion.textContent = data.region;
    settingsUi.ociWarning.textContent = "提交后将同时替换现有配置和 API 私钥，旧私钥不会显示。";
    submit.textContent = "替换 OCI 凭据";
    settingsNotify(replacing ? "OCI 凭据已更新" : "OCI 凭据已保存");
  } catch (_) {
    settingsUi.ociError.textContent = "无法连接到控制台";
  } finally {
    submit.disabled = false;
  }
});
