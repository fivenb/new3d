@echo off
cd /d %~dp0
start cmd /k python -m http.server 8080
timeout /t 2 /nobreak
start http://localhost:8080/bom_3d.html
pause
REM 暂停，防止窗口关闭，以便查看上述所有输出
