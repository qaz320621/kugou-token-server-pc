# 安装开机自启（可选，非默认！你主动运行本脚本才会安装）
# 作用：登录 Windows 后在后台静默启动酷狗 Token 服务
# 用法：右键 -> 使用 PowerShell 运行（或以管理员运行）
$ErrorActionPreference = 'Stop'
$taskName = 'KugouTokenServer'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $dir 'token_server.py'
$pyw = 'D:\SoftWare\Directory\miniforge3\pythonw.exe'

if (-not (Test-Path $pyw)) {
    Write-Host "找不到 pythonw: $pyw，请修改本脚本中的路径" -ForegroundColor Red
    exit 1
}

# 创建登录时启动的计划任务（无窗口，后台运行）
schtasks /Create /TN $taskName /TR "`"$pyw`" `"$script`"" /SC ONLOGON /RL LIMITED /F | Out-Null

Write-Host "✅ 已安装开机自启（登录 Windows 后自动后台运行 Token 服务）" -ForegroundColor Green
Write-Host "   任务名: $taskName"
Write-Host "   如需取消，请运行: 卸载开机自启.ps1"
