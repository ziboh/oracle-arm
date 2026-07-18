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
    settingsNotify(t("password_updated"));
  } catch (_) {
    settingsUi.passwordError.textContent = t("connect_failed");
  } finally {
    submit.disabled = false;
  }
});

settingsUi.ociForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const replacing = settingsUi.ociForm.dataset.configured === "true";
  if (replacing && !window.confirm(t("confirm_replace_oci"))) return;
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
    settingsUi.ociBadge.textContent = t("oci_configured");
    settingsUi.ociBadge.className = "settings-badge is-ready";
    settingsUi.ociHealthItem.className = "health-item is-ready";
    settingsUi.ociHealthText.textContent = t("oci_connected");
    settingsUi.ociProfile.textContent = data.profile;
    settingsUi.ociRegion.textContent = data.region;
    settingsUi.ociWarning.textContent = t("oci_warning_replace");
    submit.textContent = t("replace_oci");
    settingsNotify(replacing ? t("channel_updated", {name: "OCI"}) : t("channel_added", {name: "OCI"}));
  } catch (_) {
    settingsUi.ociError.textContent = t("connect_failed");
  } finally {
    submit.disabled = false;
  }
});
