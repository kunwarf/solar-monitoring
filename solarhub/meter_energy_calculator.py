"""
Meter Energy Calculator Module

This module provides functions to calculate hourly import/export energy (kWh) from meter
power (watts) data using Riemann sum integration, similar to EnergyCalculator but for meters.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from solarhub.timezone_utils import get_configured_timezone, to_configured

log = logging.getLogger(__name__)


class MeterEnergyCalculator:
    """Calculate hourly import/export energy from meter power data using Riemann sum integration."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_meter_energy_table()
    
    def _init_meter_energy_table(self):
        """Initialize the meter_hourly_energy table for storing calculated energy data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
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
            
            # Create indexes for efficient queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_meter_hourly_energy_meter_date 
                ON meter_hourly_energy(meter_id, date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_meter_hourly_energy_date_hour 
                ON meter_hourly_energy(date, hour_start)
            """)
            
            conn.commit()
            log.info("Initialized meter_hourly_energy table with indexes")
            
        except Exception as e:
            log.error(f"Failed to initialize meter_hourly_energy table: {e}")
            raise
        finally:
            conn.close()
    
    def calculate_hourly_energy(self, meter_id: str, start_time: datetime, end_time: datetime) -> Dict[str, float]:
        """
        Calculate hourly import/export energy from meter power data using Riemann sum integration.
        
        Args:
            meter_id: The meter ID
            start_time: Start time for calculation (will be converted to configured timezone)
            end_time: End time for calculation (will be converted to configured timezone)
            
        Returns:
            Dictionary with import_energy_kwh and export_energy_kwh
        """
        # Convert times to configured timezone
        start_time_configured = to_configured(start_time)
        end_time_configured = to_configured(end_time)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get power data for the time period
            query = """
                SELECT 
                    ts,
                    grid_power_w
                FROM meter_samples 
                WHERE ts >= ? AND ts <= ?
                AND meter_id = ?
                ORDER BY ts
            """
            
            # Use ISO format with space separator to match SQLite TEXT timestamps
            start_str = start_time_configured.isoformat(sep=' ')
            end_str = end_time_configured.isoformat(sep=' ')
            cursor.execute(query, (start_str, end_str, meter_id))
            rows = cursor.fetchall()
            
            if not rows:
                log.warning(f"No meter power data found for {meter_id} between {start_time} and {end_time}")
                return {'import_energy_kwh': 0.0, 'export_energy_kwh': 0.0, 'avg_power_w': 0.0, 'sample_count': 0}
            
            # Convert to DataFrame for easier processing
            df = pd.DataFrame(rows, columns=['ts', 'grid_power_w'])
            df['ts'] = pd.to_datetime(df['ts'])
            
            # Convert timestamps to configured timezone
            configured_tz = get_configured_timezone()
            df['ts'] = df['ts'].dt.tz_convert(configured_tz) if df['ts'].dt.tz is not None else df['ts'].dt.tz_localize('UTC').dt.tz_convert(configured_tz)
            df = df.sort_values('ts')
            
            # Calculate time differences for Riemann sum
            df['time_diff_hours'] = df['ts'].diff().dt.total_seconds() / 3600.0
            df['time_diff_hours'] = df['time_diff_hours'].fillna(0)
            
            # Calculate energy using Riemann sum (power * time)
            # Positive power = import, negative power = export
            df['import_energy_kwh'] = (df['grid_power_w'].where(df['grid_power_w'] > 0, 0) * df['time_diff_hours']) / 1000.0
            df['export_energy_kwh'] = (df['grid_power_w'].where(df['grid_power_w'] < 0, 0).abs() * df['time_diff_hours']) / 1000.0
            
            # Sum up the energy for the period
            energy_data = {
                'import_energy_kwh': df['import_energy_kwh'].sum(),
                'export_energy_kwh': df['export_energy_kwh'].sum(),
                'avg_power_w': df['grid_power_w'].mean(),
                'sample_count': len(df)
            }
            
            log.debug(f"Calculated meter energy for {meter_id}: import={energy_data['import_energy_kwh']:.3f} kWh, export={energy_data['export_energy_kwh']:.3f} kWh")
            return energy_data
            
        except Exception as e:
            log.error(f"Failed to calculate meter hourly energy: {e}", exc_info=True)
            return {'import_energy_kwh': 0.0, 'export_energy_kwh': 0.0, 'avg_power_w': 0.0, 'sample_count': 0}
        finally:
            conn.close()
    
    def store_hourly_energy(self, meter_id: str, hour_start: datetime, energy_data: Dict[str, float]):
        """Store calculated energy data in the meter_hourly_energy table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Convert hour_start to configured timezone
            hour_start_configured = to_configured(hour_start)
            
            # Extract date and hour from hour_start in configured timezone
            date = hour_start_configured.strftime('%Y-%m-%d')
            hour = hour_start_configured.hour
            
            cursor.execute("""
                INSERT OR REPLACE INTO meter_hourly_energy 
                (meter_id, date, hour_start, import_energy_kwh, export_energy_kwh,
                 avg_power_w, sample_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                meter_id,
                date,
                hour,
                energy_data['import_energy_kwh'],
                energy_data['export_energy_kwh'],
                energy_data['avg_power_w'],
                energy_data['sample_count']
            ))
            
            conn.commit()
            log.debug(f"Stored hourly meter energy data for {meter_id} at {hour_start}")
            
        except Exception as e:
            log.error(f"Failed to store hourly meter energy data: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def get_hourly_energy_data(self, meter_ids: List[str], start_time: datetime, end_time: datetime) -> List[Dict]:
        """
        Get hourly energy data from the database for one or more meters.
        
        Args:
            meter_ids: List of meter IDs (will be aggregated)
            start_time: Start time for query
            end_time: End time for query
            
        Returns:
            List of hourly energy data dictionaries, aggregated across all meters
        """
        if not meter_ids:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Convert times to configured timezone
            start_time_configured = to_configured(start_time)
            end_time_configured = to_configured(end_time)
            start_date_str = start_time_configured.strftime('%Y-%m-%d')
            end_date_str = end_time_configured.strftime('%Y-%m-%d')
            
            # Build query with placeholders for meter IDs
            placeholders = ','.join(['?'] * len(meter_ids))
            query = f"""
                SELECT 
                    date,
                    hour_start,
                    SUM(import_energy_kwh) as import_energy_kwh,
                    SUM(export_energy_kwh) as export_energy_kwh,
                    AVG(avg_power_w) as avg_power_w,
                    SUM(sample_count) as sample_count
                FROM meter_hourly_energy 
                WHERE meter_id IN ({placeholders})
                AND date >= ? 
                AND date <= ?
                GROUP BY date, hour_start
                ORDER BY date, hour_start
            """
            
            cursor.execute(query, meter_ids + [start_date_str, end_date_str])
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                date, hour_start, import_kwh, export_kwh, avg_power_w, sample_count = row
                
                # Format hour as HH:00
                hour = f"{hour_start:02d}:00"
                # Include date+hour for precise matching in fallback logic
                date_hour = f"{date} {hour}"
                
                data.append({
                    'time': hour,  # Keep for backward compatibility
                    'date_hour': date_hour,  # New: date+hour for precise matching
                    'date': date,  # Include date separately
                    'hour': hour_start,  # Include hour as integer
                    'import': round(import_kwh or 0, 3),
                    'export': round(export_kwh or 0, 3),
                    'avg_power_w': round(avg_power_w or 0),
                    'sample_count': sample_count or 0
                })
            
            return data
            
        except Exception as e:
            log.error(f"Failed to get hourly meter energy data: {e}", exc_info=True)
            return []
        finally:
            conn.close()
    
    def calculate_and_store_hourly_energy(self, meter_id: str, hour_start: datetime):
        """Calculate and store energy data for a specific hour."""
        hour_end = hour_start + timedelta(hours=1)
        
        # Calculate energy for this hour
        energy_data = self.calculate_hourly_energy(meter_id, hour_start, hour_end)
        
        # Store in database
        self.store_hourly_energy(meter_id, hour_start, energy_data)
        
        return energy_data
    
    def backfill_hourly_energy_for_date_range(
        self, 
        meter_id: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> int:
        """
        Backfill hourly energy data for a meter for a date range.
        
        Args:
            meter_id: The meter ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Number of hours backfilled
        """
        configured_tz = get_configured_timezone()
        start_date_configured = to_configured(start_date)
        end_date_configured = to_configured(end_date)
        
        hours_backfilled = 0
        current_date = start_date_configured.replace(hour=0, minute=0, second=0, microsecond=0)
        end_datetime = end_date_configured.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        log.info(f"Backfilling meter hourly energy for {meter_id} from {start_date_configured} to {end_date_configured}")
        
        while current_date <= end_datetime:
            # Backfill all 24 hours for this day
            for hour in range(24):
                hour_start = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                
                try:
                    self.calculate_and_store_hourly_energy(meter_id, hour_start)
                    hours_backfilled += 1
                except Exception as e:
                    log.debug(f"Backfill failed for {meter_id} at {hour_start}: {e}")
            
            # Move to next day
            current_date += timedelta(days=1)
            current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        log.info(f"Backfilled {hours_backfilled} hours of meter energy data for {meter_id}")
        return hours_backfilled
    
    def get_missing_hours(
        self,
        meter_ids: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, List[str]]:
        """
        Get list of missing hours for given meters in the time range.
        
        Args:
            meter_ids: List of meter IDs
            start_time: Start time
            end_time: End time
            
        Returns:
            Dictionary mapping hour string (YYYY-MM-DD HH:00) to list of meter IDs that are missing
        """
        if not meter_ids:
            return {}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            start_time_configured = to_configured(start_time)
            end_time_configured = to_configured(end_time)
            start_date_str = start_time_configured.strftime('%Y-%m-%d')
            end_date_str = end_time_configured.strftime('%Y-%m-%d')
            
            # Get all hours in the range
            all_hours = set()
            current = start_time_configured.replace(minute=0, second=0, microsecond=0)
            while current <= end_time_configured:
                hour_str = current.strftime('%Y-%m-%d %H:00')
                all_hours.add(hour_str)
                current += timedelta(hours=1)
            
            # Get existing hours from database
            placeholders = ','.join(['?'] * len(meter_ids))
            query = f"""
                SELECT date || ' ' || printf('%02d', hour_start) || ':00' as hour_str, meter_id
                FROM meter_hourly_energy
                WHERE meter_id IN ({placeholders})
                AND date >= ?
                AND date <= ?
            """
            
            cursor.execute(query, meter_ids + [start_date_str, end_date_str])
            rows = cursor.fetchall()
            
            # Build set of existing hours per meter
            existing_hours = {meter_id: set() for meter_id in meter_ids}
            for hour_str, meter_id in rows:
                if meter_id in existing_hours:
                    existing_hours[meter_id].add(hour_str)
            
            # Find missing hours
            missing_hours = {}
            for meter_id in meter_ids:
                meter_missing = []
                for hour_str in all_hours:
                    if hour_str not in existing_hours[meter_id]:
                        meter_missing.append(hour_str)
                        if hour_str not in missing_hours:
                            missing_hours[hour_str] = []
                        missing_hours[hour_str].append(meter_id)
            
            return missing_hours
            
        except Exception as e:
            log.error(f"Failed to get missing hours: {e}", exc_info=True)
            return {}
        finally:
            conn.close()

