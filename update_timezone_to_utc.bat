@echo off
echo Updating timezone from Asia/Karachi to UTC...
echo This will update all existing records to use UTC timezone.
echo A backup will be created before making any changes.
echo.

python update_timezone_to_utc.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Timezone update completed successfully!
    echo All records now use UTC timezone.
) else (
    echo.
    echo Update failed! Check the error messages above.
)

pause
