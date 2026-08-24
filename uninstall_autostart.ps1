# 卸载开机自启（取消登录自启，不影响当前运行的服务）
$ErrorActionPreference = 'Stop'
$taskName = 'KugouTokenServer'
schtasks /Delete /TN $taskName /F 2>$null | Out-Null
Write-Host "✅ 已取消开机自启（当前已运行的服务不受影响）" -ForegroundColor Green
