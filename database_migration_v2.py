#!/usr/bin/env python3
"""
Database Migration Script v2.0
Solar Monitoring System

This script handles database schema updates for new features:
- Settings/Configuration management
- Energy Calculator with hourly_energy table
- Enhanced API endpoints
- Inverter sensor management

Run this script after updating the application to ensure database compatibility.
"""

import sqlite3
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

def find_database_path():
    """Find the database file path."""
    possible_paths = [
        os.path.expanduser("~/.solarhub/solarhub.db"),
        os.path.join(os.getcwd(), "solarhub.db"),
        os.path.join(os.getcwd(), "data", "solarhub.db"),
        "/opt/solar-monitoring/solarhub.db"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            log.info(f"Found database at: {path}")
            return path
    
    # If not found, use default location
    default_path = os.path.expanduser("~/.solarhub/solarhub.db")
    os.makedirs(os.path.dirname(default_path), exist_ok=True)
    log.info(f"Using default database path: {default_path}")
    return default_path

def backup_database(db_path: str) -> str:
    """Create a backup of the database before migration."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        log.info(f"Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        log.error(f"Failed to backup database: {e}")
        raise

def migrate_database(db_path: str) -> bool:
    """
    Perform database migration to v2.0.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        True if successful, False otherwise
    """
    log.info(f"Starting database migration v2.0 for: {db_path}")
    
    if not os.path.exists(db_path):
        log.error(f"Database file not found: {db_path}")
        return False
    
    # Create backup
    backup_path = backup_database(db_path)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # 1. Ensure energy_samples table has all required columns
        log.info("Checking energy_samples table schema...")
        cursor.execute("PRAGMA table_info(energy_samples)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = {
            'inverter_mode': 'TEXT',
            'inverter_temp_c': 'REAL',
            'grid_import_wh': 'REAL',
            'grid_export_wh': 'REAL'
        }
        
        for column, column_type in required_columns.items():
            if column not in columns:
                try:
                    cursor.execute(f"ALTER TABLE energy_samples ADD COLUMN {column} {column_type}")
                    log.info(f"Added column {column} to energy_samples table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        log.debug(f"Column {column} already exists")
                    else:
                        log.warning(f"Failed to add column {column}: {e}")
        
        # 2. Create/verify configuration table for settings management
        log.info("Creating/verifying configuration table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuration (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'api'
            )
        """)
        
        # Add index for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_config_source 
            ON configuration(source)
        """)
        
        # 3. Create hourly_energy table for Energy Calculator
        log.info("Creating/verifying hourly_energy table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hourly_energy (
                inverter_id TEXT NOT NULL,
                date TEXT NOT NULL,
                hour_start INTEGER NOT NULL,
                -- Energy data in kWh
                solar_energy_kwh REAL,
                load_energy_kwh REAL,
                battery_charge_energy_kwh REAL,
                battery_discharge_energy_kwh REAL,
                grid_import_energy_kwh REAL,
                grid_export_energy_kwh REAL,
                -- Power data in watts (for reference)
                avg_solar_power_w REAL,
                avg_load_power_w REAL,
                avg_battery_power_w REAL,
                avg_grid_power_w REAL,
                -- Metadata
                sample_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (inverter_id, date, hour_start)
            )
        """)
        
        # Add indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hourly_energy_inverter_date 
            ON hourly_energy(inverter_id, date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hourly_energy_date_hour 
            ON hourly_energy(date, hour_start)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hourly_energy_inverter_id 
            ON hourly_energy(inverter_id)
        """)
        
        # 4. Create/verify pv_daily table (if not exists)
        log.info("Creating/verifying pv_daily table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pv_daily (
                day TEXT NOT NULL,
                inverter_id TEXT NOT NULL,
                pv_kwh REAL NOT NULL,
                PRIMARY KEY(day, inverter_id)
            )
        """)
        
        # 5. Create inverter_config table for sensor management
        log.info("Creating/verifying inverter_config table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inverter_config (
                inverter_id TEXT NOT NULL,
                sensor_id TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'api',
                PRIMARY KEY (inverter_id, sensor_id)
            )
        """)
        
        # Add indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_inverter_config_inverter_id 
            ON inverter_config(inverter_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_inverter_config_updated_at 
            ON inverter_config(updated_at)
        """)
        
        # 6. Create system_logs table for enhanced logging
        log.info("Creating/verifying system_logs table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                component TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp 
            ON system_logs(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_system_logs_level 
            ON system_logs(level)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_system_logs_component 
            ON system_logs(component)
        """)
        
        # 7. Update database version
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT
            )
        """)
        
        cursor.execute("""
            INSERT OR REPLACE INTO schema_version (version, applied_at, description)
            VALUES ('2.0', ?, 'Settings management, Energy Calculator, Enhanced API endpoints')
        """, (datetime.now().isoformat(),))
        
        # Commit all changes first
        conn.commit()
        
        # 8. Optimize database (after commit, outside transaction)
        log.info("Optimizing database...")
        try:
            cursor.execute("VACUUM")
            cursor.execute("ANALYZE")
            log.info("Database optimization completed")
        except sqlite3.OperationalError as e:
            log.warning(f"Database optimization failed (non-critical): {e}")
            # Continue anyway as this is not critical
        log.info("Database migration completed successfully")
        
        # Verify migration
        cursor.execute("SELECT version, applied_at, description FROM schema_version WHERE version = '2.0'")
        version_info = cursor.fetchone()
        if version_info:
            log.info(f"Migration verified - Version: {version_info[0]}, Applied: {version_info[1]}")
        
        conn.close()
        return True
        
    except Exception as e:
        log.error(f"Migration failed: {e}", exc_info=True)
        log.error(f"Database backup available at: {backup_path}")
        return False

def verify_migration(db_path: str) -> bool:
    """Verify that the migration was successful."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if all required tables exist
        required_tables = [
            'energy_samples',
            'configuration', 
            'hourly_energy',
            'pv_daily',
            'inverter_config',
            'system_logs',
            'schema_version'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = set(required_tables) - set(existing_tables)
        if missing_tables:
            log.error(f"Missing tables after migration: {missing_tables}")
            return False
        
        # Check schema version
        cursor.execute("SELECT version FROM schema_version WHERE version = '2.0'")
        if not cursor.fetchone():
            log.error("Schema version 2.0 not found")
            return False
        
        log.info("Migration verification successful")
        conn.close()
        return True
        
    except Exception as e:
        log.error(f"Migration verification failed: {e}")
        return False

def main():
    """Main function to run the database migration."""
    log.info("=== Solar Monitoring System Database Migration v2.0 ===")
    
    # Find database
    db_path = find_database_path()
    
    if not os.path.exists(db_path):
        log.info("Database doesn't exist yet, creating new database...")
        # Create empty database file
        Path(db_path).touch()
    
    # Run migration
    if migrate_database(db_path):
        log.info("Migration completed successfully")
        
        # Verify migration
        if verify_migration(db_path):
            log.info("✅ Database migration v2.0 completed and verified successfully!")
            log.info("New features available:")
            log.info("  - Settings/Configuration management")
            log.info("  - Energy Calculator with hourly energy data")
            log.info("  - Enhanced API endpoints")
            log.info("  - Inverter sensor management")
            log.info("  - System logging")
            sys.exit(0)
        else:
            log.error("❌ Migration verification failed")
            sys.exit(1)
    else:
        log.error("❌ Database migration failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
