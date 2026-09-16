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

set /p PALMERI_CAMPAIGN=Campaign ID (ej. 2025, 2026):
echo.
echo 1 = inventory
echo 2 = pilot
echo 3 = validate pilot
echo 4 = remaining
echo 5 = validate all
set /p ACTION=Accion:

if "%ACTION%"=="1" (
  set "PALMERI_MODE=inventory"
  set "PALMERI_OVERWRITE=0"
  "%METASHAPE_EXE%" -r "%CD%\scripts\palmeri_pipeline.py"
)
if "%ACTION%"=="2" (
  set "PALMERI_MODE=pilot"
  set "PALMERI_OVERWRITE=0"
  "%METASHAPE_EXE%" -r "%CD%\scripts\palmeri_pipeline.py"
)
if "%ACTION%"=="3" (
  set "PALMERI_VALIDATE_MODE=pilot"
  "%METASHAPE_EXE%" -r "%CD%\scripts\validate_marking.py"
)
if "%ACTION%"=="4" (
  set "PALMERI_MODE=remaining"
  set "PALMERI_OVERWRITE=0"
  "%METASHAPE_EXE%" -r "%CD%\scripts\palmeri_pipeline.py"
)
if "%ACTION%"=="5" (
  set "PALMERI_VALIDATE_MODE=all"
  "%METASHAPE_EXE%" -r "%CD%\scripts\validate_marking.py"
)
pause
