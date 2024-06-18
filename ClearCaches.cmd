::::::::::::::::::::::::::::::::::::::::::::
:: Elevate.cmd - Version 4
:: Automatically check & get admin rights
:: see "https://stackoverflow.com/a/12264592/1016343" for description
::::::::::::::::::::::::::::::::::::::::::::
 @echo off
 CLS
 ECHO.
 ECHO NOTE: 
 ECHO Elevation is only needed if you need to clear the nVidia cache at
 ECHO "C:\ProgramData\NVIDIA Corporation\NV_Cache\". Otherwise, you can
 ECHO deny the script elevation permissions and it will still clear all
 ECHO other locations without issue.
 ECHO =============================
 ECHO Running Admin shell
 ECHO =============================

:init
 setlocal DisableDelayedExpansion
 set cmdInvoke=1
 set winSysFolder=System32
 set "batchPath=%~0"
 for %%k in (%0) do set batchName=%%~nk
 set "vbsGetPrivileges=%temp%\OEgetPriv_%batchName%.vbs"
 setlocal EnableDelayedExpansion

:checkPrivileges
  NET FILE 1>NUL 2>NUL
  if '%errorlevel%' == '0' ( goto gotPrivileges ) else ( goto getPrivileges )

:getPrivileges
  if '%1'=='ELEV' (echo ELEV & shift /1 & goto gotPrivileges)
  ECHO.
  ECHO **************************************
  ECHO Invoking UAC for Privilege Escalation
  ECHO **************************************

  ECHO Set UAC = CreateObject^("Shell.Application"^) > "%vbsGetPrivileges%"
  ECHO args = "ELEV " >> "%vbsGetPrivileges%"
  ECHO For Each strArg in WScript.Arguments >> "%vbsGetPrivileges%"
  ECHO args = args ^& strArg ^& " "  >> "%vbsGetPrivileges%"
  ECHO Next >> "%vbsGetPrivileges%"

  if '%cmdInvoke%'=='1' goto InvokeCmd 

  ECHO UAC.ShellExecute "!batchPath!", args, "", "runas", 1 >> "%vbsGetPrivileges%"
  goto ExecElevation

:InvokeCmd
  ECHO args = "/c """ + "!batchPath!" + """ " + args >> "%vbsGetPrivileges%"
  ECHO UAC.ShellExecute "%SystemRoot%\%winSysFolder%\cmd.exe", args, "", "runas", 1 >> "%vbsGetPrivileges%"

:ExecElevation
 "%SystemRoot%\%winSysFolder%\WScript.exe" "%vbsGetPrivileges%" %*
 exit /B

:gotPrivileges
 setlocal & cd /d %~dp0
 if '%1'=='ELEV' (del "%vbsGetPrivileges%" 1>nul 2>nul  &  shift /1)

 ::::::::::::::::::::::::::::
 ::START
 ::::::::::::::::::::::::::::
 
@echo off
echo Clearing temp files and D3D shader cache...
:: Remove the :: from the next line to also clean up your temp files location that may help with other games:
del /s /q "%localappdata%\Temp\*.* "
del /s /q "%localappdata%\D3DSCache\*.* "

echo Clearing nVidia caches...
del /s /q "%localappdata%\NVIDIA\GLCACHE\*.* "
del /s /q "%localappdata%\NVIDIA\NV_Cache\*.* "
del /s /q "%appdata%\NVIDIA\ComputeCache\*.* "
del /s /q "C:\ProgramData\NVIDIA Corporation\NV_Cache\*.* "

echo Clearing AMD caches...
del /s /q "%localappdata%\AMD\DxCache\*.* "
del /s /q "%localappdata%\AMD\DxcCache\*.* "
del /s /q "%localappdata%\AMD\Dx9Cache\*.* "

echo Clearing Star Citizen cache... keeps GraphicsSettings.json
set "scfolder=%localappdata%\Star Citizen"
md ".\_TempDir_"
robocopy "%scfolder%" "_TempDir_" /MIR /E GraphicsSettings.json
del /s /q "%localappdata%\Star Citizen\*.* "
robocopy "_TempDir_" "%scfolder%" /MIR /E GraphicsSettings.json
del /s /q ".\_TempDir_\*.*"
rd /s /q ".\_TempDir_"

exit /b
