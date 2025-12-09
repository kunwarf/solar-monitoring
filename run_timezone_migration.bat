@echo off
echo Database Timezone Migration Utility
echo ===================================
echo.

REM Check if database exists
if not exist "solarhub.db" (
    echo ERROR: solarhub.db not found in current directory
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

echo Database found: solarhub.db
echo.

REM Ask user for options
set /p create_backup="Create backup before migration? (y/n): "
set /p dry_run="Run in dry-run mode first? (y/n): "

echo.
echo Starting migration...
echo.

REM Run dry-run first if requested
if /i "%dry_run%"=="y" (
    echo Running dry-run first...
    python database_timezone_migration.py --dry-run --db-path solarhub.db
    echo.
    set /p continue="Continue with actual migration? (y/n): "
    if /i not "%continue%"=="y" (
        echo Migration cancelled by user
        pause
        exit /b 0
    )
)

REM Run actual migration
if /i "%create_backup%"=="y" (
    python database_timezone_migration.py --backup --db-path solarhub.db
) else (
    python database_timezone_migration.py --db-path solarhub.db
)

if %errorlevel% equ 0 (
    echo.
    echo Migration completed successfully!
) else (
    echo.
    echo Migration failed! Check the logs above for details.
)

echo.
pause