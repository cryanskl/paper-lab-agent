# Windows 部署指南

本文说明如何在 Windows 10/11 上部署并运行 `paper-lab-agent`。仓库当前支持的是单机或受信任局域网
部署：FastAPI、SQLite、APScheduler 和原生 Web 工作台都运行在 Windows 主机上；
GROBID 作为可选 Docker 服务单独运行。

> 安全边界：当前应用没有内置公网身份认证、租户隔离或 TLS 终止。不要把 8000 或 8070 端口
> 直接映射到公网。需要跨公网访问时，应先在受控反向代理、VPN 和身份认证之后部署。

## 1. 部署后会得到什么

| 组件 | 默认地址或路径 | 用途 |
| --- | --- | --- |
| 文献工作台 | `http://127.0.0.1:8000/ui/` | 日常检索、下载、阅读、问答和化学库复核 |
| FastAPI | `http://127.0.0.1:8000/` | API、OpenAPI 和工作台静态资源 |
| SQLite | `data/plasma.db` | 论文、任务和业务数据 |
| 本地文件 | `data/` | PDF、TEI、翻译、导出和向量索引 |
| GROBID | `http://127.0.0.1:8070/` | 可选；真实 PDF 结构化解析 |

`start.ps1` 是 Windows 的统一启动入口。它会按 UTF-8 读取 `.env`，创建或复用 `.venv`，安装
`requirements.txt`，释放被旧进程占用的 8000 端口，启动 FastAPI，等待 API 与内置工作台健康后
打开工作台。按 `Ctrl+C` 会进入清理流程并停止本次启动的进程。

## 2. 系统要求

推荐准备：

- 64 位 Windows 10 或 Windows 11；
- PowerShell 5.1 或 PowerShell 7；
- 64 位 Python 3.11，安装时勾选 **Add Python to PATH**；
- Git for Windows；
- Docker Desktop（仅在需要用 GROBID 解析真实 PDF 时安装）；
- 至少 10 GB 可用磁盘空间。大量 PDF、本地 embedding 模型和 Chroma 索引会继续占用空间。

在 PowerShell 中确认基础工具：

```powershell
git --version
py -3.11 --version
```

若没有 `py` 命令，也可以确认：

```powershell
python --version
```

## 3. 获取代码

在准备存放项目的目录中执行：

```powershell
git clone https://github.com/cryanskl/paper-lab-agent.git
Set-Location .\paper-lab-agent
git switch main
git pull --ff-only origin main
```

如果代码来自压缩包，解压后直接在项目根目录打开 PowerShell；目录中应能看到 `README.md`、
`requirements.txt` 和 `start.ps1`。

## 4. 配置环境

首次运行 `start.ps1` 会在 `.env` 不存在时自动复制 `.env.example`。如需在启动前配置，可手动执行：

```powershell
Copy-Item .env.example .env
notepad .env
```

本机最小配置可以保留默认值。正式使用外部能力时填写以下项目：

```dotenv
OPENALEX_API_KEY=
OPENALEX_MAILTO=
UNPAYWALL_EMAIL=
GROBID_URL=http://127.0.0.1:8070
LLM_API_KEY=
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

- `OPENALEX_API_KEY` 用于 OpenAlex 正式检索；`OPENALEX_MAILTO` 是 OpenAlex/Crossref 联系邮箱。
- `UNPAYWALL_EMAIL` 用于合法 OA 链接补全。
- `LLM_API_KEY` 未配置时，翻译只会使用本地诊断 adapter；回显原文不算有效翻译。
- API Key 只写入本机 `.env`。不要提交、截图或发送 `.env`。

默认 RAG 索引契约为：

```dotenv
EMBEDDING_MODEL=bge-m3
VECTOR_DB_BACKEND=chroma
VECTOR_DB_PATH=./data/chroma
```

这三个值必须作为一组管理。修改 embedding 模型或向量后端后，应重新索引已有文档，不能继续混用旧索引。

如果希望把数据放到其他磁盘，可使用绝对路径，例如：

```dotenv
PAPER_LAB_DATA_DIR=D:/paper-lab-data
DATABASE_PATH=D:/paper-lab-data/plasma.db
PAPER_LAB_PDF_DIR=D:/paper-lab-data/pdfs
PAPER_LAB_TEI_DIR=D:/paper-lab-data/tei
PAPER_LAB_TRANSLATION_DIR=D:/paper-lab-data/translations
PAPER_LAB_EXPORT_DIR=D:/paper-lab-data/exports
VECTOR_DB_PATH=D:/paper-lab-data/chroma
```

建议在 `.env` 中使用正斜杠，避免反斜杠转义或复制时产生歧义。数据目录必须允许当前 Windows 用户读写。

## 5. 一键启动

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

第一次启动需要创建虚拟环境并安装依赖，时间取决于网络和机器性能。成功后终端会打印 FastAPI、工作台、
日志目录和 PID 文件位置，并默认打开工作台。

如果不希望自动打开浏览器：

```powershell
$env:START_OPEN_BROWSER = 'false'
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

只验证 API 与内置工作台能否启动，ready 后立即退出并清理进程：

```powershell
$env:START_OPEN_BROWSER = 'false'
$env:DEV_EXIT_AFTER_READY = 'true'
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

这些会话级变量优先于 `.env`。关闭当前 PowerShell 后它们不会永久保留。

## 6. 启动后验证

另开一个 PowerShell 窗口，在项目根目录执行：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/v1/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8000/ui/ -UseBasicParsing
.\.venv\Scripts\python.exe scripts\health_check.py --summary-only --compact
.\.venv\Scripts\python.exe scripts\health_check.py --require-frontend
.\.venv\Scripts\python.exe scripts\health_check.py --require-openapi
```

