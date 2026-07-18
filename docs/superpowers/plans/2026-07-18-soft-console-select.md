# Soft Console Select Styling 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将语言切换与新建任务等表单 `<select>` 统一为 Soft Console 视觉（自定义 chevron、钢青描边、信号色 focus），与整体控制台主题一致。

**架构：** 保留原生 `<select>`；在 `app.css` 中用 `appearance: none` + 统一 CSS 三角箭头（`.select-wrap` / 既有 `.lang-select-wrap`）实现 Soft Console 规格；表单 select 与 input 共享高度/边框/hover/focus；语言控件保持顶栏紧凑 ghost 变体。隐藏的 `#notification-channel-picker` 不包 wrap、不改业务。

**技术栈：** Jinja2 模板、纯 CSS（`oracle_arm_console/static/app.css`）、现有 Flask 静态资源缓存查询参数。

**规格：** `docs/superpowers/specs/2026-07-18-soft-console-select-design.md`

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `oracle_arm_console/static/app.css` | 表单 select Soft Console 规则、`.select-wrap` chevron、语言 select focus/hover 对齐 |
| `oracle_arm_console/templates/dashboard.html` | 可见表单 select 外包一层 `span.select-wrap`（6 处：5 新建任务 + 1 SMTP security） |
| `oracle_arm_console/templates/base.html` |  bump `app.css?v=` 缓存版本 |
| `oracle_arm_console/templates/_lang_switch.html` | **不改结构**（已有 wrap）；仅靠 CSS 微调 |

**不改：** `app.js` / `settings.js` / i18n 提交逻辑 / 隐藏 channel picker / 新测试文件（规格：无像素 UI 测试；跑现有 `tests/test_web.py` 防回归即可）。

**Chevron 策略（锁定）：** 表单用显式 `<span class="select-wrap">` 包住 select，避免 `label::after` 在多行 label 文本高度下定位不稳。语言继续用 `.lang-select-wrap`。

---

### 任务 1：全局表单 select + `.select-wrap` 样式

**文件：**
- 修改：`oracle_arm_console/static/app.css`（约 175–243 语言块之后可先不动；主改约 480–498 输入/select 规则区，并在其后新增 `.select-wrap`）

- [ ] **步骤 1：在全局 form 控件规则中为 `select` 关闭系统箭头并预留 chevron 内边距**

定位现有块（约 480–498 行）：

```css
input:not([type="checkbox"]):not([type="radio"]):not([type="range"]):not([type="file"]), select, textarea {
  background: #fff;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  color: var(--ink);
  min-width: 0;
  padding: 0 11px;
  transition: border-color .16s ease, box-shadow .16s ease, background .16s ease;
  width: 100%;
}
input:not([type="checkbox"]):not([type="radio"]):not([type="range"]):not([type="file"]), select { height: 42px; }
textarea { line-height: 1.55; padding-bottom: 10px; padding-top: 10px; resize: vertical; }
input:hover, select:hover, textarea:hover { border-color: #8da0aa; }
input:disabled, select:disabled, textarea:disabled, input[readonly], textarea[readonly] {
  background: #eef2f4;
  border-color: #d5dfe3;
  color: #74848d;
  cursor: not-allowed;
}
```

替换/扩展为（保留 input/textarea 行为；select 单独补强）：

```css
input:not([type="checkbox"]):not([type="radio"]):not([type="range"]):not([type="file"]), select, textarea {
  background: #fff;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  color: var(--ink);
  min-width: 0;
  padding: 0 11px;
  transition: border-color .16s ease, box-shadow .16s ease, background .16s ease;
  width: 100%;
}
input:not([type="checkbox"]):not([type="radio"]):not([type="range"]):not([type="file"]), select { height: 42px; }
select {
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;
  font-weight: 600;
  padding-right: 34px;
}
select:hover {
  background: #fbfdfe;
  border-color: #8da0aa;
}
select:focus,
select:focus-visible {
  border-color: var(--signal);
  box-shadow: 0 0 0 3px rgba(40, 127, 141, .16);
  outline: none;
}
textarea { line-height: 1.55; padding-bottom: 10px; padding-top: 10px; resize: vertical; }
input:hover, select:hover, textarea:hover { border-color: #8da0aa; }
input:disabled, select:disabled, textarea:disabled, input[readonly], textarea[readonly] {
  background: #eef2f4;
  border-color: #d5dfe3;
  color: #74848d;
  cursor: not-allowed;
}
select:disabled {
  cursor: not-allowed;
}
```

说明：
- 全局 `button, input, select…:focus-visible` 仍有 outline 规则（约 259 行）。`select:focus-visible { outline: none }` 必须写在其后或提高特异性，避免双环。若全局规则压过，在本块末尾再写一次：

```css
select:focus-visible {
  outline: none;
  outline-offset: 0;
}
```

