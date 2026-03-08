@echo off
echo ============================================
echo   Building HFB.exe - Hay Day Farming Bot
echo ============================================
echo.

:: Install PyInstaller if not present
pip install pyinstaller >nul 2>&1

:: Build the exe
echo Building... This may take a few minutes.
pyinstaller hfb.spec --noconfirm

echo.
if exist "dist\HFB.exe" (
    echo ✅ Build successful! HFB.exe is at: dist\HFB.exe
) else (
    echo ❌ Build failed. Check the output above for errors.
)
echo.
pause
