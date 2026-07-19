<h1 align="center">A1 Control</h1>

<p align="center">
  <strong>用于创建 OCI Ampere A1 Always Free 实例的自托管 Web 控制台</strong>
</p>

<p align="center">
  <a href="./README.md">English</a> | 简体中文
</p>

A1 Control 可以自动发现 OCI 资源，在暂无 A1 容量时持续重试，并通过带密码保护的网页完成整个申请流程。

## 主要功能

- 自动发现隔间、可用性域、公有子网和 ARM 镜像
- 在网页中设置 A1 OCPU、内存、启动卷和 SSH 登录方式
- OCI 容量不足时自动重试
- 显示任务状态、实时日志、公网 IP 和生成的 root 密码
- 显示 Always Free 200 GB 块存储配额及剩余容量
- 可通过 Telegram、Bark、PushPlus、ServerChan、Gotify、ntfy、Webhook 或 SMTP 发送成功通知
- 登录页和顶部导航栏均可切换中文与英文

## 使用 Docker 快速部署

开始前请准备 Docker Compose，以及 OCI API 凭证（config 配置片段和对应的未加密 PEM 私钥）。

```bash
git clone https://github.com/ziboh/oracle-arm.git
cd oracle-arm
docker compose pull
docker compose up -d
```

仅本机访问时不需要创建 `.env`。打开 `http://127.0.0.1:8080`，在首次页面中设置管理密码。Session 签名密钥会自动生成并保存在持久化数据卷中。

如需从其他设备访问，请将 `.env.example` 复制为 `.env`，修改 `BIND_ADDRESS`、启用安全 Cookie，并通过 HTTPS 反向代理对外提供服务。

默认镜像为 `ghcr.io/ziboh/oracle-arm:latest`，支持 `linux/amd64` 和 `linux/arm64`。如需固定版本，可在 `.env` 中设置 `ORACLE_ARM_IMAGE`。

## 首次配置

1. 首次访问时设置管理密码；系统没有默认密码。
2. 打开 **设置**，导入 OCI config 配置片段和对应的 PEM 私钥。
3. 返回 **控制台**，选择自动发现的 OCI 资源并设置实例规格。
4. 启动任务，然后在 **日志** 页面查看进度。

首次访问时，界面会根据浏览器语言选择中文或英文。之后可随时使用登录页或顶部栏的语言菜单切换。

## 常用配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Docker Compose 对宿主机暴露的地址 |
| `WEB_SECURE_COOKIE` | `false` | 公网地址使用 HTTPS 时设为 `true` |
| `ORACLE_ARM_IMAGE` | `ghcr.io/ziboh/oracle-arm:latest` | 可选的镜像版本覆盖值 |

OCI 凭证、任务参数、重试间隔和通知渠道都在网页中设置，不再通过 `.env` 配置。

## 本地开发

推荐使用 Python 3.10+ 和 [uv](https://docs.astral.sh/uv/)：

```bash
uv sync
uv run dev
```

运行测试：

```bash
uv run pytest
```

## 安全建议

- 公网部署必须使用 HTTPS，并设置 `WEB_SECURE_COOKIE=true`。
- 不要直接向公网开放 `8080` 端口，应通过反向代理访问。
- 妥善保护数据卷，其中包含 OCI 凭证、生成的 SSH 密钥和任务数据。
- 任务日志可能包含生成的 root 密码，请严格限制控制台访问权限。

## 项目链接

[更新日志](CHANGELOG.md) · [参与贡献](CONTRIBUTING.md) · [安全策略](SECURITY.md) · [许可证](LICENSE)
