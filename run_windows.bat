@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  set "PY=python"
) else (
  set "PY=py -3"
)
%PY% -c "import numpy, pygame" >nul 2>&1
if errorlevel 1 (
  echo Installing the simulation and viewer dependencies...
  %PY% -m pip install -r requirements-viewer.txt
  if errorlevel 1 (
    echo ERROR: Installation failed. Check Python 3.10+ and Internet access.
    pause
    exit /b 1
  )
)
%PY% -m biosphere view
if errorlevel 1 echo Viewer exited with an error. Review the output above.
pause
