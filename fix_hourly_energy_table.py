#!/usr/bin/env python3
"""
Fix the hourly_energy table structure to properly support historical data
"""

import sqlite3
import logging
from datetime import datetime, timedelta
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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

def fix_hourly_energy_table(db_path: str = None):
    """Fix the hourly_energy table structure"""
    
    if db_path is None:
        db_path = find_database_path()
    
    if not os.path.exists(db_path):
        log.error(f"Database file {db_path} not found!")
        return False
    
    try:
        # Backup the database first
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        log.info(f"Creating backup: {backup_path}")
        
        import shutil
        shutil.copy2(db_path, backup_path)
        log.info("Backup created successfully")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the table exists and get its current structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hourly_energy'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            log.info("Current hourly_energy table exists, checking structure...")
            
            # Get current table info
            cursor.execute("PRAGMA table_info(hourly_energy)")
            columns = cursor.fetchall()
            log.info(f"Current columns: {[col[1] for col in columns]}")
            
            # Check if we need to migrate
            column_names = [col[1] for col in columns]
            needs_migration = 'date' not in column_names
            
            if needs_migration:
                log.info("Table needs migration - date column missing")
                
                # Create new table with correct structure
                log.info("Creating new hourly_energy table with correct structure...")
                cursor.execute("""
                    CREATE TABLE hourly_energy_new (
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
                
                # Migrate existing data if any
                log.info("Migrating existing data...")
                cursor.execute("SELECT COUNT(*) FROM hourly_energy")
                existing_count = cursor.fetchone()[0]
                
                if existing_count > 0:
                    log.info(f"Found {existing_count} existing records to migrate")
                    
                    # Get existing data
                    cursor.execute("""
                        SELECT ts, inverter_id, hour_start, solar_energy_kwh, load_energy_kwh,
                               battery_charge_energy_kwh, battery_discharge_energy_kwh,
                               grid_import_energy_kwh, grid_export_energy_kwh,
                               avg_solar_power_w, avg_load_power_w, avg_battery_power_w,
                               avg_grid_power_w, sample_count, created_at
                        FROM hourly_energy
                    """)
                    
                    migrated_count = 0
                    for row in cursor.fetchall():
                        ts, inverter_id, hour_start, solar_energy_kwh, load_energy_kwh, \
                        battery_charge_energy_kwh, battery_discharge_energy_kwh, \
                        grid_import_energy_kwh, grid_export_energy_kwh, \
                        avg_solar_power_w, avg_load_power_w, avg_battery_power_w, \
                        avg_grid_power_w, sample_count, created_at = row
                        
                        # Extract date from timestamp
                        try:
                            if ts:
                                # Parse timestamp and extract date
                                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                date = dt.strftime('%Y-%m-%d')
                                
                                # Extract hour from hour_start
                                hour = int(hour_start.split(':')[0]) if ':' in str(hour_start) else int(hour_start)
                                
                                # Insert into new table
                                cursor.execute("""
                                    INSERT OR REPLACE INTO hourly_energy_new (
                                        inverter_id, date, hour_start, solar_energy_kwh, load_energy_kwh,
                                        battery_charge_energy_kwh, battery_discharge_energy_kwh,
                                        grid_import_energy_kwh, grid_export_energy_kwh,
                                        avg_solar_power_w, avg_load_power_w, avg_battery_power_w,
                                        avg_grid_power_w, sample_count, created_at
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    inverter_id, date, hour, solar_energy_kwh, load_energy_kwh,
                                    battery_charge_energy_kwh, battery_discharge_energy_kwh,
                                    grid_import_energy_kwh, grid_export_energy_kwh,
                                    avg_solar_power_w, avg_load_power_w, avg_battery_power_w,
                                    avg_grid_power_w, sample_count, created_at
                                ))
                                migrated_count += 1
                        except Exception as e:
                            log.warning(f"Failed to migrate record {row}: {e}")
                            continue
                    
                    log.info(f"Migrated {migrated_count} records")
                else:
                    log.info("No existing data to migrate")
                
                # Drop old table and rename new one
                log.info("Replacing old table with new structure...")
                cursor.execute("DROP TABLE hourly_energy")
                cursor.execute("ALTER TABLE hourly_energy_new RENAME TO hourly_energy")
                
            else:
                log.info("Table already has correct structure")
        else:
            log.info("Creating new hourly_energy table with correct structure...")
            cursor.execute("""
                CREATE TABLE hourly_energy (
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
        
        # Create indexes for better performance
        log.info("Creating indexes...")
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
        
        # Commit changes
        conn.commit()
        
        # Verify the new structure
        log.info("Verifying new table structure...")
        cursor.execute("PRAGMA table_info(hourly_energy)")
        columns = cursor.fetchall()
        log.info(f"New table columns: {[col[1] for col in columns]}")
        
        # Check primary key
        cursor.execute("PRAGMA index_list(hourly_energy)")
        indexes = cursor.fetchall()
        log.info(f"Table indexes: {indexes}")
        
        conn.close()
        log.info("✅ hourly_energy table structure fixed successfully!")
        return True
        
    except Exception as e:
        log.error(f"❌ Error fixing hourly_energy table: {e}")
        import traceback
        log.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    import sys
    
    # Use command line argument if provided, otherwise auto-detect
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = find_database_path()
    
    print(f"Fixing hourly_energy table in database: {db_path}")
    success = fix_hourly_energy_table(db_path)
    
    if success:
        print("✅ Migration completed successfully!")
        print("\nNew table structure:")
        print("- Primary key: (inverter_id, date, hour_start)")
        print("- date column: YYYY-MM-DD format")
        print("- hour_start: Integer (0-23)")
        print("- Supports historical data for each inverter for each day")
    else:
        print("❌ Migration failed!")
        sys.exit(1)
