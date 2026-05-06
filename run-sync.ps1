# 设置工作目录
Set-Location "C:\Users\10259\Documents\code\codex\ai-tools"

# 记录开始时间
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Output "$timestamp - Starting sync..." | Out-File -Append -FilePath "task-scheduler.log"

# 运行同步
try {
    & "C:\Users\10259\.local\bin\uv.exe" run python scheduler.py --once
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Output "$timestamp - Sync completed successfully" | Out-File -Append -FilePath "task-scheduler.log"
} catch {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Output "$timestamp - Sync failed: $_" | Out-File -Append -FilePath "task-scheduler.log"
    exit 1
}
