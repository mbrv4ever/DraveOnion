@echo off
rem === Build-DraveOnion-EXE.bat - maak een losse EXE van de browser ===
rem  Let op: dit bundelt de hele Chromium-engine (QtWebEngine), dus de map
rem  wordt fors (~300-500 MB) en de build duurt enkele minuten. Normaal.
cd /d "%~dp0"

rem --- Python vinden ---
set "PY="
for %%V in (3.11 3.12 3.10 3.13) do (
  if not defined PY ( py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V" )
)
if not defined PY ( py -3 -c "import sys" >nul 2>&1 && set "PY=py -3" )
if not defined PY ( python -c "import sys" >nul 2>&1 && set "PY=python" )
if not defined PY ( echo Geen Python gevonden. Installeer Python 3.11 of 3.12. & pause & exit /b 1 )

rem --- benodigdheden installeren (eenmalig) ---
%PY% -c "import PyQt6.QtWebEngineWidgets" >nul 2>&1
if errorlevel 1 ( echo PyQt6 + WebEngine installeren... & %PY% -m pip install PyQt6 PyQt6-WebEngine )
%PY% -c "import cryptography" >nul 2>&1
if errorlevel 1 ( echo cryptography installeren... & %PY% -m pip install cryptography )
%PY% -c "import PIL" >nul 2>&1
if errorlevel 1 ( echo Pillow installeren ^(voor icoon^)... & %PY% -m pip install pillow )
%PY% -c "import PyInstaller" >nul 2>&1
if errorlevel 1 ( echo PyInstaller installeren... & %PY% -m pip install pyinstaller )

rem --- icoon (her)maken uit het draaklogo ---
if exist make_icon.py ( %PY% make_icon.py )

rem --- bouwen ---
rem --- draaiende instantie sluiten + oude build wissen ---
rem  (anders "WinError 5 / Toegang geweigerd": de EXE is nog in gebruik)
echo Eventueel draaiende DraveOnion/Tor sluiten...
taskkill /im DraveOnion.exe /f >nul 2>&1
powershell -NoProfile -Command "Get-Process tor -EA 0 | ? { $_.Path -like '*\DraveOnion\*' } | Stop-Process -Force" >nul 2>&1
timeout /t 2 >nul
rem  je favorieten/wachtwoorden/Tor (cache) eerst opzij zetten, anders worden ze gewist
if exist "dist\DraveOnion\cache" (
  if exist "_cache_bewaard" rmdir /s /q "_cache_bewaard"
  move "dist\DraveOnion\cache" "_cache_bewaard" >nul
)
if exist "dist\DraveOnion" rmdir /s /q "dist\DraveOnion"
if exist "build\DraveOnion" rmdir /s /q "build\DraveOnion"
if exist "dist\DraveOnion\DraveOnion.exe" (
  echo.
  echo KON DE OUDE EXE NIET VERWIJDEREN.
  echo Sluit DraveOnion ^(en sluit ook Verkenner-vensters in de dist-map^) en
  echo probeer opnieuw. Soms houdt antivirus het bestand even vast.
  pause & exit /b 1
)

echo.
echo === DraveOnion bouwen (kan een paar minuten duren) ===
%PY% -m PyInstaller --noconfirm --clean --windowed --name DraveOnion ^
  --icon "assets\icon.ico" ^
  --collect-all PyQt6 ^
  --hidden-import cryptography ^
  --collect-submodules cryptography ^
  main.py
if errorlevel 1 ( echo. & echo BOUWEN MISLUKT. Lees de melding hierboven. & pause & exit /b 1 )

rem --- assets naast de EXE zetten (icoon + logo's, app blijft portable) ---
if exist "dist\DraveOnion" (
  xcopy /e /i /y "assets" "dist\DraveOnion\assets" >nul
)
rem --- cache (favorieten/wachtwoorden/Tor) terugzetten ---
if exist "_cache_bewaard" if exist "dist\DraveOnion" move "_cache_bewaard" "dist\DraveOnion\cache" >nul

rem --- controleren of de EXE er echt is ---
if not exist "dist\DraveOnion\DraveOnion.exe" (
  echo. & echo FOUT: DraveOnion.exe niet gevonden in dist\DraveOnion. & pause & exit /b 1
)

echo.
echo === KLAAR! ===
echo De browser staat in:  "%~dp0dist\DraveOnion\DraveOnion.exe"
echo Je kunt de hele map "dist\DraveOnion" verplaatsen/kopieren; alles
echo (Tor, cache, wachtwoorden) blijft in die map staan.
echo.
pause
