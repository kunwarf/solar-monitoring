@echo off
REM Solar Monitoring System - Database Migration Runner (Windows)
REM This script runs the database migration for new features

echo === Solar Monitoring System Database Migration ===
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3 and add it to your PATH
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "database_migration_v2.py" (
    echo ❌ database_migration_v2.py not found in current directory
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

echo 🚀 Starting database migration...
echo.

REM Run the migration
python database_migration_v2.py

REM Check exit code
if errorlevel 1 (
    echo.
    echo ❌ Migration failed!
    echo Check the logs above for details.
    echo A database backup was created before the migration attempt.
    pause
    exit /b 1
) else (
    echo.
    echo ✅ Migration completed successfully!
    echo.
    echo New features now available:
    echo   - Settings/Configuration management
    echo   - Energy Calculator with hourly energy data
    echo   - Enhanced API endpoints
    echo   - Inverter sensor management
    echo   - System logging
    echo.
    echo You can now restart the application to use the new features.
    pause
)
