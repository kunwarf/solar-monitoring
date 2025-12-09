#!/bin/bash

echo "Database Timezone Migration Utility"
echo "==================================="
echo

# Check if database exists
if [ ! -f "solarhub.db" ]; then
    echo "ERROR: solarhub.db not found in current directory"
    echo "Please run this script from the project root directory"
    exit 1
fi

echo "Database found: solarhub.db"
echo

# Ask user for options
read -p "Create backup before migration? (y/n): " create_backup
read -p "Run in dry-run mode first? (y/n): " dry_run

echo
echo "Starting migration..."
echo

# Run dry-run first if requested
if [[ "$dry_run" =~ ^[Yy]$ ]]; then
    echo "Running dry-run first..."
    python3 database_timezone_migration.py --dry-run --db-path solarhub.db
    echo
    read -p "Continue with actual migration? (y/n): " continue
    if [[ ! "$continue" =~ ^[Yy]$ ]]; then
        echo "Migration cancelled by user"
        exit 0
    fi
fi

# Run actual migration
if [[ "$create_backup" =~ ^[Yy]$ ]]; then
    python3 database_timezone_migration.py --backup --db-path solarhub.db
else
    python3 database_timezone_migration.py --db-path solarhub.db
fi

if [ $? -eq 0 ]; then
    echo
    echo "Migration completed successfully!"
else
    echo
    echo "Migration failed! Check the logs above for details."
    exit 1
fi

echo
