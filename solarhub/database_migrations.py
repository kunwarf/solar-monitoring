"""
Database migration scripts for array and battery pack support.
"""
import sqlite3
import logging
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

log = logging.getLogger(__name__)


def migrate_to_arrays(db_path: str) -> None:
    """
    Migrate database schema to support arrays and battery packs.
    
    Creates new tables:
    - arrays
    - battery_packs
    - battery_pack_attachments
    - array_samples
    
    Updates existing tables:
    - energy_samples: add array_id column
    - battery_bank_samples: add pack_id and array_id columns
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    try:
        # Create arrays table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS arrays (
                array_id TEXT PRIMARY KEY,
                name TEXT
            )
        """)
        log.info("Created arrays table")
        
        # Create battery_packs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battery_packs (
                pack_id TEXT PRIMARY KEY,
                name TEXT,
                chemistry TEXT,
                nominal_kwh REAL,
                max_charge_kw REAL,
                max_discharge_kw REAL
            )
        """)
        log.info("Created battery_packs table")
        
        # Create battery_pack_attachments table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battery_pack_attachments (
                pack_id TEXT,
                array_id TEXT,
                attached_since TEXT NOT NULL,
                detached_at TEXT,
                PRIMARY KEY (pack_id, attached_since)
            )
        """)
        log.info("Created battery_pack_attachments table")
        
        # Create array_samples table for per-array rollups
        cur.execute("""
            CREATE TABLE IF NOT EXISTS array_samples (
                ts TEXT NOT NULL,
                array_id TEXT NOT NULL,
                pv_power_w INTEGER,
                load_power_w INTEGER,
                grid_power_w INTEGER,
                batt_power_w INTEGER,
                batt_soc_pct REAL,
                batt_voltage_v REAL,
                batt_current_a REAL,
                PRIMARY KEY (ts, array_id)
            )
        """)
        log.info("Created array_samples table")
        
        # Add array_id to energy_samples if not exists
        try:
            cur.execute("ALTER TABLE energy_samples ADD COLUMN array_id TEXT")
            log.info("Added array_id column to energy_samples")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                log.debug("array_id column already exists in energy_samples")
            else:
                raise
        
        # Add pack_id and array_id to battery_bank_samples if not exists
        try:
            cur.execute("ALTER TABLE battery_bank_samples ADD COLUMN pack_id TEXT")
            log.info("Added pack_id column to battery_bank_samples")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                log.debug("pack_id column already exists in battery_bank_samples")
            else:
                raise
        
        try:
            cur.execute("ALTER TABLE battery_bank_samples ADD COLUMN array_id TEXT")
            log.info("Added array_id column to battery_bank_samples")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                log.debug("array_id column already exists in battery_bank_samples")
            else:
                raise
        
        # Create inverter_setpoints table for power splitting logging
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inverter_setpoints (
                ts TEXT NOT NULL,
                array_id TEXT NOT NULL,
                inverter_id TEXT NOT NULL,
                action TEXT CHECK(action IN ('charge','discharge')),
                target_w INTEGER NOT NULL,
                headroom_w INTEGER,
                unmet_w INTEGER DEFAULT 0,
                PRIMARY KEY (ts, inverter_id, action)
            )
        """)
        log.info("Created/verified inverter_setpoints table")
        
        # Create indexes for performance
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_energy_samples_array_id 
            ON energy_samples(array_id)
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_array_samples_array_id 
            ON array_samples(array_id)
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_array_samples_ts 
            ON array_samples(ts)
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_battery_pack_attachments_pack_id 
            ON battery_pack_attachments(pack_id)
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_battery_pack_attachments_array_id 
            ON battery_pack_attachments(array_id)
        """)
        
        log.info("Created indexes for array support")
        
        con.commit()
        log.info("Database migration to arrays completed successfully")
        
    except Exception as e:
        con.rollback()
        log.error(f"Database migration failed: {e}", exc_info=True)
        raise
    finally:
        con.close()


def backfill_array_ids(
    db_path: str,
    inverter_to_array_map: Dict[str, str]
) -> None:
    """
    Backfill array_id in energy_samples using inverter_id -> array_id mapping.
    
    Args:
        db_path: Path to SQLite database
        inverter_to_array_map: Dict mapping inverter_id -> array_id
    """
    if not inverter_to_array_map:
        log.warning("No inverter to array mapping provided, skipping backfill")
        return
    
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    try:
        updated_count = 0
        for inverter_id, array_id in inverter_to_array_map.items():
            cur.execute("""
                UPDATE energy_samples 
                SET array_id = ? 
                WHERE inverter_id = ? AND array_id IS NULL
            """, (array_id, inverter_id))
            updated_count += cur.rowcount
        
        con.commit()
        log.info(f"Backfilled array_id for {updated_count} rows in energy_samples")
        
    except Exception as e:
        con.rollback()
        log.error(f"Failed to backfill array_id: {e}", exc_info=True)
        raise
    finally:
        con.close()


