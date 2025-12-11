import sqlite3
from solarhub.models import Telemetry
from solarhub.array_models import ArrayTelemetry
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from solarhub.timezone_utils import from_os_to_configured
from solarhub.database_migrations import migrate_to_arrays

log = logging.getLogger(__name__)
class DataLogger:
    def __init__(self, path: str = None):
        if path is None:
            base = os.path.expanduser("~/.solarhub")   # inside user home
            os.makedirs(base, exist_ok=True)
            path = os.path.join(base, "solarhub.db")
        self.path = path
        self._init()
        # Run migration to arrays schema
        try:
            migrate_to_arrays(self.path)
        except Exception as e:
            log.warning(f"Array migration may have already run or failed: {e}")
        
        # Run billing tables migration
        try:
            from solarhub.database_migrations import migrate_to_billing_tables
            migrate_to_billing_tables(self.path)
        except Exception as e:
            log.warning(f"Billing tables migration may have already run or failed: {e}")
        
        # Run device discovery migration
        try:
            from solarhub.database_migrations import migrate_to_device_discovery
            migrate_to_device_discovery(self.path)
        except Exception as e:
            log.warning(f"Device discovery migration may have already run or failed: {e}")
        
        # Run home billing migration
        try:
            from solarhub.database_migrations import migrate_to_home_billing
            migrate_to_home_billing(self.path)
        except Exception as e:
            log.warning(f"Home billing migration may have already run or failed: {e}")
        
        # Run Phase 1: Hierarchy schema migration
        try:
            from solarhub.database_migrations import (
                migrate_to_hierarchy_schema,
                create_default_system,
                backfill_system_ids,
                migrate_config_yaml_to_database,
                migrate_production_data
            )
            
            # Step 1: Create all new tables and add foreign keys
            try:
                migrate_to_hierarchy_schema(self.path)
            except sqlite3.DatabaseError as e:
                if "malformed" in str(e).lower() or "corrupt" in str(e).lower():
                    log.error(f"Database is corrupted: {e}")
                    log.error("Please restore from backup or recreate the database.")
                    log.error("Application will continue but may not function correctly.")
                    # Don't continue with other migration steps if database is corrupted
                    return
                raise
            
            # Step 2: Create default system if none exists
            create_default_system(self.path)
            
            # Step 3: Migrate config.yaml to database (if config.yaml exists and database is empty)
            # Check if we have any systems in database
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM systems")
            systems_count = cur.fetchone()[0]
            con.close()
            
            if systems_count == 0:
                # Database is empty, try to migrate from config.yaml
                try:
                    migrate_config_yaml_to_database(self.path)
                except Exception as e:
                    log.warning(f"Config.yaml migration failed (may not exist): {e}")
            
            # Step 4: Migrate production data
            migrate_production_data(self.path)
            
            # Step 5: Backfill system_ids in all tables
            backfill_system_ids(self.path)
            
            log.info("Phase 1: Hierarchy migration completed successfully")
        except Exception as e:
            log.error(f"Phase 1: Hierarchy migration failed: {e}", exc_info=True)
            # Don't raise - allow system to continue with existing structure
        
        # Step 6: Optional aggregation backfill (runs in background, doesn't block startup)
        try:
            from solarhub.aggregation_backfill import backfill_all_aggregated_tables
            import threading
            
            def run_backfill():
                """Run aggregation backfill in background thread."""
                try:
                    log.info("Starting aggregation backfill for historical data (last 30 days)")
                    backfill_all_aggregated_tables(self.path, days_back=30)
                    log.info("Aggregation backfill completed successfully")
                except Exception as e:
                    log.warning(f"Aggregation backfill failed (non-critical): {e}")
            
            # Start backfill in background thread to avoid blocking startup
            backfill_thread = threading.Thread(target=run_backfill, daemon=True)
            backfill_thread.start()
            log.info("Started aggregation backfill in background thread")
        except Exception as e:
            log.warning(f"Failed to start aggregation backfill (non-critical): {e}")
    
    def _init(self):
        log.info(f"Initializing database at: {self.path}")
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        
        # Create energy_samples table with all columns
        cur.execute("""
            CREATE TABLE IF NOT EXISTS energy_samples (
                ts TEXT NOT NULL,
                inverter_id TEXT NOT NULL,
                pv_power_w INTEGER,
                load_power_w INTEGER,
                grid_power_w INTEGER,
                batt_voltage_v REAL,
                batt_current_a REAL,
                soc REAL,
                battery_soc REAL,
                battery_voltage_v REAL,
                battery_current_a REAL,
                inverter_mode INTEGER,
                inverter_temp_c REAL
            )
        """)
        log.info("Created/verified energy_samples table with all columns")
        
        # Create pv_daily table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pv_daily (
                day TEXT NOT NULL,
                inverter_id TEXT NOT NULL,
                pv_kwh REAL NOT NULL,
                PRIMARY KEY(day, inverter_id)
            )
        """)
        log.info("Created/verified pv_daily table")

        # Create configuration table for persisting HA changes
        cur.execute("""
            CREATE TABLE IF NOT EXISTS configuration (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source TEXT NOT NULL
            )
        """)
        log.info("Created/verified configuration table")

        # Battery logging tables
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battery_bank_samples (
                ts TEXT NOT NULL,
                bank_id TEXT NOT NULL,
                voltage REAL,
                current REAL,
                temperature REAL,
                soc REAL,
                batteries_count INTEGER,
                cells_per_battery INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battery_unit_samples (
                ts TEXT NOT NULL,
                bank_id TEXT NOT NULL,
                power INTEGER NOT NULL,
                voltage REAL,
                current REAL,
                temperature REAL,
                soc REAL,
                basic_st TEXT,
                volt_st TEXT,
                current_st TEXT,
                temp_st TEXT,
                soh_st TEXT,
                coul_st TEXT,
                heater_st TEXT,
                bat_events INTEGER,
                power_events INTEGER,
                sys_events INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battery_cell_samples (
                ts TEXT NOT NULL,
                bank_id TEXT NOT NULL,
                power INTEGER NOT NULL,
                cell INTEGER NOT NULL,
                voltage REAL,
                temperature REAL,
                soc REAL,
                volt_st TEXT,
                temp_st TEXT
            )
        """)
        log.info("Created/verified battery tables")
        
        # Create users table for authentication
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        log.info("Created/verified users table")
        
        # Create user_sessions table for token-based authentication
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)")
        log.info("Created/verified user_sessions table")

        # Create meter_samples table for storing meter telemetry
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meter_samples (
                ts TEXT NOT NULL,
                meter_id TEXT NOT NULL,
                array_id TEXT,
                grid_power_w INTEGER,
                grid_voltage_v REAL,
                grid_current_a REAL,
                grid_frequency_hz REAL,
                grid_import_wh INTEGER,
                grid_export_wh INTEGER,
                energy_kwh REAL,
                power_factor REAL,
                voltage_phase_a REAL,
                voltage_phase_b REAL,
                voltage_phase_c REAL,
                current_phase_a REAL,
                current_phase_b REAL,
                current_phase_c REAL,
                power_phase_a INTEGER,
                power_phase_b INTEGER,
                power_phase_c INTEGER
            )
        """)
        log.info("Created/verified meter_samples table")

        # Create meter_daily table for daily import/export summaries
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meter_daily (
                day TEXT NOT NULL,
                meter_id TEXT NOT NULL,
                array_id TEXT,
                import_energy_kwh REAL NOT NULL DEFAULT 0,
                export_energy_kwh REAL NOT NULL DEFAULT 0,
                net_energy_kwh REAL NOT NULL DEFAULT 0,
                max_import_power_w INTEGER,
                max_export_power_w INTEGER,
                avg_voltage_v REAL,
                avg_current_a REAL,
                avg_frequency_hz REAL,
                sample_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(day, meter_id)
            )
        """)
        log.info("Created/verified meter_daily table")

        # Create indexes for efficient queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_meter_samples_ts 
            ON meter_samples(ts DESC, meter_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_meter_daily_day 
            ON meter_daily(day DESC, meter_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_meter_daily_meter 
            ON meter_daily(meter_id, day DESC)
        """)

        con.commit()
        con.close()
        log.info("Database initialization completed successfully")
    def _get_inverter_system_id(self, cur, inverter_id: str) -> Optional[str]:
        """Get system_id for an inverter from database."""
        try:
            cur.execute("SELECT system_id FROM inverters WHERE inverter_id = ?", (inverter_id,))
            result = cur.fetchone()
            if result:
                return result[0]
            # Fallback: try to get from array if inverter not in catalog
            cur.execute("""
                SELECT a.system_id FROM arrays a
                JOIN inverters i ON i.array_id = a.array_id
                WHERE i.inverter_id = ?
            """, (inverter_id,))
            result = cur.fetchone()
            if result:
                return result[0]
            # Final fallback: default system
            return 'system'
        except sqlite3.OperationalError:
            # Table might not exist yet
            return 'system'
    
    def _get_battery_pack_info(self, cur, pack_id: str) -> tuple:
        """Get system_id and battery_array_id for a battery pack from database."""
        try:
            cur.execute("SELECT system_id, battery_array_id FROM battery_packs WHERE pack_id = ?", (pack_id,))
            result = cur.fetchone()
            if result:
                return result[0], result[1]
            # Fallback: default system
            return 'system', None
        except sqlite3.OperationalError:
            # Table might not exist yet
            return 'system', None
    
    def _get_meter_system_id(self, cur, meter_id: str) -> Optional[str]:
        """Get system_id for a meter from database."""
        try:
            cur.execute("SELECT system_id FROM meters WHERE meter_id = ?", (meter_id,))
            result = cur.fetchone()
            if result:
                return result[0]
            # Fallback: default system
            return 'system'
        except sqlite3.OperationalError:
            # Table might not exist yet
            return 'system'
    
    def _get_array_system_id(self, cur, array_id: str) -> Optional[str]:
        """Get system_id for an array from database."""
        try:
            cur.execute("SELECT system_id FROM arrays WHERE array_id = ?", (array_id,))
            result = cur.fetchone()
            if result:
                return result[0]
            # Fallback: default system
            return 'system'
        except sqlite3.OperationalError:
            # Table might not exist yet
            return 'system'
    
    def insert_sample(self, inverter_id: str, tel: Telemetry):
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            # Use explicit column names to handle both old and new schema
            # Extract inverter_mode and inverter_temp_c from extra data if available
            inverter_mode = None
            inverter_temp_c = None
            if hasattr(tel, 'extra') and tel.extra:
                inverter_mode = tel.extra.get('inverter_mode')
                if isinstance(inverter_mode, str):
                    # Convert string mode to numeric value if needed
                    mode_map = {
                        "Initial mode": 0,
                        "Standby mode": 1,
                        "OnGrid mode": 3,
                        "OffGrid mode": 4,
                        "Fault mode": 5,
                        "Shutdown mode": 9
                    }
                    inverter_mode = mode_map.get(inverter_mode, inverter_mode)
                
                inverter_temp_c = tel.extra.get('inverter_temp_c') or tel.extra.get('inner_temperature')  # Prefer standardized ID
            
            # Convert timestamp from OS timezone to configured timezone
            # Parse the ISO string to datetime first
            tel_dt = datetime.fromisoformat(tel.ts)
            ts_configured = from_os_to_configured(tel_dt)
            
            # Get array_id from telemetry if available
            array_id = getattr(tel, 'array_id', None)
            
            # Get system_id from database
            system_id = self._get_inverter_system_id(cur, inverter_id)
            
            cur.execute("""
                INSERT INTO energy_samples 
                (ts, inverter_id, array_id, system_id, pv_power_w, load_power_w, grid_power_w, 
                 batt_voltage_v, batt_current_a, soc, battery_soc, battery_voltage_v, battery_current_a, inverter_mode, inverter_temp_c)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (ts_configured, inverter_id, array_id, system_id, tel.pv_power_w, tel.load_power_w, tel.grid_power_w,
                  tel.batt_voltage_v, tel.batt_current_a, tel.batt_soc_pct,
                  tel.batt_soc_pct, tel.batt_voltage_v, tel.batt_current_a, inverter_mode, inverter_temp_c))
            con.commit()
            log.debug(f"Successfully inserted telemetry sample for {inverter_id}")
        except Exception as e:
            log.error(f"Failed to insert telemetry sample for {inverter_id}: {e}")
            raise
        finally:
            con.close()
    def upsert_daily_pv(self, day: str, inverter_id: str, pv_kwh: float):
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute(
            "INSERT INTO pv_daily(day,inverter_id,pv_kwh) VALUES(?,?,?)\n"
            "ON CONFLICT(day,inverter_id) DO UPDATE SET pv_kwh=excluded.pv_kwh",
            (day, inverter_id, pv_kwh)
        )
        con.commit(); con.close()
    
    def insert_array_sample(self, array_tel: ArrayTelemetry):
        """Insert array-level aggregated telemetry sample."""
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            ts_configured = from_os_to_configured(datetime.fromisoformat(array_tel.ts))
            
            # Get system_id from database
            system_id = self._get_array_system_id(cur, array_tel.array_id)
            
            cur.execute("""
                INSERT OR REPLACE INTO array_samples 
                (ts, array_id, system_id, pv_power_w, load_power_w, grid_power_w, 
                 batt_power_w, batt_soc_pct, batt_voltage_v, batt_current_a)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                ts_configured, array_tel.array_id, system_id,
                array_tel.pv_power_w, array_tel.load_power_w, array_tel.grid_power_w,
                array_tel.batt_power_w, array_tel.batt_soc_pct,
                array_tel.batt_voltage_v, array_tel.batt_current_a
            ))
            con.commit()
            log.debug(f"Successfully inserted array sample for {array_tel.array_id}")
        except Exception as e:
            log.error(f"Failed to insert array sample for {array_tel.array_id}: {e}")
            raise
        finally:
            con.close()

    def insert_battery_bank_sample(self, bank_id: str, ts_iso: str, voltage, current, temperature, soc, batteries_count: int, cells_per_battery: int):
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            ts_configured = from_os_to_configured(datetime.fromisoformat(ts_iso))
            
            # Get system_id and battery_array_id from database
            system_id, battery_array_id = self._get_battery_pack_info(cur, bank_id)
            
            cur.execute(
                """
                INSERT INTO battery_bank_samples(ts, bank_id, system_id, battery_array_id, voltage, current, temperature, soc, batteries_count, cells_per_battery)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (ts_configured, bank_id, system_id, battery_array_id, voltage, current, temperature, soc, batteries_count, cells_per_battery),
            )
            con.commit()
        except Exception as e:
            log.error(f"Failed to insert battery bank sample: {e}")
            raise
        finally:
            con.close()

    def insert_battery_unit_samples(self, bank_id: str, ts_iso: str, devices: list):
        if not devices:
            return
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            ts_configured = from_os_to_configured(datetime.fromisoformat(ts_iso))
            rows = []
            for d in devices:
                rows.append(
                    (
                        ts_configured,
                        bank_id,
                        getattr(d, 'power', None) if not isinstance(d, dict) else d.get('power'),
                        getattr(d, 'voltage', None) if not isinstance(d, dict) else d.get('voltage'),
                        getattr(d, 'current', None) if not isinstance(d, dict) else d.get('current'),
                        getattr(d, 'temperature', None) if not isinstance(d, dict) else d.get('temperature'),
                        getattr(d, 'soc', None) if not isinstance(d, dict) else d.get('soc'),
                        (getattr(d, 'basic_st', None) if not isinstance(d, dict) else d.get('basic_st')),
                        (getattr(d, 'volt_st', None) if not isinstance(d, dict) else d.get('volt_st')),
                        (getattr(d, 'current_st', None) if not isinstance(d, dict) else d.get('current_st')),
                        (getattr(d, 'temp_st', None) if not isinstance(d, dict) else d.get('temp_st')),
                        (getattr(d, 'soh_st', None) if not isinstance(d, dict) else d.get('soh_st')),
                        (getattr(d, 'coul_st', None) if not isinstance(d, dict) else d.get('coul_st')),
                        (getattr(d, 'heater_st', None) if not isinstance(d, dict) else d.get('heater_st')),
                        (getattr(d, 'bat_events', None) if not isinstance(d, dict) else d.get('bat_events')),
                        (getattr(d, 'power_events', None) if not isinstance(d, dict) else d.get('power_events')),
                        (getattr(d, 'sys_events', None) if not isinstance(d, dict) else d.get('sys_events')),
                    )
                )
            cur.executemany(
                """
                INSERT INTO battery_unit_samples(
                    ts, bank_id, power, voltage, current, temperature, soc,
                    basic_st, volt_st, current_st, temp_st, soh_st, coul_st, heater_st,
                    bat_events, power_events, sys_events
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                rows,
            )
            con.commit()
        except Exception as e:
            log.error(f"Failed to insert battery unit samples: {e}")
            raise
        finally:
            con.close()

    def insert_inverter_setpoint(self, array_id: str, inverter_id: str, ts_iso: str, 
                                  action: str, target_w: int, headroom_w: Optional[int] = None, 
                                  unmet_w: int = 0):
        """Insert inverter power setpoint from power splitting."""
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            ts_configured = from_os_to_configured(datetime.fromisoformat(ts_iso))
            cur.execute(
                """
                INSERT OR REPLACE INTO inverter_setpoints(ts, array_id, inverter_id, action, target_w, headroom_w, unmet_w)
                VALUES(?,?,?,?,?,?,?)
                """,
                (ts_configured, array_id, inverter_id, action, target_w, headroom_w, unmet_w),
            )
            con.commit()
        except Exception as e:
            log.error(f"Failed to insert inverter setpoint: {e}")
            raise
        finally:
            con.close()

    def insert_battery_cell_samples(self, bank_id: str, ts_iso: str, cells_data: list):
        if not cells_data:
            return
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            ts_configured = from_os_to_configured(datetime.fromisoformat(ts_iso))
            rows = []
            for entry in cells_data:
                power = entry.get('power') if isinstance(entry, dict) else getattr(entry, 'power', None)
                cells = entry.get('cells') if isinstance(entry, dict) else getattr(entry, 'cells', [])
                for c in cells or []:
                    rows.append(
                        (
                            ts_configured,
                            bank_id,
                            power,  # Use power from entry level, not from cell
                            c.get('cell'),
                            c.get('voltage'),
                            c.get('temperature'),
                            c.get('soc'),
                            c.get('volt_st'),
                            c.get('temp_st'),
                        )
                    )
            if rows:
                cur.executemany(
                    """
                    INSERT INTO battery_cell_samples(
                        ts, bank_id, power, cell, voltage, temperature, soc, volt_st, temp_st
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    rows,
                )
                con.commit()
        except Exception as e:
            log.error(f"Failed to insert battery cell samples: {e}")
            raise
        finally:
            con.close()
    
    def get_config(self, key: str) -> str:
        """Get configuration value from database."""
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute("SELECT value FROM configuration WHERE key = ?", (key,))
        result = cur.fetchone()
        con.close()
        return result[0] if result else None
    
    def set_config(self, key: str, value: str, source: str = "home_assistant"):
        """Set configuration value in database."""
        from solarhub.timezone_utils import now_configured
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO configuration(key, value, updated_at, source) VALUES(?, ?, ?, ?)",
            (key, value, now_configured().isoformat(), source)
        )
        con.commit()
        con.close()
        log.info(f"Configuration updated: {key} = {value} (source: {source})")
    
    def get_all_configs(self) -> dict:
        """Get all configuration values from database."""
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute("SELECT key, value FROM configuration")
        results = cur.fetchall()
        con.close()
        return dict(results)
    
    def delete_config(self, key: str):
        """Delete configuration value from database."""
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute("DELETE FROM configuration WHERE key = ?", (key,))
        con.commit()
        con.close()
        log.info(f"Configuration deleted: {key}")
    
    def insert_meter_sample(self, meter_id: str, tel):
        """Insert meter telemetry sample into database."""
        from solarhub.schedulers.models import MeterTelemetry
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            ts_configured = from_os_to_configured(datetime.fromisoformat(tel.ts))
            
            # Get system_id from database
            system_id = self._get_meter_system_id(cur, meter_id)
            
            cur.execute("""
                INSERT INTO meter_samples 
                (ts, meter_id, array_id, system_id, grid_power_w, grid_voltage_v, grid_current_a, grid_frequency_hz,
                 grid_import_wh, grid_export_wh, energy_kwh, power_factor,
                 voltage_phase_a, voltage_phase_b, voltage_phase_c,
                 current_phase_a, current_phase_b, current_phase_c,
                 power_phase_a, power_phase_b, power_phase_c)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                ts_configured, meter_id, tel.array_id, system_id,
                tel.grid_power_w, tel.grid_voltage_v, tel.grid_current_a, tel.grid_frequency_hz,
                tel.grid_import_wh, tel.grid_export_wh, tel.energy_kwh, tel.power_factor,
                tel.voltage_phase_a, tel.voltage_phase_b, tel.voltage_phase_c,
                tel.current_phase_a, tel.current_phase_b, tel.current_phase_c,
                tel.power_phase_a, tel.power_phase_b, tel.power_phase_c
            ))
            con.commit()
            log.debug(f"Successfully inserted meter sample for {meter_id}")
        except Exception as e:
            log.error(f"Failed to insert meter sample for {meter_id}: {e}")
            raise
        finally:
            con.close()
    
    def upsert_array_hourly_energy(self, array_id: str, system_id: str, date: str, hour_start: int,
                                    solar_energy_kwh: Optional[float] = None,
                                    load_energy_kwh: Optional[float] = None,
                                    battery_charge_energy_kwh: Optional[float] = None,
                                    battery_discharge_energy_kwh: Optional[float] = None,
                                    grid_import_energy_kwh: Optional[float] = None,
                                    grid_export_energy_kwh: Optional[float] = None,
                                    avg_solar_power_w: Optional[float] = None,
                                    avg_load_power_w: Optional[float] = None,
                                    avg_battery_power_w: Optional[float] = None,
                                    avg_grid_power_w: Optional[float] = None,
                                    avg_soc_pct: Optional[float] = None,
                                    sample_count: int = 0):
        """Insert or update array hourly energy summary."""
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            cur.execute("""
                INSERT INTO array_hourly_energy 
                (array_id, system_id, date, hour_start, solar_energy_kwh, load_energy_kwh,
                 battery_charge_energy_kwh, battery_discharge_energy_kwh,
                 grid_import_energy_kwh, grid_export_energy_kwh,
                 avg_solar_power_w, avg_load_power_w, avg_battery_power_w, avg_grid_power_w,
                 avg_soc_pct, sample_count)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(array_id, date, hour_start) DO UPDATE SET
                    solar_energy_kwh = COALESCE(excluded.solar_energy_kwh, array_hourly_energy.solar_energy_kwh),
                    load_energy_kwh = COALESCE(excluded.load_energy_kwh, array_hourly_energy.load_energy_kwh),
                    battery_charge_energy_kwh = COALESCE(excluded.battery_charge_energy_kwh, array_hourly_energy.battery_charge_energy_kwh),
                    battery_discharge_energy_kwh = COALESCE(excluded.battery_discharge_energy_kwh, array_hourly_energy.battery_discharge_energy_kwh),
                    grid_import_energy_kwh = COALESCE(excluded.grid_import_energy_kwh, array_hourly_energy.grid_import_energy_kwh),
                    grid_export_energy_kwh = COALESCE(excluded.grid_export_energy_kwh, array_hourly_energy.grid_export_energy_kwh),
                    avg_solar_power_w = COALESCE(excluded.avg_solar_power_w, array_hourly_energy.avg_solar_power_w),
                    avg_load_power_w = COALESCE(excluded.avg_load_power_w, array_hourly_energy.avg_load_power_w),
                    avg_battery_power_w = COALESCE(excluded.avg_battery_power_w, array_hourly_energy.avg_battery_power_w),
                    avg_grid_power_w = COALESCE(excluded.avg_grid_power_w, array_hourly_energy.avg_grid_power_w),
                    avg_soc_pct = COALESCE(excluded.avg_soc_pct, array_hourly_energy.avg_soc_pct),
                    sample_count = excluded.sample_count
            """, (array_id, system_id, date, hour_start, solar_energy_kwh, load_energy_kwh,
                  battery_charge_energy_kwh, battery_discharge_energy_kwh,
                  grid_import_energy_kwh, grid_export_energy_kwh,
                  avg_solar_power_w, avg_load_power_w, avg_battery_power_w, avg_grid_power_w,
                  avg_soc_pct, sample_count))
            con.commit()
        except Exception as e:
            log.error(f"Failed to upsert array hourly energy: {e}")
            raise
        finally:
            con.close()
    
    def upsert_system_hourly_energy(self, system_id: str, date: str, hour_start: int,
                                     solar_energy_kwh: Optional[float] = None,
                                     load_energy_kwh: Optional[float] = None,
                                     battery_charge_energy_kwh: Optional[float] = None,
                                     battery_discharge_energy_kwh: Optional[float] = None,
                                     grid_import_energy_kwh: Optional[float] = None,
                                     grid_export_energy_kwh: Optional[float] = None,
                                     avg_solar_power_w: Optional[float] = None,
                                     avg_load_power_w: Optional[float] = None,
                                     avg_battery_power_w: Optional[float] = None,
                                     avg_grid_power_w: Optional[float] = None,
                                     avg_soc_pct: Optional[float] = None,
                                     sample_count: int = 0):
        """Insert or update system hourly energy summary."""
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            cur.execute("""
                INSERT INTO system_hourly_energy 
                (system_id, date, hour_start, solar_energy_kwh, load_energy_kwh,
                 battery_charge_energy_kwh, battery_discharge_energy_kwh,
                 grid_import_energy_kwh, grid_export_energy_kwh,
                 avg_solar_power_w, avg_load_power_w, avg_battery_power_w, avg_grid_power_w,
                 avg_soc_pct, sample_count)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(system_id, date, hour_start) DO UPDATE SET
                    solar_energy_kwh = COALESCE(excluded.solar_energy_kwh, system_hourly_energy.solar_energy_kwh),
                    load_energy_kwh = COALESCE(excluded.load_energy_kwh, system_hourly_energy.load_energy_kwh),
                    battery_charge_energy_kwh = COALESCE(excluded.battery_charge_energy_kwh, system_hourly_energy.battery_charge_energy_kwh),
                    battery_discharge_energy_kwh = COALESCE(excluded.battery_discharge_energy_kwh, system_hourly_energy.battery_discharge_energy_kwh),
                    grid_import_energy_kwh = COALESCE(excluded.grid_import_energy_kwh, system_hourly_energy.grid_import_energy_kwh),
                    grid_export_energy_kwh = COALESCE(excluded.grid_export_energy_kwh, system_hourly_energy.grid_export_energy_kwh),
                    avg_solar_power_w = COALESCE(excluded.avg_solar_power_w, system_hourly_energy.avg_solar_power_w),
                    avg_load_power_w = COALESCE(excluded.avg_load_power_w, system_hourly_energy.avg_load_power_w),
                    avg_battery_power_w = COALESCE(excluded.avg_battery_power_w, system_hourly_energy.avg_battery_power_w),
                    avg_grid_power_w = COALESCE(excluded.avg_grid_power_w, system_hourly_energy.avg_grid_power_w),
                    avg_soc_pct = COALESCE(excluded.avg_soc_pct, system_hourly_energy.avg_soc_pct),
                    sample_count = excluded.sample_count
            """, (system_id, date, hour_start, solar_energy_kwh, load_energy_kwh,
                  battery_charge_energy_kwh, battery_discharge_energy_kwh,
                  grid_import_energy_kwh, grid_export_energy_kwh,
                  avg_solar_power_w, avg_load_power_w, avg_battery_power_w, avg_grid_power_w,
                  avg_soc_pct, sample_count))
            con.commit()
        except Exception as e:
            log.error(f"Failed to upsert system hourly energy: {e}")
            raise
        finally:
            con.close()
    
    def upsert_battery_bank_hourly(self, pack_id: str, battery_array_id: str, system_id: str,
                                    date: str, hour_start: int,
                                    charge_energy_kwh: Optional[float] = None,
                                    discharge_energy_kwh: Optional[float] = None,
                                    net_energy_kwh: Optional[float] = None,
                                    avg_power_w: Optional[float] = None,
                                    avg_soc_pct: Optional[float] = None,
                                    avg_voltage_v: Optional[float] = None,
                                    avg_current_a: Optional[float] = None,
                                    avg_temperature_c: Optional[float] = None,
                                    sample_count: int = 0):
        """Insert or update battery bank hourly summary."""
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            cur.execute("""
                INSERT INTO battery_bank_hourly 
                (pack_id, battery_array_id, system_id, date, hour_start,
                 charge_energy_kwh, discharge_energy_kwh, net_energy_kwh,
                 avg_power_w, avg_soc_pct, avg_voltage_v, avg_current_a, avg_temperature_c, sample_count)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(pack_id, date, hour_start) DO UPDATE SET
                    charge_energy_kwh = COALESCE(excluded.charge_energy_kwh, battery_bank_hourly.charge_energy_kwh),
                    discharge_energy_kwh = COALESCE(excluded.discharge_energy_kwh, battery_bank_hourly.discharge_energy_kwh),
                    net_energy_kwh = COALESCE(excluded.net_energy_kwh, battery_bank_hourly.net_energy_kwh),
                    avg_power_w = COALESCE(excluded.avg_power_w, battery_bank_hourly.avg_power_w),
                    avg_soc_pct = COALESCE(excluded.avg_soc_pct, battery_bank_hourly.avg_soc_pct),
                    avg_voltage_v = COALESCE(excluded.avg_voltage_v, battery_bank_hourly.avg_voltage_v),
                    avg_current_a = COALESCE(excluded.avg_current_a, battery_bank_hourly.avg_current_a),
                    avg_temperature_c = COALESCE(excluded.avg_temperature_c, battery_bank_hourly.avg_temperature_c),
                    sample_count = excluded.sample_count
            """, (pack_id, battery_array_id, system_id, date, hour_start,
                  charge_energy_kwh, discharge_energy_kwh, net_energy_kwh,
                  avg_power_w, avg_soc_pct, avg_voltage_v, avg_current_a, avg_temperature_c, sample_count))
            con.commit()
        except Exception as e:
            log.error(f"Failed to upsert battery bank hourly: {e}")
            raise
        finally:
            con.close()
    
    def upsert_meter_daily(self, day: str, meter_id: str, import_kwh: float, export_kwh: float, 
                           net_kwh: float, max_import_w: Optional[int] = None, 
                           max_export_w: Optional[int] = None, array_id: Optional[str] = None,
                           avg_voltage: Optional[float] = None, avg_current: Optional[float] = None,
                           avg_frequency: Optional[float] = None, sample_count: int = 0):
        """Insert or update daily meter summary."""
        from solarhub.timezone_utils import now_configured
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            updated_at = now_configured().isoformat()
            
            cur.execute("""
                INSERT INTO meter_daily 
                (day, meter_id, array_id, import_energy_kwh, export_energy_kwh, net_energy_kwh,
                 max_import_power_w, max_export_power_w, avg_voltage_v, avg_current_a, 
                 avg_frequency_hz, sample_count, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(day, meter_id) DO UPDATE SET
                    import_energy_kwh = excluded.import_energy_kwh,
                    export_energy_kwh = excluded.export_energy_kwh,
                    net_energy_kwh = excluded.net_energy_kwh,
                    max_import_power_w = excluded.max_import_power_w,
                    max_export_power_w = excluded.max_export_power_w,
                    avg_voltage_v = excluded.avg_voltage_v,
                    avg_current_a = excluded.avg_current_a,
                    avg_frequency_hz = excluded.avg_frequency_hz,
                    sample_count = excluded.sample_count,
                    updated_at = excluded.updated_at
            """, (
                day, meter_id, array_id, import_kwh, export_kwh, net_kwh,
                max_import_w, max_export_w, avg_voltage, avg_current, avg_frequency,
                sample_count, updated_at
            ))
            con.commit()
            log.debug(f"Successfully upserted daily summary for {meter_id} on {day}")
        except Exception as e:
            log.error(f"Failed to upsert daily summary for {meter_id}: {e}")
            raise
        finally:
            con.close()
    
    def get_meter_daily_summary(self, meter_id: str, start_date: str, end_date: str) -> list:
        """Get daily summaries for a meter within a date range."""
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            cur.execute("""
                SELECT day, import_energy_kwh, export_energy_kwh, net_energy_kwh,
                       max_import_power_w, max_export_power_w, avg_voltage_v, 
                       avg_current_a, avg_frequency_hz, sample_count
                FROM meter_daily
                WHERE meter_id = ? AND day >= ? AND day <= ?
                ORDER BY day ASC
            """, (meter_id, start_date, end_date))
            rows = cur.fetchall()
            con.close()
            
            return [
                {
                    "day": row[0],
                    "import_energy_kwh": row[1],
                    "export_energy_kwh": row[2],
                    "net_energy_kwh": row[3],
                    "max_import_power_w": row[4],
                    "max_export_power_w": row[5],
                    "avg_voltage_v": row[6],
                    "avg_current_a": row[7],
                    "avg_frequency_hz": row[8],
                    "sample_count": row[9]
                }
                for row in rows
            ]
        except Exception as e:
            log.error(f"Failed to get daily summary for {meter_id}: {e}")
            return []
