@echo off
chcp 65001 >nul
echo ================================================
echo   GAMEHUB PS SALON - KURULUM PROGRAMI (SETUP) URETIMI
echo ================================================
echo.
echo Bu islem BIR KEZ (her yeni surumde tekrar) yapilir, birkac dakika surer.
echo Gerekenler: Python 3.10+  ve  Inno Setup 6 (ucretsiz: jrsoftware.org/isdl.php)
echo Sonunda Output\GameHub_Kurulum_x.y.z.exe olusur: musteriye bu TEK dosyayi verin.
echo.
pause

for /f %%v in ('python -c "import re;print(re.search(r'SURUM\s*=\s*.([0-9.]+).',open('core/surum.py').read()).group(1))"') do set SURUM=%%v
echo Surum: %SURUM%

echo.
echo [1/3] Paketler kuruluyor...
python -m pip install --upgrade pip
python -m pip install PyQt6 pyinstaller
if errorlevel 1 goto hata

echo.
echo [2/3] Program klasoru olusturuluyor...
python -m PyInstaller --name "GameHub_PS_Salon" --onedir --windowed --noconfirm --clean ^
  --icon assets\icon.ico --add-data "assets;assets" main.py
if errorlevel 1 goto hata

echo.
echo [3/3] Kurulum programi (Setup) olusturuluyor...
set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe
if "%ISCC%"=="" (
  echo Inno Setup bulunamadi. Once https://jrsoftware.org/isdl.php adresinden kurun, sonra bu dosyayi tekrar calistirin.
  goto hata
)
"%ISCC%" /DSurum=%SURUM% kurulum.iss
if errorlevel 1 goto hata

echo.
echo ================================================
echo   TAMAMLANDI!  Dosyaniz: Output\GameHub_Kurulum_%SURUM%.exe
echo   Musteri bunu calistirir: Kurulum klasoru + Baslat Menusu + Masaustu
echo   kisayolu + Program Ekle/Kaldir girisi olusur. Ilk acilista lisans ister.
echo   Verileri %%APPDATA%%\GameHub klasorunde tutulur (guncelleme/kaldirmada SILINMEZ).
echo ================================================
pause
exit /b 0

:hata
echo.
echo HATA OLUSTU - yukaridaki mesaji bana iletin.
pause
exit /b 1
