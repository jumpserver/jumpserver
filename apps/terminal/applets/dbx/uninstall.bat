@echo off
setlocal

set "APP_DIR=%DBX_HOME%"
if not defined DBX_HOME set "APP_DIR=%ProgramFiles%\DBX"

taskkill /f /im DBX.exe >nul 2>&1

if exist "%APP_DIR%" rmdir /s /q "%APP_DIR%"
if defined DBX_DRIVERS_HOME if exist "%DBX_DRIVERS_HOME%" rmdir /s /q "%DBX_DRIVERS_HOME%"

endlocal
rem 目录不存在也算卸载成功，否则重复卸载会让部署任务失败
exit /b 0