- [ ] **步骤 2：在 form 控件规则之后新增 `.select-wrap` chevron**

紧接在上述 disabled 规则后插入：

```css
.select-wrap {
  display: block;
  position: relative;
  width: 100%;
}
.select-wrap::after {
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid var(--muted);
  content: "";
  pointer-events: none;
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-40%);
}
.select-wrap:has(select:disabled)::after {
  opacity: .46;
}
.select-wrap > select {
  width: 100%;
}
```

- [ ] **步骤 3：确认 `label` 已是 `position: relative` 的 grid（已有，无需改结构）**

现有（约 472–478）：

```css
fieldset label:not(.switch-row):not(.channel-toggle), .dialog-body label, .editor-body label {
  color: #4e606b;
  display: grid;
  font-size: 11px;
  font-weight: 600;
  gap: 7px;
  position: relative;
}
```

保持不变；chevron 挂在 `.select-wrap` 上，不挂在 `label::after`。

- [ ] **步骤 4：Commit 样式基础（可与任务 2 合并 commit；若单独提交则只 add app.css）**

```bash
git add oracle_arm_console/static/app.css
git commit -m "style: soft-console form select base and select-wrap chevron"
```

---

### 任务 2：Dashboard 可见 select 包上 `.select-wrap`

**文件：**
- 修改：`oracle_arm_console/templates/dashboard.html`（约 97–103、275 行）

- [ ] **步骤 1：包装新建任务连接/实例区 5 个 select**

将下列模式：

```html
<label>{{ t('dashboard.compartment') }}<select id="compartment-id" name="compartment_id" required>...</select></label>
```

改为：

```html
<label>{{ t('dashboard.compartment') }}<span class="select-wrap"><select id="compartment-id" name="compartment_id" required>...</select></span></label>
```

对这 5 个 id 全部套用同一包裹（保留全部属性与 option 不变）：

1. `compartment-id`
2. `availability-domain`
3. `subnet-id`
4. `image-family`
5. `image-id`

完整示例（compartment）：

```html
<label>{{ t('dashboard.compartment') }}<span class="select-wrap"><select id="compartment-id" name="compartment_id" required><option value="" selected disabled hidden>{{ t('dashboard.load_first') }}</option></select></span></label>
```

- [ ] **步骤 2：包装通知编辑器 SMTP security select（约 275 行）**

从：

```html
<label>{{ t('notify_editor.smtp_security') }}<select name="email_security">...</select></label>
```

改为：

```html
<label>{{ t('notify_editor.smtp_security') }}<span class="select-wrap"><select name="email_security">...</select></span></label>
```

- [ ] **步骤 3：确认不碰隐藏 picker**

`#notification-channel-picker` 保持：

```html
<select id="notification-channel-picker" hidden aria-hidden="true">...</select>
```

不要包 `.select-wrap`。

- [ ] **步骤 4：Commit**

```bash
git add oracle_arm_console/templates/dashboard.html
git commit -m "style: wrap dashboard form selects for soft-console chevron"
```

---

### 任务 3：语言选择与表单 focus 族对齐

**文件：**
- 修改：`oracle_arm_console/static/app.css`（约 175–243）

- [ ] **步骤 1：增强 `.lang-select` 的 transition 与 focus 环，与 form select 同族**

将现有：

```css
.lang-select {
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, .55);
  border: 1px solid var(--line-strong);
  border-radius: 9px;
  color: var(--ink);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  min-height: 34px;
  min-width: 7.5rem;
  padding: 0 28px 0 12px;
  transition: background .16s ease, border-color .16s ease, color .16s ease;
}
.lang-select:hover {
  background: #fff;
  border-color: #8fa1ab;
}
.lang-select:focus {
  outline: none;
}
.lang-select:focus-visible {
  outline: 3px solid rgba(40, 127, 141, .22);
  outline-offset: 2px;
}
```

改为：

```css
.lang-select {
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, .55);
  border: 1px solid var(--line-strong);
  border-radius: 9px;
  color: var(--ink);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  min-height: 34px;
  min-width: 7.5rem;
  padding: 0 28px 0 12px;
  transition: background .16s ease, border-color .16s ease, color .16s ease, box-shadow .16s ease;
}
.lang-select:hover {
  background: #fff;
  border-color: #8fa1ab;
}
.lang-select:focus,
.lang-select:focus-visible {
  border-color: var(--signal);
  box-shadow: 0 0 0 3px rgba(40, 127, 141, .16);
  outline: none;
}
```

保留 `.lang-select-wrap` 与 `::after` chevron（已存在，勿删）。

- [ ] **步骤 2：确保全局 form `select` 规则不冲掉语言紧凑高度**

语言 select 同时带 class `lang-select`，会命中全局 `select { height: 42px }`。必须在语言规则中显式覆盖：

```css
.lang-select {
  /* ...existing... */
  height: auto;
  min-height: 34px;
  width: auto;
  padding-right: 28px;
}
```

