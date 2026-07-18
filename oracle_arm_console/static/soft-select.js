(function () {
  "use strict";

  const ENHANCED = "is-enhanced";
  const OPEN = "is-open";
  const instances = new WeakMap();
  let openInstance = null;

  function isHiddenSelect(select) {
    if (!select || select.tagName !== "SELECT") return true;
    if (select.hidden || select.getAttribute("aria-hidden") === "true") return true;
    if (select.hasAttribute("hidden")) return true;
    return false;
  }

  function optionLabel(option) {
    return (option.label || option.textContent || "").trim();
  }

  function selectedOption(select) {
    if (select.selectedIndex >= 0) return select.options[select.selectedIndex];
    return select.options[0] || null;
  }

  function setValueLabel(instance) {
    if (instance.isLang) {
      // Language switcher keeps a fixed 文A glyph; never overwrite it with the locale name.
      return;
    }
    const option = selectedOption(instance.select);
    const label = option ? optionLabel(option) : "";
    const isPlaceholder = Boolean(
      option &&
        (option.disabled || option.hidden || option.value === "") &&
        !option.value,
    );
    instance.valueEl.textContent = label || "—";
    instance.valueEl.classList.toggle("is-placeholder", isPlaceholder || !label);
  }

  function closePanel(instance) {
    if (!instance || !instance.wrap.classList.contains(OPEN)) return;
    instance.wrap.classList.remove(OPEN);
    instance.trigger.setAttribute("aria-expanded", "false");
    instance.panel.hidden = true;
    if (openInstance === instance) openInstance = null;
  }

  function closeAll(except) {
    if (openInstance && openInstance !== except) closePanel(openInstance);
  }

  function placePanel(instance) {
    const rect = instance.trigger.getBoundingClientRect();
    const minWidth = Math.max(rect.width, instance.isLang ? 148 : 160);
    const maxHeight = Math.min(280, window.innerHeight * 0.48);
    const gap = instance.isLang ? 6 : 2;
    const spaceBelow = window.innerHeight - rect.bottom - gap;
    const spaceAbove = rect.top - gap;
    const preferTop = spaceBelow < Math.min(220, maxHeight) && spaceAbove > spaceBelow;

    instance.panel.dataset.placement = preferTop ? "top" : "bottom";
    instance.panel.style.position = "fixed";
    // Language menu aligns to the right edge of the circular button (like common i18n menus).
    if (instance.isLang) {
      const left = Math.max(8, Math.min(rect.right - minWidth, window.innerWidth - minWidth - 8));
      instance.panel.style.left = `${left}px`;
    } else {
      instance.panel.style.left = `${Math.min(rect.left, window.innerWidth - minWidth - 8)}px`;
    }
    instance.panel.style.right = "auto";
    instance.panel.style.minWidth = `${minWidth}px`;
    instance.panel.style.maxWidth = `${Math.min(window.innerWidth - 16, Math.max(minWidth, rect.width + 40))}px`;
    instance.panel.style.maxHeight = `${maxHeight}px`;

    if (preferTop) {
      instance.panel.style.top = "auto";
      instance.panel.style.bottom = `${window.innerHeight - rect.top + gap}px`;
    } else {
      instance.panel.style.bottom = "auto";
      instance.panel.style.top = `${rect.bottom + gap}px`;
    }
  }

  function markActive(instance, index) {
    const options = instance.panel.querySelectorAll(".soft-select-option");
    options.forEach((el, i) => {
      el.classList.toggle("is-active", i === index);
    });
    instance.activeIndex = index;
    if (index >= 0 && options[index]) {
      options[index].scrollIntoView({ block: "nearest" });
    }
  }

  function rebuildOptions(instance) {
    const select = instance.select;
    const fragment = document.createDocumentFragment();
    const options = Array.from(select.options);
    let activeIndex = -1;
    let count = 0;

    options.forEach((option) => {
      if (option.hidden) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "soft-select-option";
      button.setAttribute("role", "option");
      button.dataset.value = option.value;
      button.dataset.index = String(option.index);

      const label = document.createElement("span");
      label.className = "soft-select-option-label";
      label.textContent = optionLabel(option) || "—";
      button.append(label);
      if (instance.isLang) {
        const mark = document.createElement("span");
        mark.className = "soft-select-option-check";
        mark.setAttribute("aria-hidden", "true");
        button.append(mark);
      }

      const disabled = option.disabled;
      if (disabled) {
        button.setAttribute("aria-disabled", "true");
        button.tabIndex = -1;
      }
      if (option.selected) {
        button.classList.add("is-selected");
        button.setAttribute("aria-selected", "true");
        activeIndex = count;
      } else {
        button.setAttribute("aria-selected", "false");
      }

      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (disabled) return;
        chooseOption(instance, option.index);
      });

      button.addEventListener("mousemove", () => {
        if (!disabled) markActive(instance, count);
      });

      fragment.appendChild(button);
      count += 1;
    });

    instance.panel.replaceChildren(fragment);
    if (!count) {
      const empty = document.createElement("div");
      empty.className = "soft-select-empty";
      empty.textContent = "—";
      instance.panel.appendChild(empty);
    }
    instance.optionCount = count;
    instance.activeIndex = activeIndex;
    setValueLabel(instance);
  }

  function chooseOption(instance, optionIndex) {
    const select = instance.select;
    if (optionIndex < 0 || optionIndex >= select.options.length) return;
    const option = select.options[optionIndex];
    if (!option || option.disabled) return;

    const previous = select.value;
    select.selectedIndex = optionIndex;
    setValueLabel(instance);
    rebuildOptions(instance);
    closePanel(instance);
    instance.trigger.focus({ preventScroll: true });

    if (select.value !== previous) {
      select.dispatchEvent(new Event("input", { bubbles: true }));
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  function openPanel(instance) {
    if (instance.select.disabled) return;
    closeAll(instance);
    rebuildOptions(instance);
    placePanel(instance);
    instance.wrap.classList.add(OPEN);
    instance.trigger.setAttribute("aria-expanded", "true");
    instance.panel.hidden = false;
    openInstance = instance;
    markActive(instance, instance.activeIndex);
  }

  function togglePanel(instance) {
    if (instance.wrap.classList.contains(OPEN)) closePanel(instance);
    else openPanel(instance);
  }

  function moveActive(instance, delta) {
    if (!instance.optionCount) return;
    let next = instance.activeIndex;
    if (next < 0) next = delta > 0 ? 0 : instance.optionCount - 1;
    else next = (next + delta + instance.optionCount) % instance.optionCount;

    const buttons = instance.panel.querySelectorAll(".soft-select-option");
    let guard = 0;
    while (buttons[next] && buttons[next].getAttribute("aria-disabled") === "true" && guard < instance.optionCount) {
      next = (next + delta + instance.optionCount) % instance.optionCount;
      guard += 1;
    }
    markActive(instance, next);
  }

  function activateCurrent(instance) {
    const buttons = instance.panel.querySelectorAll(".soft-select-option");
    const active = buttons[instance.activeIndex];
    if (!active || active.getAttribute("aria-disabled") === "true") return;
    const index = Number(active.dataset.index);
    chooseOption(instance, index);
  }

  function enhance(select) {
    if (isHiddenSelect(select) || instances.has(select)) return;
    const wrap = select.closest(".lang-select-wrap, .select-wrap");
    if (!wrap) return;

    const isLang = wrap.classList.contains("lang-select-wrap");
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "soft-select-trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");

    const ariaLabel = select.getAttribute("aria-label");
    if (ariaLabel) {
      trigger.setAttribute("aria-label", ariaLabel);
    } else if (select.id) {
      const fieldLabel = document.querySelector(`label[for="${CSS.escape(select.id)}"]`);
      if (fieldLabel) {
        const text = Array.from(fieldLabel.childNodes)
          .filter((node) => node.nodeType === Node.TEXT_NODE)
          .map((node) => node.textContent.trim())
          .join(" ")
          .trim();
        if (text) trigger.setAttribute("aria-label", text);
      }
    } else {
      const parentLabel = select.closest("label");
      if (parentLabel) {
        const text = Array.from(parentLabel.childNodes)
          .filter((node) => node.nodeType === Node.TEXT_NODE)
          .map((node) => node.textContent.trim())
          .join(" ")
          .trim();
        if (text) trigger.setAttribute("aria-label", text);
      }
    }

    const valueEl = document.createElement("span");
    valueEl.className = "soft-select-value";
    if (isLang) {
      trigger.classList.add("lang-switch-trigger");
      valueEl.className = "lang-switch-glyph";
      valueEl.setAttribute("aria-hidden", "true");
      valueEl.innerHTML = '文<span>A</span>';
      trigger.append(valueEl);
    } else {
      const chevron = document.createElement("span");
      chevron.className = "soft-select-chevron";
      chevron.setAttribute("aria-hidden", "true");
      trigger.append(valueEl, chevron);
    }

    const panel = document.createElement("div");
    panel.className = isLang ? "soft-select-panel lang-switch-panel" : "soft-select-panel";
    panel.setAttribute("role", "listbox");
    panel.hidden = true;
    if (select.id) panel.id = `${select.id}-soft-panel`;
    trigger.setAttribute("aria-controls", panel.id || "");

    wrap.classList.add("soft-select", ENHANCED);
    if (isLang) wrap.classList.add("lang-switch-menu");
    wrap.append(trigger, panel);

    const instance = {
      select,
      wrap,
      trigger,
      panel,
      valueEl,
      isLang,
      activeIndex: -1,
      optionCount: 0,
      observer: null,
    };
    instances.set(select, instance);

    const syncDisabled = () => {
      const disabled = select.disabled;
      wrap.classList.toggle("is-disabled", disabled);
      trigger.disabled = disabled;
    };

    rebuildOptions(instance);
    syncDisabled();

    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      togglePanel(instance);
    });

    trigger.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (!instance.wrap.classList.contains(OPEN)) openPanel(instance);
        else moveActive(instance, event.key === "ArrowDown" ? 1 : -1);
      } else if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (instance.wrap.classList.contains(OPEN)) activateCurrent(instance);
        else openPanel(instance);
      } else if (event.key === "Escape") {
        if (instance.wrap.classList.contains(OPEN)) {
          event.preventDefault();
          closePanel(instance);
        }
      } else if (event.key === "Home") {
        if (instance.wrap.classList.contains(OPEN)) {
          event.preventDefault();
          markActive(instance, 0);
        }
      } else if (event.key === "End") {
        if (instance.wrap.classList.contains(OPEN)) {
          event.preventDefault();
          markActive(instance, Math.max(instance.optionCount - 1, 0));
        }
      }
    });

    select.addEventListener("change", () => {
      setValueLabel(instance);
      rebuildOptions(instance);
    });

    instance.observer = new MutationObserver(() => {
      rebuildOptions(instance);
      syncDisabled();
    });
    instance.observer.observe(select, {
      attributes: true,
      attributeFilter: ["disabled"],
      childList: true,
      subtree: true,
    });
  }

  function enhanceAll(root) {
    const scope = root || document;
    scope.querySelectorAll(".lang-select-wrap > select, .select-wrap > select").forEach(enhance);
  }

  document.addEventListener("click", (event) => {
    if (!openInstance) return;
    if (openInstance.wrap.contains(event.target)) return;
    closePanel(openInstance);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && openInstance) {
      closePanel(openInstance);
    }
  });

  window.addEventListener(
    "resize",
    () => {
      if (openInstance) placePanel(openInstance);
    },
    { passive: true },
  );

  window.addEventListener(
    "scroll",
    () => {
      if (openInstance) placePanel(openInstance);
    },
    { passive: true, capture: true },
  );

  window.SoftSelect = {
    enhance,
    enhanceAll,
    refresh(select) {
      const instance = instances.get(select);
      if (!instance) return;
      rebuildOptions(instance);
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => enhanceAll(document));
  } else {
    enhanceAll(document);
  }
})();
