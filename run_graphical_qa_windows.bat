@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (set "PY=python") else (set "PY=py -3")
%PY% -c "import numpy, pygame" >nul 2>&1
if errorlevel 1 (
  echo Installing required Pygame and NumPy dependencies...
  %PY% -m pip install -r requirements-viewer.txt
  if errorlevel 1 (
    echo ERROR: Could not install dependencies.
    pause
    exit /b 1
  )
)
echo Running actual SDL/Pygame visual and input smoke tests...
%PY% tools\run_graphical_qa.py
if errorlevel 1 (
  echo One or more graphical QA checks failed. See results\qa_windows\summary.json.
) else (
  echo All automated Pygame checks passed. Screenshots: results\qa_windows\
)
echo NOTE: These tests do not replace manually playing with the window.
pause
