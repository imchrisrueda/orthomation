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

echo Procesara los vuelos restantes de 2026. Continuar solo tras validar el piloto.
pause

set "PALMERI_CAMPAIGN=2026"
set "PALMERI_MODE=remaining"
set "PALMERI_OVERWRITE=0"
"%METASHAPE_EXE%" -r "%CD%\scripts\palmeri_pipeline.py"
pause
