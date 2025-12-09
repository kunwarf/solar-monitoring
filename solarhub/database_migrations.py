"""
Database migration scripts for array and battery pack support.
"""
import sqlite3
import logging
from typing import Optional, Dict

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