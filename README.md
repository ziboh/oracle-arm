# A1 Control

当前版本：`1.0.0`。A1 Control 以 MIT 许可证发布，欢迎通过 Pull Request 贡献代码。

A1 Control 是一个自托管的 OCI Ampere A1 抢注控制台。它通过 OCI API 自动读取区间、可用域、公共子网和 ARM 镜像，容量不足时持续尝试创建实例，并通过受密码保护的网页展示任务状态和实时日志。

## 功能

- 密码登录、CSRF 防护和登录失败限速
- 自动读取 OCI 区间、可用域、公共子网和 A1 镜像
- 统计现有启动盘和块存储，显示 Always Free 200 GB 额度的已用与可用空间
- 网页导入 OCI 配置片段和 PEM 私钥，适合全新 Docker 容器
- 网页选择实例配置，无需 Terraform 或 `main.tf`
- 单任务启动、停止和实时日志
- 托管单套 OCI 凭据与重试间隔设置
- 可选 Telegram、Bark、Webhook 和 SMTP 邮箱成功通知
- 实例创建后显示公网 IP 和随机 root 密码
- Waitress WSGI 服务，支持反向代理部署

## 项目结构

```text
oracle-arm/
├── oracle_arm_console/
│   ├── __main__.py        # 服务入口
│   ├── cli.py             # 抢注子进程入口
│   ├── jobs.py            # 任务生命周期和日志
│   ├── provisioner.py     # OCI 实例创建
│   ├── settings.py        # 参数模型和校验
│   ├── instance.py        # 实例参数模型和校验
│   ├── oci_resources.py   # OCI 资源发现
│   ├── web.py             # Web 应用和鉴权
│   ├── static/
│   └── templates/
├── tests/
├── .env.example
└── pyproject.toml
```

## 本地运行

需要 Python 3.10 或更高版本和 OCI API 配置。实例登录使用的 Ed25519 SSH 密钥由控制台自动生成。

### 1. OCI API 认证

在 OCI 控制台为用户创建 API Key 后，需要保留：

- OCI 提供的配置文件片段
- 创建 API Key 时下载的私有密钥

将配置保存到 `~/.oci/config`，并把 `key_file` 修改为私有密钥的真实路径：

```ini
[DEFAULT]
user=ocid1.user.oc1..example
fingerprint=00:00:00:00:00:00:00:00
tenancy=ocid1.tenancy.oc1..example
region=ap-tokyo-1
key_file=C:\Users\your-name\.oci\oci_api_key.pem
```

私有密钥只用于 OCI API 认证，不会通过网页上传。

### 2. 实例登录密钥

读取 OCI 资源后，可以选择两种方式：自动生成一对 Ed25519 SSH 密钥，或上传已有的 `.pub` 公钥文件。自动生成模式必须下载并保存私钥后才能启动创建任务；上传模式只接收公钥，不需要也不允许上传 SSH 私钥。实例登录私钥不会写入任务日志，与 OCI API 的 PEM 私钥不是同一个文件。

准备完成后启动服务：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

export WEB_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export WEB_HOST=0.0.0.0
oracle-arm-console
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .

$env:WEB_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
oracle-arm-console
```

默认访问地址为 `http://127.0.0.1:8080`。

首次启动时默认管理密码为 `admin`。登录后打开顶部“设置”修改密码；新密码以哈希形式保存在 `data/security.json`。正式部署前必须修改默认密码。

登录后：

1. 确认本地 OCI 配置文件和环境变量中的 Profile。
2. 点击“读取 OCI 资源”。
3. 选择实例区间、可用域、公共子网和 ARM 系统镜像。
4. 确认实例名称、免费规格和 SSH 公钥。
5. 点击“开始等待容量”。

控制台按当前 Always Free A1 总额度限制实例规格为最多 2 OCPU 和 12 GB 内存，启动盘范围为 50 到 200 GB。

## Docker 部署

项目依赖中的 `oci` 是 Oracle 官方 Python SDK 包，不是 OCI CLI 命令行程序。Docker 镜像会通过 `pip` 自动安装该包，不需要额外安装 OCI CLI。

在 B 服务器安装 Docker 和 Docker Compose，然后进入项目目录运行：

```bash
docker compose up -d --build
```

生产部署建议先复制 `.env.example` 为 `.env`，至少修改 `WEB_PASSWORD`、`WEB_SECRET_KEY`，并保持 `BIND_ADDRESS=127.0.0.1`。应用容器以非 root 用户运行，运行数据保存在 Docker 命名卷中。

从 Docker Hub 使用已发布镜像时，将 `compose.yaml` 中的 `build: .` 替换为镜像地址，例如 `image: <dockerhub-user>/oracle-arm-console:1.0.0`，然后运行 `docker compose pull && docker compose up -d`。

默认只监听 B 服务器的 `127.0.0.1:8080`。在本机建立 SSH 隧道：

```bash
ssh -L 8080:127.0.0.1:8080 ubuntu@B服务器IP
```

然后访问 `http://127.0.0.1:8080`，首次登录密码为 `admin`。进入后按以下顺序操作：

