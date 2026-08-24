@echo off
chcp 65001 >nul
echo ============================================
echo   酷狗插件 Token 管理服务
echo   启动后请用浏览器打开 http://127.0.0.1:8765/
echo   关闭本窗口即停止服务
echo ============================================
"D:\SoftWare\Directory\miniforge3\python.exe" "%~dp0token_server.py"
pause