HTTP 200 只能证明监听服务可访问；交付或演示前还应检查聚合发布状态：

```powershell
.\.venv\Scripts\python.exe scripts\health_check.py --require-release-ready
```

如需准备完整的离线演示数据：

```powershell
.\.venv\Scripts\python.exe scripts\prepare_demo_data.py --summary-only --compact
```

成功摘要应包含 `ready: true`，并显示文档已解析/索引、化学抽取完成、反应集已复核，以及 JSON、TXT、
BOLSIG 三种导出格式。

## 7. 启用 GROBID

GROBID 只在解析真实 PDF 时需要。先启动 Docker Desktop，再运行：

```powershell
docker run --rm -p 8070:8070 lfoppiano/grobid
```

保持该窗口运行，在另一个 PowerShell 中验证：

```powershell
.\.venv\Scripts\python.exe scripts\health_check.py --check-external
.\.venv\Scripts\python.exe scripts\health_check.py --require-grobid
```

GROBID 不可用时，隔离测试和 fixture 演示仍可运行，但真实 PDF 会使用有限的本地 fallback，不能把它当成
完整结构化解析结果。

## 8. 受信任局域网访问（可选）

只需要本机使用时保持 `127.0.0.1`，无需修改防火墙。需要同一受信任局域网中的其他电脑访问时，在
`.env` 中设置：

```dotenv
API_HOST=0.0.0.0
API_BASE_URL=http://127.0.0.1:8000/api/v1
```

用下面的命令查看 Windows 主机 IPv4 地址：

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' }
```

以管理员身份打开 PowerShell，并且只为 **Private** 网络配置文件放行应用端口：

```powershell
New-NetFirewallRule -DisplayName 'Paper Lab API' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -Profile Private
```

其他设备随后访问 `http://<Windows主机IP>:8000/ui/`。
不要放行 8070 给局域网客户端；应用在 Windows 主机内部访问 GROBID 即可。

## 9. 日志、停止与重启

每次启动都会创建 `logs/run-YYYYMMDD-HHMMSS/`。Windows 目录通常包含：

- `backend.log` 与 `backend.err.log`；
- `pids.env`。

正常停止请在运行 `start.ps1` 的窗口按 `Ctrl+C`。重新执行脚本时，它会检查并清理 8000 上的旧监听
进程；如果不希望影响这些端口上的其他应用，请先在 `.env` 中改用独立端口。

查看端口占用：

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

## 10. 更新与备份

更新前先停止服务，并备份 `data/` 与 `.env`。示例：

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
New-Item -ItemType Directory -Force ".\backup-$stamp" | Out-Null
Copy-Item -Recurse .\data ".\backup-$stamp\data"
Copy-Item .\.env ".\backup-$stamp\.env"
git status --short
git pull --ff-only origin main
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

如果 `git status --short` 有输出，先确认这些本地修改是否需要保留；不要用强制覆盖命令更新。备份中的
`.env` 可能包含凭据，应按敏感文件管理。

## 11. 正式交付检查

原生 PowerShell 先执行基础预检和测试：

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py --strict --compact
.\.venv\Scripts\python.exe -m pytest -q
```

仓库的完整发布门禁是 Bash 脚本。在 Windows 上可从 Git for Windows 附带的 Git Bash 执行：

```bash
bash scripts/release_check.sh
```

完整门禁还会验证文档链接、接口契约、演示数据、发布产物、实时 API、smoke 和全量测试。若本机没有可靠的
Bash 环境，应以 GitHub Actions 对同一提交的成功结果作为正式门禁证据，不要仅凭服务端口可访问就宣称
部署完成。

## 12. 常见问题

### PowerShell 禁止执行脚本

直接使用文档中的单次绕过命令，不需要永久修改系统策略：

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

### 找不到 Python

确认 Python 已加入 PATH，或在当前窗口指定解释器：

```powershell
$env:PYTHON = 'C:\Program Files\Python311\python.exe'
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

### pip 下载慢或失败

先确认 Windows 能访问 Python 包索引，再重试启动。虚拟环境已经成功创建时，脚本会复用 `.venv`，无需
手工删除。不要在来源不明的镜像中输入项目 API Key。

### 启动超时

低性能机器首次加载依赖可能超过默认等待时间：

```powershell
$env:DEV_READY_TIMEOUT = '120'
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

仍失败时检查最新 `logs/run-*/backend.err.log`。

### 端口被其他应用占用

`start.ps1` 默认会停止占用 8000 的监听进程。若该端口属于其他应用，请在 `.env` 中改为：

```dotenv
API_PORT=8001
API_BASE_URL=http://127.0.0.1:8001/api/v1
```

### 中文日志乱码

使用 `start.ps1` 启动，不要删掉它设置的 `PYTHONUTF8=1` 和 `PYTHONIOENCODING=utf-8`。同时确认 `.env`
以 UTF-8 保存。

### 外部能力显示 warning

OpenAlex、Unpaywall 和 LLM 凭据未配置时，基础本地功能仍可启动，但对应联网检索、OA 补全或真实翻译能力
不可用。用以下命令查看具体缺项：

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py --compact
.\.venv\Scripts\python.exe scripts\health_check.py --summary-only --compact
```