1. 在右上角“设置”中修改管理密码。
2. 点击“导入 OCI 凭据”。
3. 粘贴 OCI 控制台提供的多行配置文件片段。
4. 上传创建 API Key 时下载的 `.pem` 私钥。
5. 保存后，程序会自动识别配置片段中的唯一 Profile 并读取 OCI 资源。

已有凭据时，页面会显示“替换 OCI 凭据”。OCI 私钥不会回显，因此替换时需要重新提交完整配置片段和配套私钥；程序不会追加多个账户或 Profile。

程序会校验 PEM 私钥与配置中的 fingerprint 是否匹配，并将 `key_file` 自动改写为容器内路径。以下文件保存在 Docker 命名卷 `oracle-arm-data` 中：

```text
/data/security.json       管理密码哈希
/data/oci/config          OCI SDK 配置
/data/oci/oci_api_key.pem OCI API 私钥
/data/ssh-keys/*.key      自动生成的实例登录私钥
```

更新容器不会删除这些数据。要查看状态和日志：

```bash
docker compose ps
docker compose logs -f
```

公网部署时必须配置 HTTPS 反向代理，并将 `WEB_SECURE_COOKIE=true`。不要直接把 8080 端口暴露到公网。

## 配置

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `WEB_PASSWORD` | `admin` | 尚未保存自定义密码时使用的初始密码 |
| `SECURITY_FILE` | `data/security.json` | 管理密码哈希的持久化文件 |
| `OCI_DATA_DIR` | `data/oci` | 网页导入的 OCI 配置与私钥保存目录 |
| `SSH_KEY_DIR` | `data/ssh-keys` | 自动生成的实例登录私钥保存目录 |
| `WEB_SECRET_KEY` | 启动时随机生成 | 建议设置固定长随机值 |
| `WEB_HOST` | `127.0.0.1` | 监听地址 |
| `WEB_PORT` | `8080` | 监听端口 |
| `WEB_THREADS` | `4` | WSGI 工作线程数 |
| `WEB_SECURE_COOKIE` | `false` | HTTPS 部署时设为 `true` |
| `OCI_CONFIG_FILE` | `~/.oci/config` | OCI 配置文件路径 |
| `OCI_PROFILE` | `DEFAULT` | OCI Profile |
| `RETRY_INTERVAL` | `10` | 初始重试间隔，单位秒 |
| `TELEGRAM_ENABLED` | `false` | 启用 Telegram 通知 |
| `TELEGRAM_TOKEN` | 空 | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | 空 | Telegram 会话 ID |
| `TELEGRAM_API_HOST` | `api.telegram.org` | Telegram API 主机名，不含协议和路径 |
| `BARK_ENABLED` | `false` | 启用 Bark 通知 |
| `BARK_SERVER` | `https://api.day.app` | Bark 官方或自建服务地址 |
| `BARK_DEVICE_KEY` | 空 | Bark 设备密钥 |
| `WEBHOOK_ENABLED` | `false` | 启用 Webhook 通知 |
| `WEBHOOK_PROVIDER` | `generic` | `feishu`、`dingtalk`、`wecom`、`discord`、`slack` 或 `generic` |
| `WEBHOOK_URL` | 空 | 对应平台的机器人或 Incoming Webhook 地址 |
| `EMAIL_ENABLED` | `false` | 启用 SMTP 邮箱通知 |
| `EMAIL_SMTP_HOST` | `smtp.example.com` | SMTP 服务器地址 |
| `EMAIL_SMTP_PORT` | `587` | SMTP 端口 |
| `EMAIL_SECURITY` | `starttls` | `starttls`、`ssl` 或 `none` |
| `EMAIL_USERNAME` | 空 | SMTP 账号 |
| `EMAIL_PASSWORD` | 空 | SMTP 密码或邮箱授权码 |
| `EMAIL_FROM` | 空 | 发件人地址 |
| `EMAIL_TO` | 空 | 收件人地址 |

通知参数可以在网页中按任务填写，也可以用 `.env.example` 中对应的环境变量设置默认值。环境变量中的 Token、设备密钥、Webhook 地址和邮箱密码不会回显到页面；保持输入框为空即可继续使用环境变量配置。QQ、163 等邮箱通常需要使用授权码。

Webhook 会按所选平台生成兼容的文本消息。通用 JSON 格式发送 `{"title": "A1 Control", "message": "..."}`。通知渠道互相独立，发送失败只会记录到任务日志，不会把已经创建成功的实例标记为失败。

## 测试

```bash
pip install -e ".[dev]"
pytest
```

CI 会在 Python 3.10、3.11 和 3.12 上运行测试，并验证 Docker 镜像可以构建。

## 开源协作

- [贡献指南](CONTRIBUTING.md)
- [安全策略](SECURITY.md)
- [行为准则](CODE_OF_CONDUCT.md)
- [变更记录](CHANGELOG.md)
- [许可证](LICENSE)

## 安全建议

- 公网部署时使用 HTTPS 反向代理，并设置 `WEB_SECURE_COOKIE=true`。
- 只开放反向代理端口，不直接暴露应用端口。
- OCI 私钥和配置文件不要放入项目目录或提交到版本控制。
- 页面日志包含实例 root 密码，应限制控制台访问范围。
