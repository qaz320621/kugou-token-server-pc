@echo off
chcp 65001 >nul
rem ============================================
rem  酷狗 Token 服务（静默运行）
rem  无窗口后台运行；启动后自动打开管理网页
rem  注意：这只是"启动本次"，不是开机自启。
rem ============================================
start "" "D:\SoftWare\Directory\miniforge3\pythonw.exe" "%~dp0token_server.py"
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8765/
echo 服务已后台启动（无窗口）。
echo 管理网页已打开：http://127.0.0.1:8765/
echo.
echo 如需开机自启，请运行：安装开机自启.ps1（可选，默认不安装）
pause
