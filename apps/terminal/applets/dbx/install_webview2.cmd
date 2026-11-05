@echo off
rem DBX needs the Microsoft Edge WebView2 Runtime, which Windows Server does not ship with.
rem Like the official DBX offline installer, always run the bundled installer so that a
rem missing or outdated runtime is installed without network access. The installer exits
rem non-zero in cases such as a newer runtime already being present or a policy blocking
rem it, so the result is judged by a machine-wide runtime being registered afterwards.
rem
rem Tinker runs this from a service without a console and fails the install as soon as
rem anything is written to stdout or stderr, so all output goes to the log file and only
rem a failure is reported, in a single write.
setlocal

set "WEBVIEW2_HOME=C:\Program Files\DBX\webview2"
set "INSTALLER=%WEBVIEW2_HOME%\MicrosoftEdgeWebView2RuntimeInstaller.exe"
set "INSTALL_LOG=%WEBVIEW2_HOME%\install.log"
set "RUNTIME_KEY=HKLM\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"

if not exist "%WEBVIEW2_HOME%\" mkdir "%WEBVIEW2_HOME%" >nul 2>&1
>"%INSTALL_LOG%" 2>&1 echo %DATE% %TIME% install the Microsoft Edge WebView2 Runtime
if not exist "%INSTALLER%" >>"%INSTALL_LOG%" 2>&1 echo installer not found: %INSTALLER%
if exist "%INSTALLER%" "%INSTALLER%" /silent /install <nul >>"%INSTALL_LOG%" 2>&1
if exist "%INSTALLER%" >>"%INSTALL_LOG%" 2>&1 echo installer exit code: %ERRORLEVEL%

set "RUNTIME_VERSION="
for /f "tokens=3" %%v in ('reg query "%RUNTIME_KEY%" /v pv /reg:32 2^>nul ^| findstr /i "REG_SZ" 2^>nul') do set "RUNTIME_VERSION=%%v"
if not defined RUNTIME_VERSION set "RUNTIME_VERSION=0.0.0.0"
>>"%INSTALL_LOG%" 2>&1 echo registered runtime: %RUNTIME_VERSION%
if not "%RUNTIME_VERSION%"=="0.0.0.0" exit /b 0

<nul set /p "=Microsoft Edge WebView2 Runtime is not installed, see %INSTALL_LOG%"
exit /b 1