或更高优先级：

```css
select.lang-select {
  height: auto;
  min-height: 34px;
  width: auto;
  font-weight: 600;
}
```

推荐在现有 `.lang-select` 块内加入 `height: auto; width: auto;`，并确认 `.topbar-actions .lang-select` / `.login-panel .lang-select` 仍有效。

- [ ] **步骤 3：确认窄屏断点仍设置 min-width（约 1213、1281 行）**

现有：

```css
.topbar-actions .lang-select { min-height: 33px; min-width: 6.5rem; padding-left: 10px; padding-right: 26px; }
/* max-width: 440px */
.topbar-actions .lang-select { min-width: 5.75rem; font-size: 11px; }
```

保持；无需改断点逻辑。

- [ ] **步骤 4：Commit**

```bash
git add oracle_arm_console/static/app.css
git commit -m "style: align language select focus with soft-console form selects"
```

---

### 任务 4：缓存破坏与回归验证

**文件：**
- 修改：`oracle_arm_console/templates/base.html`（第 12 行）

- [ ] **步骤 1：Bump CSS 版本查询**

从：

```html
<link rel="stylesheet" href="{{ url_for('static', filename='app.css') }}?v=20260718-13">
```

改为（日期+序号递增即可）：

```html
<link rel="stylesheet" href="{{ url_for('static', filename='app.css') }}?v=20260718-14">
```

- [ ] **步骤 2：跑现有 web 测试（规格不要求新像素测试）**

```bash
python -m pytest tests/test_web.py -q
```

预期：全部 PASS（模板仍含必要 select name/id；仅多了 span 包裹）。

若项目用 uv：

```bash
uv run pytest tests/test_web.py -q
```

- [ ] **步骤 3：静态验收清单（手动，不测 UI 自动化；AGENT.md：不要测试 UI 界面 / 不要用内置浏览器）**

对照检查即可，**不要**启动浏览器自动化：

1. `grep` 确认 6 处 `.select-wrap` 与 0 处对 hidden picker 的 wrap：

```bash
# PowerShell
Select-String -Path oracle_arm_console/templates/dashboard.html -Pattern "select-wrap"
Select-String -Path oracle_arm_console/templates/dashboard.html -Pattern "notification-channel-picker" -Context 0,0
```

预期：`select-wrap` 出现 6 次；channel picker 行无 `select-wrap`。

2. 确认 CSS 含 `appearance: none` 与 `.select-wrap::after`：

```bash
Select-String -Path oracle_arm_console/static/app.css -Pattern "appearance:\s*none|\.select-wrap"
```

- [ ] **步骤 4：最终 commit**

```bash
git add oracle_arm_console/templates/base.html oracle_arm_console/static/app.css oracle_arm_console/templates/dashboard.html
git status
git commit -m "style: soft-console selects for language and new-task forms"
```

若前序任务已分别 commit，本步仅 commit `base.html` 版本号：

```bash
git add oracle_arm_console/templates/base.html
git commit -m "chore: bump app.css cache for soft-console select styles"
```

---

### 任务 5（可选合并）：单 commit 路径

若执行者偏好一次提交而非多次，可跳过任务 1–4 的中间 commit，在全部改完后：

```bash
git add oracle_arm_console/static/app.css oracle_arm_console/templates/dashboard.html oracle_arm_console/templates/base.html
git commit -m "style: soft-console language and form select controls

Hide system carets, add shared chevrons, align focus rings with
signal theme for language switch and new-task selects."
```

---

## 自检对照规格

| 规格项 | 对应任务 |
|--------|----------|
| Soft Console 方向 A、原生 select | 全文；无自定义 listbox |
| 表单 select 42px / 8px / 白底 / hover / signal focus | 任务 1 |
| 自定义 chevron、无双箭头 | 任务 1–2（appearance + wrap） |
| 语言紧凑 ghost + 同族 focus | 任务 3 |
| 新建任务 + SMTP 可见 select | 任务 2 |
| 隐藏 channel picker 不改 | 任务 2 步骤 3 |
| 无新 JS / 业务逻辑 | 文件列表无 JS |
| 缓存 bump | 任务 4 |
| 窄屏 min-width 保留 | 任务 3 步骤 3 |
| 无像素 UI 自动化 | 任务 4 静态 grep + pytest |

---

## 风险速查

| 风险 | 处理 |
|------|------|
| 全局 `select { height: 42px }` 撑高语言框 | `select.lang-select { height: auto; min-height: 34px; width: auto }` |
| 双 focus 环（outline + box-shadow） | select / lang-select 上 `outline: none` 覆盖全局 focus-visible |
| 双 chevron | 仅 wrap 上画箭头；select 必须 `appearance: none` |
| 长 OCI 文案 | 不设固定 select 宽；`min-width: 0` + `width: 100%` 已有 |
