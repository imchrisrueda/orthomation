@echo off
setlocal
cd /d "%~dp0\.."

set "METASHAPE_EXE=C:\Program Files\Agisoft\Metashape Pro\metashape.exe"
if not exist "%METASHAPE_EXE%" set "METASHAPE_EXE=C:\Program Files\Agisoft\Metashape\metashape.exe"

if not exist "%METASHAPE_EXE%" (
  echo ERROR: no se encontro metashape.exe.
  pause
  exit /b 1
)

set "PALMERI_CAMPAIGN=2025"
set "PALMERI_VALIDATE_MODE=pilot"
"%METASHAPE_EXE%" -r "%CD%\scripts\validate_marking.py"
pause
