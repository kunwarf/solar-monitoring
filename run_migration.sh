#!/bin/bash

# Solar Monitoring System - Database Migration Runner
# This script runs the database migration for new features

echo "=== Solar Monitoring System Database Migration ==="
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "database_migration_v2.py" ]; then
    echo "❌ database_migration_v2.py not found in current directory"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Make the migration script executable
chmod +x database_migration_v2.py

echo "🚀 Starting database migration..."
echo

# Run the migration
python3 database_migration_v2.py

# Check exit code
if [ $? -eq 0 ]; then
    echo
    echo "✅ Migration completed successfully!"
    echo
    echo "New features now available:"
    echo "  - Settings/Configuration management"
    echo "  - Energy Calculator with hourly energy data"
    echo "  - Enhanced API endpoints"
    echo "  - Inverter sensor management"
    echo "  - System logging"
    echo
    echo "You can now restart the application to use the new features."
else
    echo
    echo "❌ Migration failed!"
    echo "Check the logs above for details."
    echo "A database backup was created before the migration attempt."
    exit 1
fi
