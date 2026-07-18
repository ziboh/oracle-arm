# A1 Control

[English](README.md)

当前版本：`1.1.0`。A1 Control 使用 MIT 许可证发布。

A1 Control 是自托管 Web 控制台，用于申请 **OCI Ampere A1**（Always Free）实例。通过 OCI API 自动加载隔间、可用性域、公有子网与 ARM 镜像；容量不足时自动重试；在密码认证后提供任务状态与实时日志。

## 功能

- 密码登录、CSRF 防护、登录限流
- 自动发现 OCI 隔间、可用性域、公有子网与 A1 镜像
- Always Free 200 GB 块存储用量与剩余配额
- 浏览器内导入 OCI 配置片段 + PEM 私钥（适合 Docker）
- 在界面中配置实例规格，无需 Terraform / `main.tf`
- 单任务启停与实时日志
- 可选成功通知（Telegram、Bark、PushPlus、ServerChan、Gotify、ntfy、Webhook、SMTP）
- 创建成功后展示公网 IP 与随机 root 密码
- Waitress WSGI，便于反向代理部署
- **基于文件的多语言**（默认英文；浏览器语言为中文时使用中文）

## 项目结构

```text
oracle-arm/
├── oracle_arm_console/
│   ├── __main__.py        # 生产入口
│   ├── dev.py             # uv run dev / 调试服务
│   ├── cli.py             # worker 子进程
│   ├── jobs.py            # 任务生命周期与日志
│   ├── provisioner.py     # OCI 实例创建
│   ├── settings.py        # 设置模型与校验
│   ├── instance.py        # 实例表单模型
│   ├── oci_resources.py   # OCI 资源发现
│   ├── i18n.py            # 语言加载
│   ├── locales/           # 每种语言一个 JSON
│   ├── web.py             # Flask 应用与认证
│   ├── static/
│   └── templates/
├── tests/
├── .env.example
└── pyproject.toml
```

## 本地开发

需要 Python 3.10+ 与 OCI API 凭证。实例登录用的 Ed25519 密钥可由控制台生成。

### 安装与运行（uv）

```bash
uv sync
uv run dev
```

浏览器打开 `http://127.0.0.1:8080`。默认管理密码为 `admin`，请在 **设置** 中尽快修改。

类生产安装：

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -e .

export WEB_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export WEB_HOST=0.0.0.0
oracle-arm-console
```

### OCI API 凭证

在 OCI 控制台创建 API 密钥并妥善保存：

- 多行 config 配置片段
- 创建时下载的未加密 PEM 私钥

可放在宿主机 `~/.oci/`，也可登录后在控制台 / 设置页导入。

### 语言支持

界面文案按语言分文件存放：

```text
oracle_arm_console/locales/
  en.json   # 英文（默认）
  zh.json   # 中文
```

选择顺序：

1. 手动切换：语言下拉框 → `GET /locale?lang=en|zh`（写入长期 `lang` Cookie 后跳回原页）
2. 已有 `lang` Cookie（你上次的选择）
3. `Accept-Language` — **仅首次访问**（尚无 Cookie）时使用，解析后会立刻写入 Cookie
4. 回退：**英文**

因此浏览器语言只决定第一次打开时的默认界面；之后以登录页 / 顶栏的语言下拉框为准，直到清除 Cookie。也可临时打开 `/?lang=en` 强制一次。

中文浏览器环境（`zh`、`zh-CN` 等）会解析为 `zh`。其他语言在未添加对应 JSON 时保持英文。

**新增语言：** 将 `en.json` 复制为例如 `fr.json`，翻译 value 后重启进程。登录页与顶栏的语言下拉框会自动出现新选项。

登录页或登录后顶栏使用 **语言** 下拉框即可切换。

## Docker

```bash
docker compose up -d --build
```

生产环境请复制 `.env.example` 为 `.env`，至少设置 `WEB_PASSWORD`、`WEB_SECRET_KEY`，并保持 `BIND_ADDRESS=127.0.0.1`（除非已在反向代理终止 TLS）。

## 配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `WEB_PASSWORD` | `admin` | 自定义哈希保存前的初始密码 |
| `WEB_SECRET_KEY` | 每次启动随机 | 请持久化为足够长的随机值 |
| `WEB_HOST` / `WEB_PORT` | `127.0.0.1` / `8080` | 监听地址 |
| `WEB_SECURE_COOKIE` | `false` | HTTPS 后设为 `true` |
| `OCI_DATA_DIR` | `data/oci` | 导入的 OCI 配置与 PEM |
| `SSH_KEY_DIR` | `data/ssh-keys` | 生成的实例私钥 |
| `RETRY_INTERVAL` | `10` | 初始重试间隔（秒） |

通知相关默认值可通过环境变量（见 `.env.example`）或任务界面单独配置。

## 测试

```bash
pip install -e ".[dev]"
pytest
# 或
uv run pytest
```

## 安全

- 公网部署请使用 HTTPS，并设置 `WEB_SECURE_COOKIE=true`
- 不要将应用端口直接暴露到公网
- OCI 私钥仅保存在服务器；界面不会回显私钥内容
- 运行日志可能包含实例 root 密码 — 请限制控制台访问权限

## 参与贡献

- [贡献指南](CONTRIBUTING.md)
- [安全策略](SECURITY.md)
- [行为准则](CODE_OF_CONDUCT.md)
- [更新日志](CHANGELOG.md)
- [许可证](LICENSE)