def migrate_to_billing_tables(db_path: str) -> None:
    """
    Migrate database schema to support billing daily accruals and archival.
    
    Creates new tables:
    - billing_daily: daily snapshots of running bill status
    - billing_months: finalized monthly billing records
    - billing_cycles: finalized 3-month cycle summaries
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    try:
        # Create billing_daily table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS billing_daily (
                site_id TEXT NOT NULL DEFAULT 'default',
                date TEXT NOT NULL,
                billing_month_id TEXT,
                import_off_kwh REAL DEFAULT 0.0,
                export_off_kwh REAL DEFAULT 0.0,
                import_peak_kwh REAL DEFAULT 0.0,
                export_peak_kwh REAL DEFAULT 0.0,
                net_import_off_kwh REAL DEFAULT 0.0,
                net_import_peak_kwh REAL DEFAULT 0.0,
                credits_off_cycle_kwh_balance REAL DEFAULT 0.0,
                credits_peak_cycle_kwh_balance REAL DEFAULT 0.0,
                bill_off_energy_rs REAL DEFAULT 0.0,
                bill_peak_energy_rs REAL DEFAULT 0.0,
                fixed_prorated_rs REAL DEFAULT 0.0,
                expected_cycle_credit_rs REAL DEFAULT 0.0,
                bill_raw_rs_to_date REAL DEFAULT 0.0,
                bill_credit_balance_rs_to_date REAL DEFAULT 0.0,
                bill_final_rs_to_date REAL DEFAULT 0.0,
                surplus_deficit_flag TEXT CHECK(surplus_deficit_flag IN ('SURPLUS', 'DEFICIT', 'NEUTRAL')),
                generated_at_ts TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (site_id, date)
            )
        """)
        log.info("Created billing_daily table")
        
        # Create billing_months table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS billing_months (
                id TEXT PRIMARY KEY,
                billing_month TEXT NOT NULL,
                year INTEGER NOT NULL,
                month_number INTEGER NOT NULL,
                anchor_start TEXT NOT NULL,
                anchor_end TEXT NOT NULL,
                import_off_kwh REAL DEFAULT 0.0,
                export_off_kwh REAL DEFAULT 0.0,
                import_peak_kwh REAL DEFAULT 0.0,
                export_peak_kwh REAL DEFAULT 0.0,
                net_import_off_kwh REAL DEFAULT 0.0,
                net_import_peak_kwh REAL DEFAULT 0.0,
                solar_kwh REAL DEFAULT 0.0,
                load_kwh REAL DEFAULT 0.0,
                fixed_charge_rs REAL DEFAULT 0.0,
                cycle_credit_off_rs REAL DEFAULT 0.0,
                cycle_credit_peak_rs REAL DEFAULT 0.0,
                raw_bill_rs REAL DEFAULT 0.0,
                final_bill_rs REAL DEFAULT 0.0,
                credit_balance_after_rs REAL DEFAULT 0.0,
                config_hash TEXT,
                finalized_at_ts TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        log.info("Created billing_months table")
        
        # Create billing_cycles table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS billing_cycles (
                id TEXT PRIMARY KEY,
                cycle_number INTEGER NOT NULL,
                year INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                credits_off_consumed_kwh REAL DEFAULT 0.0,
                credits_off_created_kwh REAL DEFAULT 0.0,
                credits_off_settled_rs REAL DEFAULT 0.0,
                credits_peak_consumed_kwh REAL DEFAULT 0.0,
                credits_peak_created_kwh REAL DEFAULT 0.0,
                credits_peak_settled_rs REAL DEFAULT 0.0,
                finalized_at_ts TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        log.info("Created billing_cycles table")
        
        # Create indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_billing_daily_date 
            ON billing_daily(date)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_billing_daily_month_id 
            ON billing_daily(billing_month_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_billing_months_year_month 
            ON billing_months(year, month_number)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_billing_cycles_year 
            ON billing_cycles(year)
        """)
        
        log.info("Created indexes for billing tables")
        
        con.commit()
        log.info("Database migration to billing tables completed successfully")
        
    except Exception as e:
        con.rollback()
        log.error(f"Database migration to billing tables failed: {e}", exc_info=True)
        raise
    finally:
        con.close()


def migrate_to_device_discovery(db_path: str) -> None:
    """
    Migrate database schema to support automatic USB device discovery.
    
    Creates new table:
    - device_discovery: stores auto-discovered devices with serial numbers
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    try:
        # Create device_discovery table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS device_discovery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL UNIQUE,
                device_type TEXT NOT NULL,
                serial_number TEXT NOT NULL,
                port TEXT,
                last_known_port TEXT,
                port_history TEXT,
                adapter_config TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                failure_count INTEGER DEFAULT 0,
                next_retry_time TEXT,
                first_discovered TEXT NOT NULL,
                last_seen TEXT,
                discovery_timestamp TEXT NOT NULL,
                is_auto_discovered INTEGER DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        log.info("Created device_discovery table")
        
        # Create indexes for fast lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_discovery_serial 
            ON device_discovery(serial_number, device_type)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_discovery_status 
            ON device_discovery(status)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_discovery_port 
            ON device_discovery(port)
        """)
        
        log.info("Created indexes for device_discovery table")
        
        con.commit()
        log.info("Database migration to device_discovery completed successfully")
        
    except Exception as e:
        con.rollback()
        log.error(f"Database migration to device_discovery failed: {e}", exc_info=True)
        raise
    finally:
        con.close()


def migrate_to_home_billing(db_path: str) -> None:
    """
    Migrate database schema to support home-level billing with meter data.
    
    Creates new tables:
    - meter_hourly_energy: hourly import/export energy calculated from meter samples
    
    Updates existing tables:
    - billing_daily: add home_id column (use site_id as home_id for backward compatibility)
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    try:
        # Create meter_hourly_energy table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meter_hourly_energy (
                meter_id TEXT NOT NULL,
                date TEXT NOT NULL,
                hour_start INTEGER NOT NULL,
                import_energy_kwh REAL DEFAULT 0.0,
                export_energy_kwh REAL DEFAULT 0.0,
                avg_power_w REAL,
                sample_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (meter_id, date, hour_start)
            )
        """)
        log.info("Created meter_hourly_energy table")
        
        # Create indexes for efficient queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_meter_hourly_energy_meter_date 
            ON meter_hourly_energy(meter_id, date)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_meter_hourly_energy_date_hour 
            ON meter_hourly_energy(date, hour_start)
        """)
        log.info("Created indexes for meter_hourly_energy table")
        
        # Add home_id column to billing_daily if not exists
        try:
            cur.execute("ALTER TABLE billing_daily ADD COLUMN home_id TEXT")
            log.info("Added home_id column to billing_daily")
            
            # For backward compatibility, set home_id = site_id for existing records
            cur.execute("""
                UPDATE billing_daily 
                SET home_id = site_id 
                WHERE home_id IS NULL
            """)
            log.info("Backfilled home_id from site_id in billing_daily")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                log.debug("home_id column already exists in billing_daily")
            else:
                raise
        
        # Update primary key constraint to include home_id
        # Note: SQLite doesn't support ALTER TABLE to modify PRIMARY KEY
        # We'll handle this in application logic by using (home_id, date) as unique constraint
        # For now, we'll keep the existing primary key and add a unique index
        try:
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_daily_home_date 
                ON billing_daily(home_id, date)
            """)
            log.info("Created unique index for (home_id, date) in billing_daily")
        except sqlite3.OperationalError as e:
            log.warning(f"Could not create unique index (may already exist): {e}")
        
        con.commit()
        log.info("Database migration to home billing completed successfully")
        
    except Exception as e:
        con.rollback()
        log.error(f"Database migration to home billing failed: {e}", exc_info=True)
        raise
    finally:
        con.close()


# ============= PHASE 1: HIERARCHY MIGRATION =============

def migrate_to_hierarchy_schema(db_path: str) -> None:
    """
    Phase 1: Migrate database schema to support complete hierarchy structure.
    
    Creates new tables:
    - Catalog tables: systems, adapter_base, adapters, inverters, battery_arrays, 
      battery_array_attachments, batteries, battery_cells, battery_pack_adapters, meters
    - Aggregated tables: array_hourly_energy, system_hourly_energy, battery_bank_hourly,
      array_daily_summary, system_daily_summary, battery_bank_daily
    
    Updates existing tables:
    - Adds system_id, battery_array_id, adapter_id foreign keys to existing tables
    - Adds indexes for all foreign keys
    
    This migration is idempotent (safe to run multiple times).
    """
    import sqlite3
    
    # Check database integrity first
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        # Run integrity check
        cur.execute("PRAGMA integrity_check")
        result = cur.fetchone()
        if result and result[0] != "ok":
            log.error(f"Database integrity check failed: {result[0]}")
            log.error("Database is corrupted. Please restore from backup or recreate the database.")
            con.close()
            raise sqlite3.DatabaseError(f"Database corruption detected: {result[0]}")
        con.close()
    except sqlite3.DatabaseError as e:
        log.error(f"Database integrity check failed: {e}")
        log.error("Database is corrupted. Please restore from backup or recreate the database.")
        raise
    
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # Enable foreign key constraints
    cur.execute("PRAGMA foreign_keys = ON")
    
    try:
        log.info("Starting Phase 1: Hierarchy schema migration")
        
        # ============= 1. CREATE CATALOG TABLES =============
        
        # Systems table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS systems (
                system_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                timezone TEXT DEFAULT 'Asia/Karachi',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        log.info("Created/verified systems table")
        
        # Adapter base table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS adapter_base (
                adapter_type TEXT PRIMARY KEY,
                device_category TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                config_schema TEXT NOT NULL,
                supported_transports TEXT,
                default_config TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        log.info("Created/verified adapter_base table")
        
        # Adapters table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS adapters (
                adapter_id TEXT PRIMARY KEY,
                adapter_type TEXT NOT NULL,
                device_category TEXT NOT NULL,
                name TEXT,
                config_json TEXT NOT NULL,
                device_id TEXT,
                device_type TEXT,
                priority INTEGER DEFAULT 1,
                enabled BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (adapter_type) REFERENCES adapter_base(adapter_type) ON DELETE RESTRICT
            )
        """)
        log.info("Created/verified adapters table")
        
        # Update arrays table to add system_id
        try:
            cur.execute("ALTER TABLE arrays ADD COLUMN system_id TEXT")
            log.info("Added system_id column to arrays table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
            log.debug("system_id column already exists in arrays table")
        
        # Inverters table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inverters (
                inverter_id TEXT PRIMARY KEY,
                array_id TEXT NOT NULL,
                system_id TEXT NOT NULL,
                adapter_id TEXT,
                name TEXT NOT NULL,
                model TEXT,
                serial_number TEXT,
                vendor TEXT,
                phase_type TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE CASCADE,
                FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE,
                FOREIGN KEY (adapter_id) REFERENCES adapters(adapter_id) ON DELETE SET NULL
            )
        """)
        log.info("Created/verified inverters table")
        
        # Battery arrays table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battery_arrays (
                battery_array_id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
            )
        """)
        log.info("Created/verified battery_arrays table")
        
        # Update battery_packs table to add battery_array_id and system_id
        try:
            cur.execute("ALTER TABLE battery_packs ADD COLUMN battery_array_id TEXT")
            log.info("Added battery_array_id column to battery_packs table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
            log.debug("battery_array_id column already exists in battery_packs table")
        
        try:
            cur.execute("ALTER TABLE battery_packs ADD COLUMN system_id TEXT")
            log.info("Added system_id column to battery_packs table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
            log.debug("system_id column already exists in battery_packs table")
        
        # Battery pack adapters table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battery_pack_adapters (
                pack_id TEXT NOT NULL,
                adapter_id TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 1,
                enabled BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (pack_id, adapter_id),
                FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
                FOREIGN KEY (adapter_id) REFERENCES adapters(adapter_id) ON DELETE CASCADE
            )
        """)
        log.info("Created/verified battery_pack_adapters table")
        
        # Batteries table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS batteries (
                battery_id TEXT PRIMARY KEY,
                pack_id TEXT NOT NULL,
                battery_array_id TEXT NOT NULL,
                system_id TEXT NOT NULL,
                battery_index INTEGER NOT NULL,
                serial_number TEXT,
                model TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
                FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
                FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE,
                UNIQUE(pack_id, battery_index)
            )
        """)
        log.info("Created/verified batteries table")
        
        # Battery cells table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battery_cells (
                cell_id TEXT PRIMARY KEY,
                battery_id TEXT NOT NULL,
                pack_id TEXT NOT NULL,
                battery_array_id TEXT NOT NULL,
                system_id TEXT NOT NULL,
                cell_index INTEGER NOT NULL,
                nominal_voltage REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (battery_id) REFERENCES batteries(battery_id) ON DELETE CASCADE,
                FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
                FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
                FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE,
                UNIQUE(battery_id, cell_index)
            )
        """)
        log.info("Created/verified battery_cells table")
        
        # Battery array attachments table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battery_array_attachments (
                battery_array_id TEXT NOT NULL,
                inverter_array_id TEXT NOT NULL,
                attached_since TEXT NOT NULL,
                detached_at TEXT,
                PRIMARY KEY (battery_array_id, attached_since),
                FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
                FOREIGN KEY (inverter_array_id) REFERENCES arrays(array_id) ON DELETE CASCADE
            )
        """)
        log.info("Created/verified battery_array_attachments table")
        
        # Meters table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meters (
                meter_id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                array_id TEXT,
                adapter_id TEXT,
                name TEXT NOT NULL,
                model TEXT,
                type TEXT,
                attachment_target TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE,
                FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE SET NULL,
                FOREIGN KEY (adapter_id) REFERENCES adapters(adapter_id) ON DELETE SET NULL
            )
        """)
        log.info("Created/verified meters table")
        
        # ============= 2. ADD FOREIGN KEYS TO EXISTING SAMPLE TABLES =============
        
        # Add system_id to energy_samples
        try:
            cur.execute("ALTER TABLE energy_samples ADD COLUMN system_id TEXT")
            log.info("Added system_id column to energy_samples table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
            log.debug("system_id column already exists in energy_samples table")
        
        # Add system_id to array_samples
        try:
            cur.execute("ALTER TABLE array_samples ADD COLUMN system_id TEXT")
            log.info("Added system_id column to array_samples table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
            log.debug("system_id column already exists in array_samples table")
        
        # Add battery_array_id and system_id to battery_bank_samples
        try:
            cur.execute("ALTER TABLE battery_bank_samples ADD COLUMN battery_array_id TEXT")
            log.info("Added battery_array_id column to battery_bank_samples table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
            log.debug("battery_array_id column already exists in battery_bank_samples table")
        
        try:
            cur.execute("ALTER TABLE battery_bank_samples ADD COLUMN system_id TEXT")
            log.info("Added system_id column to battery_bank_samples table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
            log.debug("system_id column already exists in battery_bank_samples table")
        
        # Add pack_id, battery_id, battery_array_id, system_id to battery_unit_samples
        for col in ['pack_id', 'battery_id', 'battery_array_id', 'system_id']:
            try:
                cur.execute(f"ALTER TABLE battery_unit_samples ADD COLUMN {col} TEXT")
                log.info(f"Added {col} column to battery_unit_samples table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise
                log.debug(f"{col} column already exists in battery_unit_samples table")
        
        # Add battery_id, pack_id, battery_array_id, system_id to battery_cell_samples
        for col in ['battery_id', 'pack_id', 'battery_array_id', 'system_id']:
            try:
                cur.execute(f"ALTER TABLE battery_cell_samples ADD COLUMN {col} TEXT")
                log.info(f"Added {col} column to battery_cell_samples table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise
                log.debug(f"{col} column already exists in battery_cell_samples table")
        
        # Add system_id to meter_samples
        try:
            cur.execute("ALTER TABLE meter_samples ADD COLUMN system_id TEXT")
            log.info("Added system_id column to meter_samples table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
            log.debug("system_id column already exists in meter_samples table")
        
        # Add system_id and array_id to hourly_energy
        for col in ['system_id', 'array_id']:
            try:
                cur.execute(f"ALTER TABLE hourly_energy ADD COLUMN {col} TEXT")
                log.info(f"Added {col} column to hourly_energy table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise
                log.debug(f"{col} column already exists in hourly_energy table")
        
        # Add system_id and array_id to daily_summary
        for col in ['system_id', 'array_id']:
            try:
                cur.execute(f"ALTER TABLE daily_summary ADD COLUMN {col} TEXT")
                log.info(f"Added {col} column to daily_summary table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise
                log.debug(f"{col} column already exists in daily_summary table")
        
        # Add system_id to meter_hourly_energy
        try:
            cur.execute("ALTER TABLE meter_hourly_energy ADD COLUMN system_id TEXT")
            log.info("Added system_id column to meter_hourly_energy table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
            log.debug("system_id column already exists in meter_hourly_energy table")
        
        # Add system_id to meter_daily
        try:
            cur.execute("ALTER TABLE meter_daily ADD COLUMN system_id TEXT")
            log.info("Added system_id column to meter_daily table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
            log.debug("system_id column already exists in meter_daily table")
        
        # ============= 3. CREATE AGGREGATED TABLES =============
        
        # Array hourly energy
        cur.execute("""
            CREATE TABLE IF NOT EXISTS array_hourly_energy (
                array_id TEXT NOT NULL,
                system_id TEXT NOT NULL,
                date TEXT NOT NULL,
                hour_start INTEGER NOT NULL,
                solar_energy_kwh REAL,
                load_energy_kwh REAL,
                battery_charge_energy_kwh REAL,
                battery_discharge_energy_kwh REAL,
                grid_import_energy_kwh REAL,
                grid_export_energy_kwh REAL,
                avg_solar_power_w REAL,
                avg_load_power_w REAL,
                avg_battery_power_w REAL,
                avg_grid_power_w REAL,
                sample_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (array_id, date, hour_start),
                FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE CASCADE,
                FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
            )
        """)
        log.info("Created/verified array_hourly_energy table")
        
        # System hourly energy
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_hourly_energy (
                system_id TEXT NOT NULL,
                date TEXT NOT NULL,
                hour_start INTEGER NOT NULL,
                solar_energy_kwh REAL,
                load_energy_kwh REAL,
                battery_charge_energy_kwh REAL,
                battery_discharge_energy_kwh REAL,
                grid_import_energy_kwh REAL,
                grid_export_energy_kwh REAL,
                avg_solar_power_w REAL,
                avg_load_power_w REAL,
                avg_battery_power_w REAL,
                avg_grid_power_w REAL,
                sample_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (system_id, date, hour_start),
                FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
            )
        """)
        log.info("Created/verified system_hourly_energy table")
        
        # Battery bank hourly
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battery_bank_hourly (
                pack_id TEXT NOT NULL,
                battery_array_id TEXT NOT NULL,
                system_id TEXT NOT NULL,
                date TEXT NOT NULL,
                hour_start INTEGER NOT NULL,
                charge_energy_kwh REAL DEFAULT 0.0,
                discharge_energy_kwh REAL DEFAULT 0.0,
                net_energy_kwh REAL DEFAULT 0.0,
                avg_power_w REAL,
                avg_soc_pct REAL,
                min_soc_pct REAL,
                max_soc_pct REAL,
                avg_voltage_v REAL,
                avg_current_a REAL,
                avg_temperature_c REAL,
                sample_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (pack_id, date, hour_start),
                FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
                FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
                FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
            )
        """)
        log.info("Created/verified battery_bank_hourly table")
        
        # Array daily summary
        cur.execute("""
            CREATE TABLE IF NOT EXISTS array_daily_summary (
                date TEXT NOT NULL,
                array_id TEXT NOT NULL,
                system_id TEXT NOT NULL,
                day_of_year INTEGER NOT NULL,
                year INTEGER NOT NULL,
                pv_energy_kwh REAL,
                pv_max_power_w REAL,
                pv_avg_power_w REAL,
                pv_peak_hour INTEGER,
                load_energy_kwh REAL,
                load_max_power_w REAL,
                load_avg_power_w REAL,
                load_peak_hour INTEGER,
                battery_min_soc_pct REAL,
                battery_max_soc_pct REAL,
                battery_avg_soc_pct REAL,
                battery_cycles REAL,
                grid_energy_imported_kwh REAL,
                grid_energy_exported_kwh REAL,
                grid_max_import_w REAL,
                grid_max_export_w REAL,
                weather_factor REAL,
                sample_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, array_id),
                FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE CASCADE,
                FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
            )
        """)
        log.info("Created/verified array_daily_summary table")
        
        # System daily summary
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_daily_summary (
                date TEXT NOT NULL,
                system_id TEXT NOT NULL,
                day_of_year INTEGER NOT NULL,
                year INTEGER NOT NULL,
                pv_energy_kwh REAL,
                pv_max_power_w REAL,
                pv_avg_power_w REAL,
                pv_peak_hour INTEGER,
                load_energy_kwh REAL,
                load_max_power_w REAL,
                load_avg_power_w REAL,
                load_peak_hour INTEGER,
                battery_min_soc_pct REAL,
                battery_max_soc_pct REAL,
                battery_avg_soc_pct REAL,
                battery_cycles REAL,
                grid_energy_imported_kwh REAL,
                grid_energy_exported_kwh REAL,
                grid_max_import_w REAL,
                grid_max_export_w REAL,
                weather_factor REAL,
                sample_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, system_id),
                FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
            )
        """)
        log.info("Created/verified system_daily_summary table")
        
        # Battery bank daily
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battery_bank_daily (
                date TEXT NOT NULL,
                pack_id TEXT NOT NULL,
                battery_array_id TEXT NOT NULL,
                system_id TEXT NOT NULL,
                day_of_year INTEGER NOT NULL,
                year INTEGER NOT NULL,
                charge_energy_kwh REAL DEFAULT 0.0,
                discharge_energy_kwh REAL DEFAULT 0.0,
                net_energy_kwh REAL DEFAULT 0.0,
                min_soc_pct REAL,
                max_soc_pct REAL,
                avg_soc_pct REAL,
                min_voltage_v REAL,
                max_voltage_v REAL,
                avg_voltage_v REAL,
                min_temperature_c REAL,
                max_temperature_c REAL,
                avg_temperature_c REAL,
                min_current_a REAL,
                max_current_a REAL,
                avg_current_a REAL,
                cycles REAL,
                sample_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, pack_id),
                FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
                FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
                FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
            )
        """)
        log.info("Created/verified battery_bank_daily table")
        
        # ============= 4. CREATE INDEXES =============
        
        # Catalog table indexes
        indexes = [
            ("idx_arrays_system_id", "arrays", "system_id"),
            ("idx_inverters_system_id", "inverters", "system_id"),
            ("idx_inverters_array_id", "inverters", "array_id"),
            ("idx_inverters_adapter_id", "inverters", "adapter_id"),
            ("idx_battery_arrays_system_id", "battery_arrays", "system_id"),
            ("idx_battery_packs_system_id", "battery_packs", "system_id"),
            ("idx_battery_packs_battery_array_id", "battery_packs", "battery_array_id"),
            ("idx_batteries_system_id", "batteries", "system_id"),
            ("idx_batteries_pack_id", "batteries", "pack_id"),
            ("idx_battery_cells_system_id", "battery_cells", "system_id"),
            ("idx_battery_cells_battery_id", "battery_cells", "battery_id"),
            ("idx_meters_system_id", "meters", "system_id"),
            ("idx_meters_array_id", "meters", "array_id"),
            ("idx_meters_adapter_id", "meters", "adapter_id"),
            ("idx_adapters_adapter_type", "adapters", "adapter_type"),
            ("idx_adapters_device_id", "adapters", "device_id, device_type"),
            ("idx_adapters_device_category", "adapters", "device_category"),
            ("idx_battery_pack_adapters_pack_id", "battery_pack_adapters", "pack_id"),
            ("idx_battery_pack_adapters_adapter_id", "battery_pack_adapters", "adapter_id"),
        ]
        
        for idx_name, table, columns in indexes:
            try:
                cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
                log.debug(f"Created/verified index {idx_name}")
            except sqlite3.OperationalError as e:
                log.warning(f"Could not create index {idx_name}: {e}")
        
        # Sample table indexes
        sample_indexes = [
            ("idx_energy_samples_system_id", "energy_samples", "system_id"),
            ("idx_array_samples_system_id", "array_samples", "system_id"),
            ("idx_battery_bank_samples_system_id", "battery_bank_samples", "system_id"),
            ("idx_battery_unit_samples_system_id", "battery_unit_samples", "system_id"),
            ("idx_battery_cell_samples_system_id", "battery_cell_samples", "system_id"),
            ("idx_meter_samples_system_id", "meter_samples", "system_id"),
        ]
        
        for idx_name, table, columns in sample_indexes:
            try:
                # Check if table exists before creating index
                cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cur.fetchone():
                    log.warning(f"Table {table} does not exist, skipping index {idx_name}")
                    continue
                cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
                log.debug(f"Created/verified index {idx_name}")
            except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
                log.warning(f"Could not create index {idx_name} on table {table}: {e}")
                # If database is corrupted, we can't continue
                if "malformed" in str(e).lower() or "corrupt" in str(e).lower():
                    raise
        
        # Summary table indexes
        summary_indexes = [
            ("idx_hourly_energy_system_id", "hourly_energy", "system_id"),
            ("idx_hourly_energy_array_id", "hourly_energy", "array_id"),
            ("idx_daily_summary_system_id", "daily_summary", "system_id"),
            ("idx_daily_summary_array_id", "daily_summary", "array_id"),
            ("idx_array_hourly_energy_system_id", "array_hourly_energy", "system_id"),
            ("idx_system_hourly_energy_date", "system_hourly_energy", "date DESC"),
            ("idx_array_daily_summary_system_id", "array_daily_summary", "system_id"),
            ("idx_system_daily_summary_date", "system_daily_summary", "date DESC"),
            ("idx_battery_bank_hourly_pack_id", "battery_bank_hourly", "pack_id"),
            ("idx_battery_bank_hourly_system_id", "battery_bank_hourly", "system_id"),
            ("idx_battery_bank_daily_pack_id", "battery_bank_daily", "pack_id"),
            ("idx_battery_bank_daily_system_id", "battery_bank_daily", "system_id"),
            ("idx_meter_hourly_energy_system_id", "meter_hourly_energy", "system_id"),
            ("idx_meter_daily_system_id", "meter_daily", "system_id"),
        ]
        
        for idx_name, table, columns in summary_indexes:
            try:
                # Check if table exists before creating index
                cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cur.fetchone():
                    log.warning(f"Table {table} does not exist, skipping index {idx_name}")
                    continue
                cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
                log.debug(f"Created/verified index {idx_name}")
            except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
                log.warning(f"Could not create index {idx_name} on table {table}: {e}")
                # If database is corrupted, we can't continue
                if "malformed" in str(e).lower() or "corrupt" in str(e).lower():
                    raise
        
        con.commit()
        log.info("Phase 1: Hierarchy schema migration completed successfully")
        
    except Exception as e:
        con.rollback()
        log.error(f"Phase 1: Hierarchy schema migration failed: {e}", exc_info=True)
        raise
    finally:
        con.close()


def create_default_system(db_path: str, system_id: str = "system", name: str = "My Solar System", 
                         description: str = "Auto-created default system", 
                         timezone: str = "Asia/Karachi") -> None:
    """
    Create default system if none exists.
    Also creates default arrays if they don't exist.
    
    Args:
        db_path: Path to SQLite database
        system_id: System ID (default: "system")
        name: System name
        description: System description
        timezone: System timezone
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    try:
        # Check if system exists
        cur.execute("SELECT COUNT(*) FROM systems WHERE system_id = ?", (system_id,))
        if cur.fetchone()[0] > 0:
            log.debug(f"System '{system_id}' already exists, skipping creation")
            con.close()
            return
        
        # Create default system
        cur.execute("""
            INSERT INTO systems (system_id, name, description, timezone)
            VALUES (?, ?, ?, ?)
        """, (system_id, name, description, timezone))
        log.info(f"Created default system: {system_id}")
        
        # Create default inverter array if none exists
        cur.execute("SELECT COUNT(*) FROM arrays WHERE array_id = 'array1'")
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO arrays (array_id, system_id, name)
                VALUES ('array1', ?, 'Default Inverter Array')
            """, (system_id,))
            log.info("Created default inverter array: array1")
        
        # Create default battery array if none exists
        cur.execute("SELECT COUNT(*) FROM battery_arrays WHERE battery_array_id = 'battery_array1'")
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO battery_arrays (battery_array_id, system_id, name)
                VALUES ('battery_array1', ?, 'Default Battery Array')
            """, (system_id,))
            log.info("Created default battery array: battery_array1")
        
        # Auto-attach battery array to inverter array if not already attached
        cur.execute("""
            SELECT COUNT(*) FROM battery_array_attachments 
            WHERE battery_array_id = 'battery_array1' 
            AND inverter_array_id = 'array1' 
            AND detached_at IS NULL
        """)
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO battery_array_attachments (battery_array_id, inverter_array_id, attached_since)
                VALUES ('battery_array1', 'array1', ?)
            """, (datetime.now().isoformat(),))
            log.info("Auto-attached battery_array1 to array1")
        
        con.commit()
        log.info("Default system and arrays created successfully")
        
    except Exception as e:
        con.rollback()
        log.error(f"Failed to create default system: {e}", exc_info=True)
        raise
    finally:
        con.close()


def backfill_system_ids(db_path: str, system_id: str = "system") -> None:
    """
    Backfill system_id in all existing tables with the default system ID.
    
    This function updates all existing rows in sample and summary tables
    to have system_id set to the default system.
    
    Args:
        db_path: Path to SQLite database
        system_id: System ID to use for backfilling (default: "system")
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    try:
        log.info(f"Starting backfill of system_id='{system_id}' in all tables")
        
        # Tables that need system_id backfilled
        tables_to_backfill = [
            ("arrays", "system_id"),
            ("battery_packs", "system_id"),
            ("energy_samples", "system_id"),
            ("array_samples", "system_id"),
            ("battery_bank_samples", "system_id"),
            ("battery_unit_samples", "system_id"),
            ("battery_cell_samples", "system_id"),
            ("meter_samples", "system_id"),
            ("hourly_energy", "system_id"),
            ("daily_summary", "system_id"),
            ("meter_hourly_energy", "system_id"),
            ("meter_daily", "system_id"),
        ]
        
        total_updated = 0
        for table, column in tables_to_backfill:
            try:
                # Check if column exists
                cur.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cur.fetchall()]
                if column not in columns:
                    log.debug(f"Column {column} does not exist in {table}, skipping")
                    continue
                
                # Update NULL system_id values
                cur.execute(f"""
                    UPDATE {table} 
                    SET {column} = ? 
                    WHERE {column} IS NULL
                """, (system_id,))
                updated = cur.rowcount
                total_updated += updated
                if updated > 0:
                    log.info(f"Backfilled {column} in {table}: {updated} rows")
            except sqlite3.OperationalError as e:
                log.warning(f"Could not backfill {column} in {table}: {e}")
        
        # Special handling for arrays: update system_id if arrays table has system_id column
        try:
            cur.execute("PRAGMA table_info(arrays)")
            columns = [row[1] for row in cur.fetchall()]
            if "system_id" in columns:
                cur.execute("UPDATE arrays SET system_id = ? WHERE system_id IS NULL", (system_id,))
                updated = cur.rowcount
                if updated > 0:
                    log.info(f"Backfilled system_id in arrays: {updated} rows")
                    total_updated += updated
        except sqlite3.OperationalError as e:
            log.warning(f"Could not backfill system_id in arrays: {e}")
        
        # Special handling for battery_packs: update system_id and battery_array_id
        try:
            cur.execute("PRAGMA table_info(battery_packs)")
            columns = [row[1] for row in cur.fetchall()]
            if "system_id" in columns:
                cur.execute("UPDATE battery_packs SET system_id = ? WHERE system_id IS NULL", (system_id,))
                updated = cur.rowcount
                if updated > 0:
                    log.info(f"Backfilled system_id in battery_packs: {updated} rows")
                    total_updated += updated
        except sqlite3.OperationalError as e:
            log.warning(f"Could not backfill system_id in battery_packs: {e}")
        
        con.commit()
        log.info(f"Backfilled system_id in all tables: {total_updated} total rows updated")
        
    except Exception as e:
        con.rollback()
        log.error(f"Failed to backfill system_id: {e}", exc_info=True)
        raise
    finally:
        con.close()


