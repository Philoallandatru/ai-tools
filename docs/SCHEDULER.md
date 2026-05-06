# Atlassian Crawler - 定时同步服务

## 使用 uv 运行

### 1. 安装 uv（如果还没有）

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 初始化项目

```bash
# uv 会自动创建虚拟环境并安装依赖
uv sync
```

### 3. 运行方式

#### 方式 1: 使用 uv run（推荐）

```bash
# 一次性同步
uv run python scheduler.py --once

# 启动定时服务（每天 09:00 同步）
uv run python scheduler.py

# 自定义同步时间
uv run python scheduler.py --time 14:30

# 使用自定义配置文件
uv run python scheduler.py --config my-config.yaml
```

#### 方式 2: 激活虚拟环境后运行

```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# 运行
python scheduler.py
```

### 4. Windows 任务计划程序设置

#### 创建每日任务

1. 打开任务计划程序（Task Scheduler）
2. 创建基本任务
3. 配置触发器：每天，选择时间
4. 配置操作：

**程序/脚本：**
```
C:\Users\10259\.local\bin\uv.exe
```

**添加参数：**
```
run python scheduler.py --once --config C:\Users\10259\Documents\code\codex\ai-tools\config.yaml
```

**起始于：**
```
C:\Users\10259\Documents\code\codex\ai-tools
```

#### 使用 PowerShell 脚本（推荐）

创建 `run-sync.ps1`:

```powershell
# 设置工作目录
Set-Location "C:\Users\10259\Documents\code\codex\ai-tools"

# 运行同步
& "C:\Users\10259\.local\bin\uv.exe" run python scheduler.py --once

# 记录日志
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path "task-scheduler.log" -Value "$timestamp - Sync completed"
```

然后在任务计划程序中运行：
```
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\10259\Documents\code\codex\ai-tools\run-sync.ps1"
```

### 5. Linux/macOS Cron 设置

编辑 crontab:
```bash
crontab -e
```

添加：
```bash
# 每天 09:00 同步
0 9 * * * cd /path/to/ai-tools && /path/to/uv run python scheduler.py --once >> /path/to/cron.log 2>&1
```

### 6. 作为后台服务运行

#### Windows 服务（使用 NSSM）

```bash
# 下载 NSSM: https://nssm.cc/download

# 安装服务
nssm install AtlassianCrawler "C:\Users\10259\.local\bin\uv.exe" "run python scheduler.py"
nssm set AtlassianCrawler AppDirectory "C:\Users\10259\Documents\code\codex\ai-tools"
nssm set AtlassianCrawler DisplayName "Atlassian Crawler Service"
nssm set AtlassianCrawler Description "Daily sync of Jira and Confluence data"

# 启动服务
nssm start AtlassianCrawler

# 停止服务
nssm stop AtlassianCrawler

# 卸载服务
nssm remove AtlassianCrawler confirm
```

#### Linux systemd 服务

创建 `/etc/systemd/system/atlassian-crawler.service`:

```ini
[Unit]
Description=Atlassian Crawler Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/ai-tools
ExecStart=/path/to/uv run python scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable atlassian-crawler
sudo systemctl start atlassian-crawler
sudo systemctl status atlassian-crawler
```

### 7. 日志查看

```bash
# 调度器日志
tail -f scheduler.log

# 同步错误日志
tail -f sync-errors.log

# Windows 任务计划程序日志
tail -f task-scheduler.log
```

### 8. 监控和告警

#### 简单的健康检查脚本

创建 `health-check.py`:

```python
import json
from datetime import datetime, timedelta
from pathlib import Path

state_file = Path(".atlassian-sync-state.json")

if not state_file.exists():
    print("WARNING: No sync has been performed yet")
    exit(1)

with open(state_file) as f:
    state = json.load(f)

last_sync = datetime.fromisoformat(state['last_sync'].replace('Z', '+00:00'))
now = datetime.now(last_sync.tzinfo)
hours_since_sync = (now - last_sync).total_seconds() / 3600

if hours_since_sync > 25:  # 超过 25 小时未同步
    print(f"ERROR: Last sync was {hours_since_sync:.1f} hours ago")
    exit(1)
else:
    print(f"OK: Last sync was {hours_since_sync:.1f} hours ago")
    exit(0)
```

运行健康检查：
```bash
uv run python health-check.py
```

## uv 的优势

1. **快速** - 比 pip 快 10-100 倍
2. **可靠** - 锁定依赖版本，确保一致性
3. **简单** - 一个命令管理所有依赖
4. **隔离** - 自动创建和管理虚拟环境
5. **跨平台** - Windows/macOS/Linux 统一体验

## 故障排查

### 问题：uv 命令找不到
```bash
# 检查 uv 是否安装
uv --version

# 重新安装
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 问题：依赖安装失败
```bash
# 清理并重新安装
rm -rf .venv
uv sync
```

### 问题：定时任务没有运行
```bash
# 检查日志
cat scheduler.log
cat sync-errors.log

# 手动测试
uv run python scheduler.py --once
```
