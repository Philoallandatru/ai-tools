# 快速开始 - 使用 uv 设置定时同步

## 1. 安装 uv

### Windows (PowerShell)
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 2. 初始化项目

```bash
cd C:\Users\10259\Documents\code\codex\ai-tools

# uv 会自动创建虚拟环境并安装所有依赖
uv sync
```

## 3. 测试运行

```bash
# 测试一次性同步
uv run python scheduler.py --once

# 测试健康检查
uv run python health-check.py
```

## 4. 设置 Windows 定时任务

### 方法 A: 使用 PowerShell 脚本（推荐）

1. 确保 `run-sync.ps1` 已创建
2. 打开任务计划程序（Task Scheduler）
3. 创建基本任务：
   - 名称：`Atlassian Daily Sync`
   - 触发器：每天 09:00
   - 操作：启动程序
     - 程序：`powershell.exe`
     - 参数：`-ExecutionPolicy Bypass -File "C:\Users\10259\Documents\code\codex\ai-tools\run-sync.ps1"`
     - 起始于：`C:\Users\10259\Documents\code\codex\ai-tools`

### 方法 B: 直接使用 uv（更简单）

1. 打开任务计划程序
2. 创建基本任务：
   - 名称：`Atlassian Daily Sync`
   - 触发器：每天 09:00
   - 操作：启动程序
     - 程序：`C:\Users\10259\.local\bin\uv.exe`
     - 参数：`run python scheduler.py --once`
     - 起始于：`C:\Users\10259\Documents\code\codex\ai-tools`

## 5. 验证设置

```bash
# 查看同步状态
uv run python cli.py status

# 查看健康状态
uv run python health-check.py

# 查看日志
cat scheduler.log
cat task-scheduler.log
```

## 6. 常用命令

```bash
# 手动触发同步
uv run python scheduler.py --once

# 自定义同步时间（作为服务运行）
uv run python scheduler.py --time 14:30

# 使用自定义配置
uv run python scheduler.py --once --config my-config.yaml

# 健康检查（可用于监控）
uv run python health-check.py --max-hours 25
```

## 7. 故障排查

### uv 命令找不到
```bash
# 检查安装
where uv

# 重新安装
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 依赖问题
```bash
# 清理并重新安装
rm -rf .venv
uv sync
```

### 查看详细日志
```bash
# 同步日志
cat sync-errors.log

# 调度器日志
cat scheduler.log

# Windows 任务日志
cat task-scheduler.log
```

## uv 的优势

✓ **快速** - 比 pip 快 10-100 倍  
✓ **可靠** - 自动锁定依赖版本  
✓ **简单** - 一个命令管理所有依赖  
✓ **隔离** - 自动创建虚拟环境  
✓ **跨平台** - Windows/macOS/Linux 统一

## 下一步

- 查看 [SCHEDULER.md](SCHEDULER.md) 了解更多高级配置
- 查看 [USAGE.md](USAGE.md) 了解详细使用说明
- 配置监控和告警（可选）