def migrate_config_yaml_to_database(db_path: str, config_path: str = "config.yaml") -> None:
    """
    Migrate configuration from config.yaml to database.
    
    Reads config.yaml and populates:
    - systems table (from home section)
    - arrays table (with system_id)
    - inverters table (with system_id, array_id, adapter_id)
    - battery_arrays table (with system_id)
    - battery_packs table (with battery_array_id, system_id)
    - battery_array_attachments table
    - meters table (with system_id, adapter_id)
    - adapters table (from device adapter configs)
    - adapter_base table (populate with supported adapter types)
    
    Args:
        db_path: Path to SQLite database
        config_path: Path to config.yaml file
    """
    config_file = Path(config_path)
    if not config_file.exists():
        log.warning(f"config.yaml not found at {config_path}, skipping config migration")
        return
    
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # Enable foreign key constraints
    cur.execute("PRAGMA foreign_keys = ON")
    
    try:
        log.info(f"Starting config.yaml to database migration from {config_path}")
        
        # Load config.yaml
        with open(config_file, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        if not config_dict:
            log.warning("config.yaml is empty, skipping migration")
            return
        
        # Get system_id from home section (default to "system")
        home_config = config_dict.get('home', {})
        system_id = home_config.get('id', 'system')
        system_name = home_config.get('name', 'My Solar System')
        system_description = home_config.get('description', 'Main residential solar system')
        system_timezone = config_dict.get('timezone', 'Asia/Karachi')
        
        # Ensure system exists
        cur.execute("SELECT COUNT(*) FROM systems WHERE system_id = ?", (system_id,))
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO systems (system_id, name, description, timezone)
                VALUES (?, ?, ?, ?)
            """, (system_id, system_name, system_description, system_timezone))
            log.info(f"Created system from config.yaml: {system_id}")
        
        # ============= POPULATE ADAPTER BASE =============
        # Populate adapter_base with supported adapter types
        adapter_types = [
            ('powdrive', 'inverter', 'Powdrive Inverter Adapter', 'Adapter for Powdrive inverters'),
            ('senergy', 'inverter', 'Senergy Inverter Adapter', 'Adapter for Senergy inverters'),
            ('pytes', 'battery', 'Pytes Battery Adapter', 'Adapter for Pytes/Pylontech batteries'),
            ('jkbms_tcpip', 'battery', 'JK BMS TCP/IP Adapter', 'JK BMS via TCP/IP gateway'),
            ('jkbms_ble', 'battery', 'JK BMS Bluetooth Adapter', 'JK BMS via Bluetooth Low Energy'),
            ('iammeter', 'meter', 'IAMMeter Adapter', 'Adapter for IAMMeter energy meters'),
        ]
        
        for adapter_type, device_category, name, description in adapter_types:
            # Check if adapter_type already exists
            cur.execute("SELECT COUNT(*) FROM adapter_base WHERE adapter_type = ?", (adapter_type,))
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO adapter_base (adapter_type, device_category, name, description, config_schema, supported_transports)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (adapter_type, device_category, name, description, '{}', '[]'))
                log.debug(f"Added adapter_base entry: {adapter_type}")
        log.info("Populated adapter_base table")
        
        # ============= MIGRATE ARRAYS =============
        arrays_config = config_dict.get('arrays', [])
        for array_cfg in arrays_config:
            array_id = array_cfg.get('id')
            array_name = array_cfg.get('name', array_id)
            
            if not array_id:
                continue
            
            # Check if array exists
            cur.execute("SELECT COUNT(*) FROM arrays WHERE array_id = ?", (array_id,))
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO arrays (array_id, system_id, name)
                    VALUES (?, ?, ?)
                """, (array_id, system_id, array_name))
                log.info(f"Migrated array from config.yaml: {array_id}")
            else:
                # Update system_id and name if needed
                cur.execute("""
                    UPDATE arrays 
                    SET system_id = COALESCE(system_id, ?), name = COALESCE(name, ?)
                    WHERE array_id = ? AND (system_id IS NULL OR name IS NULL OR name = '')
                """, (system_id, array_name, array_id))
        
        # ============= MIGRATE INVERTERS =============
        inverters_config = config_dict.get('inverters', [])
        for inv_cfg in inverters_config:
            inverter_id = inv_cfg.get('id')
            if not inverter_id:
                continue
            
            array_id = inv_cfg.get('array_id')
            if not array_id:
                # Assign to default array if no array_id
                array_id = 'array1'
                log.warning(f"Inverter {inverter_id} has no array_id, assigning to {array_id}")
            
            inverter_name = inv_cfg.get('name', inverter_id)
            model = inv_cfg.get('model')
            serial_number = inv_cfg.get('serial_number')
            vendor = inv_cfg.get('vendor')
            phase_type = inv_cfg.get('phase_type')
            
            # Extract adapter config
            adapter_cfg = inv_cfg.get('adapter', {})
            adapter_type = adapter_cfg.get('type')
            adapter_id = f"{inverter_id}_adapter" if adapter_type else None
            
            # Create adapter instance if adapter config exists
            if adapter_type and adapter_id:
                config_json = json.dumps(adapter_cfg)
                cur.execute("""
                    INSERT OR REPLACE INTO adapters (adapter_id, adapter_type, device_category, device_id, device_type, config_json)
                    VALUES (?, ?, 'inverter', ?, 'inverter', ?)
                """, (adapter_id, adapter_type, inverter_id, config_json))
                log.debug(f"Created adapter for inverter {inverter_id}: {adapter_id}")
            
            # Check if inverter exists
            cur.execute("SELECT COUNT(*) FROM inverters WHERE inverter_id = ?", (inverter_id,))
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO inverters (inverter_id, array_id, system_id, adapter_id, name, model, serial_number, vendor, phase_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (inverter_id, array_id, system_id, adapter_id, inverter_name, model, serial_number, vendor, phase_type))
                log.info(f"Migrated inverter from config.yaml: {inverter_id}")
            else:
                # Update system_id and array_id if they're NULL
                cur.execute("""
                    UPDATE inverters 
                    SET system_id = ?, array_id = ?, adapter_id = COALESCE(adapter_id, ?)
                    WHERE inverter_id = ? AND (system_id IS NULL OR array_id IS NULL)
                """, (system_id, array_id, adapter_id, inverter_id))
        
        # ============= MIGRATE BATTERY ARRAYS =============
        battery_arrays_config = config_dict.get('battery_bank_arrays', [])
        for ba_cfg in battery_arrays_config:
            battery_array_id = ba_cfg.get('id')
            battery_array_name = ba_cfg.get('name', battery_array_id)
            
            if not battery_array_id:
                continue
            
            # Check if battery array exists
            cur.execute("SELECT COUNT(*) FROM battery_arrays WHERE battery_array_id = ?", (battery_array_id,))
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO battery_arrays (battery_array_id, system_id, name)
                    VALUES (?, ?, ?)
                """, (battery_array_id, system_id, battery_array_name))
                log.info(f"Migrated battery array from config.yaml: {battery_array_id}")
        
        # ============= MIGRATE BATTERY PACKS =============
        battery_banks_config = config_dict.get('battery_banks', [])
        for bank_cfg in battery_banks_config:
            pack_id = bank_cfg.get('id')
            if not pack_id:
                continue
            
            pack_name = bank_cfg.get('name', pack_id)
            chemistry = bank_cfg.get('chemistry')
            nominal_kwh = bank_cfg.get('nominal_kwh')
            max_charge_kw = bank_cfg.get('max_charge_kw')
            max_discharge_kw = bank_cfg.get('max_discharge_kw')
            
            # Find which battery array this pack belongs to
            battery_array_id = None
            for ba_cfg in battery_arrays_config:
                battery_bank_ids = ba_cfg.get('battery_bank_ids', [])
                if pack_id in battery_bank_ids:
                    battery_array_id = ba_cfg.get('id')
                    break
            
            if not battery_array_id:
                # Assign to default battery array
                battery_array_id = 'battery_array1'
                log.warning(f"Battery pack {pack_id} has no battery_array_id, assigning to {battery_array_id}")
            
            # Extract adapter configs (support both single adapter and failover adapters)
            adapters_list = []
            if 'adapters' in bank_cfg:
                # Failover adapters
                for adapter_entry in bank_cfg['adapters']:
                    adapter_cfg = adapter_entry.get('adapter', {})
                    priority = adapter_entry.get('priority', 1)
                    enabled = adapter_entry.get('enabled', True)
                    adapters_list.append((adapter_cfg, priority, enabled))
            elif 'adapter' in bank_cfg:
                # Single adapter
                adapters_list.append((bank_cfg['adapter'], 1, True))
            
            # First, ensure battery pack exists (needed for foreign key constraint)
            cur.execute("SELECT COUNT(*) FROM battery_packs WHERE pack_id = ?", (pack_id,))
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO battery_packs (pack_id, battery_array_id, system_id, name, chemistry, nominal_kwh, max_charge_kw, max_discharge_kw)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (pack_id, battery_array_id, system_id, pack_name, chemistry, nominal_kwh, max_charge_kw, max_discharge_kw))
                log.info(f"Migrated battery pack from config.yaml: {pack_id}")
            else:
                # Update battery_array_id and system_id if they're NULL
                cur.execute("""
                    UPDATE battery_packs 
                    SET battery_array_id = COALESCE(battery_array_id, ?), system_id = COALESCE(system_id, ?)
                    WHERE pack_id = ? AND (battery_array_id IS NULL OR system_id IS NULL)
                """, (battery_array_id, system_id, pack_id))
            
            # Create adapter instances (after battery pack exists)
            for idx, (adapter_cfg, priority, enabled) in enumerate(adapters_list):
                adapter_type = adapter_cfg.get('type')
                if not adapter_type:
                    continue
                
                adapter_id = f"{pack_id}_adapter_{idx + 1}" if len(adapters_list) > 1 else f"{pack_id}_adapter"
                config_json = json.dumps(adapter_cfg)
                
                # Create adapter instance
                cur.execute("""
                    INSERT OR REPLACE INTO adapters (adapter_id, adapter_type, device_category, device_id, device_type, priority, enabled, config_json)
                    VALUES (?, ?, 'battery', ?, 'battery_pack', ?, ?, ?)
                """, (adapter_id, adapter_type, pack_id, priority, 1 if enabled else 0, config_json))
                log.debug(f"Created adapter for battery pack {pack_id}: {adapter_id} (priority {priority})")
                
                # Link adapter to battery pack (now that both exist)
                cur.execute("""
                    INSERT OR REPLACE INTO battery_pack_adapters (pack_id, adapter_id, priority, enabled)
                    VALUES (?, ?, ?, ?)
                """, (pack_id, adapter_id, priority, 1 if enabled else 0))
            
            # Create battery units and cells if specified
            batteries_count = bank_cfg.get('batteries', 0)
            cells_per_battery = bank_cfg.get('cells_per_battery', 0)
            
            if batteries_count > 0:
                for battery_idx in range(batteries_count):
                    battery_id = f"{pack_id}_battery_{battery_idx}"
                    cur.execute("""
                        INSERT OR IGNORE INTO batteries (battery_id, pack_id, battery_array_id, system_id, battery_index)
                        VALUES (?, ?, ?, ?, ?)
                    """, (battery_id, pack_id, battery_array_id, system_id, battery_idx))
                    
                    if cells_per_battery > 0:
                        for cell_idx in range(cells_per_battery):
                            cell_id = f"{battery_id}_cell_{cell_idx}"
                            cur.execute("""
                                INSERT OR IGNORE INTO battery_cells (cell_id, battery_id, pack_id, battery_array_id, system_id, cell_index)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (cell_id, battery_id, pack_id, battery_array_id, system_id, cell_idx))
        
        # ============= MIGRATE BATTERY ARRAY ATTACHMENTS =============
        attachments_config = config_dict.get('battery_bank_array_attachments', [])
        for att_cfg in attachments_config:
            battery_array_id = att_cfg.get('battery_bank_array_id')
            inverter_array_id = att_cfg.get('inverter_array_id')
            attached_since = att_cfg.get('attached_since', datetime.now().isoformat())
            detached_at = att_cfg.get('detached_at')
            
            if not battery_array_id or not inverter_array_id:
                continue
            
            # Check if attachment exists
            cur.execute("""
                SELECT COUNT(*) FROM battery_array_attachments 
                WHERE battery_array_id = ? AND inverter_array_id = ? AND attached_since = ?
            """, (battery_array_id, inverter_array_id, attached_since))
            
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO battery_array_attachments (battery_array_id, inverter_array_id, attached_since, detached_at)
                    VALUES (?, ?, ?, ?)
                """, (battery_array_id, inverter_array_id, attached_since, detached_at))
                log.info(f"Migrated battery array attachment: {battery_array_id} -> {inverter_array_id}")
        
        # ============= MIGRATE METERS =============
        meters_config = config_dict.get('meters', [])
        for meter_cfg in meters_config:
            meter_id = meter_cfg.get('id')
            if not meter_id:
                continue
            
            meter_name = meter_cfg.get('name', meter_id)
            model = meter_cfg.get('model')
            meter_type = meter_cfg.get('type', 'grid')
            attachment_target = meter_cfg.get('attachment_target') or meter_cfg.get('array_id')
            
            # Determine array_id from attachment_target
            array_id = None
            if attachment_target and attachment_target != 'home' and attachment_target != 'system':
                array_id = attachment_target
            
            # Extract adapter config
            adapter_cfg = meter_cfg.get('adapter', {})
            adapter_type = adapter_cfg.get('type')
            adapter_id = f"{meter_id}_adapter" if adapter_type else None
            
            # Create adapter instance if adapter config exists
            if adapter_type and adapter_id:
                config_json = json.dumps(adapter_cfg)
                cur.execute("""
                    INSERT OR REPLACE INTO adapters (adapter_id, adapter_type, device_category, device_id, device_type, config_json)
                    VALUES (?, ?, 'meter', ?, 'meter', ?)
                """, (adapter_id, adapter_type, meter_id, config_json))
                log.debug(f"Created adapter for meter {meter_id}: {adapter_id}")
            
            # Check if meter exists
            cur.execute("SELECT COUNT(*) FROM meters WHERE meter_id = ?", (meter_id,))
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO meters (meter_id, system_id, array_id, adapter_id, name, model, type, attachment_target)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (meter_id, system_id, array_id, adapter_id, meter_name, model, meter_type, attachment_target))
                log.info(f"Migrated meter from config.yaml: {meter_id}")
            else:
                # Update system_id if it's NULL
                cur.execute("""
                    UPDATE meters 
                    SET system_id = COALESCE(system_id, ?), adapter_id = COALESCE(adapter_id, ?)
                    WHERE meter_id = ? AND system_id IS NULL
                """, (system_id, adapter_id, meter_id))
        
        con.commit()
        log.info("Config.yaml to database migration completed successfully")
        
    except Exception as e:
        con.rollback()
        log.error(f"Config.yaml to database migration failed: {e}", exc_info=True)
        raise
    finally:
        con.close()


def migrate_production_data(db_path: str, system_id: str = "system") -> None:
    """
    Migrate existing production data to new hierarchy structure.
    
    This function:
    1. Links existing arrays to system_id
    2. Links existing battery_packs to battery_array_id and system_id
    3. Creates inverter entries from existing energy_samples data
    4. Links existing samples to system_id, array_id, etc.
    
    Args:
        db_path: Path to SQLite database
        system_id: System ID to use for migration (default: "system")
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    try:
        log.info(f"Starting production data migration for system_id='{system_id}'")
        
        # ============= 1. LINK EXISTING ARRAYS TO SYSTEM =============
        cur.execute("UPDATE arrays SET system_id = ? WHERE system_id IS NULL", (system_id,))
        updated = cur.rowcount
        if updated > 0:
            log.info(f"Linked {updated} arrays to system {system_id}")
        
        # ============= 2. LINK EXISTING BATTERY PACKS TO SYSTEM AND ARRAY =============
        # Update all battery packs to use the same system_id (fix any mismatches)
        cur.execute("""
            UPDATE battery_packs 
            SET system_id = ?
            WHERE system_id != ? OR system_id IS NULL
        """, (system_id, system_id))
        updated = cur.rowcount
        if updated > 0:
            log.info(f"Updated {updated} battery packs to system {system_id}")
        
        # If battery_array_id is NULL, assign to default battery array
        cur.execute("""
            UPDATE battery_packs 
            SET battery_array_id = 'battery_array1'
            WHERE battery_array_id IS NULL
        """)
        updated = cur.rowcount
        if updated > 0:
            log.info(f"Assigned {updated} battery packs to default battery array")
        
        # ============= 3. CREATE INVERTER ENTRIES FROM EXISTING DATA =============
        # Get unique inverter_ids from energy_samples
        cur.execute("SELECT DISTINCT inverter_id FROM energy_samples")
        inverter_ids = [row[0] for row in cur.fetchall()]
        
        for inverter_id in inverter_ids:
            # Check if inverter already exists
            cur.execute("SELECT COUNT(*) FROM inverters WHERE inverter_id = ?", (inverter_id,))
            if cur.fetchone()[0] > 0:
                continue
            
            # Try to find array_id from energy_samples
            cur.execute("SELECT array_id FROM energy_samples WHERE inverter_id = ? AND array_id IS NOT NULL LIMIT 1", (inverter_id,))
            row = cur.fetchone()
            array_id = row[0] if row else 'array1'  # Default to array1 if not found
            
            # Create inverter entry
            cur.execute("""
                INSERT INTO inverters (inverter_id, array_id, system_id, name)
                VALUES (?, ?, ?, ?)
            """, (inverter_id, array_id, system_id, inverter_id))
            log.info(f"Created inverter entry from production data: {inverter_id}")
        
        # ============= 6. LINK EXISTING SAMPLES TO SYSTEM_ID =============
        # This is handled by backfill_system_ids, but we can also do it here for completeness
        # The backfill function will be called separately
        
        con.commit()
        log.info("Production data migration completed successfully")
        
    except Exception as e:
        con.rollback()
        log.error(f"Production data migration failed: {e}", exc_info=True)
        raise
    finally:
        con.close()