"""
Energy Calculator Module

This module provides functions to calculate energy (kWh) from power (watts) data
using Riemann sum integration and stores the results in a dedicated energy table.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
from solarhub.timezone_utils import get_configured_timezone, to_configured

log = logging.getLogger(__name__)

class EnergyCalculator:
    """Calculate energy from power data using Riemann sum integration."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_energy_table()
    
    def _init_energy_table(self):
        """Initialize the hourly_energy table for storing calculated energy data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
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
            
            # Create indexes for efficient queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hourly_energy_inverter_date 
                ON hourly_energy(inverter_id, date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hourly_energy_date_hour 
                ON hourly_energy(date, hour_start)
            """)
            
            conn.commit()
            log.info("Initialized hourly_energy table with indexes")
            
        except Exception as e:
            log.error(f"Failed to initialize hourly_energy table: {e}")
            raise
        finally:
            conn.close()
    
    def calculate_hourly_energy(self, inverter_id: str, start_time: datetime, end_time: datetime) -> Dict[str, float]:
        """
        Calculate hourly energy from power data using Riemann sum integration.
        
        Args:
            inverter_id: The inverter ID
            start_time: Start time for calculation (will be converted to configured timezone)
            end_time: End time for calculation (will be converted to configured timezone)
            
        Returns:
            Dictionary with energy values in kWh
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
                    pv_power_w,
                    load_power_w,
                    batt_voltage_v,
                    batt_current_a,
                    grid_power_w
                FROM energy_samples 
                WHERE ts >= ? AND ts <= ?
                AND inverter_id = ?
                ORDER BY ts
            """
            
            # Use ISO format with space separator to match SQLite TEXT timestamps stored (e.g., 'YYYY-MM-DD HH:MM:SS+05:00')
            start_str = start_time_configured.isoformat(sep=' ')
            end_str = end_time_configured.isoformat(sep=' ')
            cursor.execute(query, (start_str, end_str, inverter_id))
            rows = cursor.fetchall()
            
            if not rows:
                log.warning(f"No power data found for {inverter_id} between {start_time} and {end_time}")
                return self._empty_energy_dict()
            
            # Convert to DataFrame for easier processing
            df = pd.DataFrame(rows, columns=['ts', 'pv_power_w', 'load_power_w', 'batt_voltage_v', 'batt_current_a', 'grid_power_w'])
            df['ts'] = pd.to_datetime(df['ts'])
            
            # Convert timestamps to configured timezone
            configured_tz = get_configured_timezone()
            df['ts'] = df['ts'].dt.tz_convert(configured_tz) if df['ts'].dt.tz is not None else df['ts'].dt.tz_localize('UTC').dt.tz_convert(configured_tz)
            df = df.sort_values('ts')
            
            # Calculate battery power from voltage and current
            df['battery_power_w'] = df['batt_voltage_v'] * df['batt_current_a']
            
            # Calculate time differences for Riemann sum
            df['time_diff_hours'] = df['ts'].diff().dt.total_seconds() / 3600.0
            df['time_diff_hours'] = df['time_diff_hours'].fillna(0)
            
            # Calculate energy using Riemann sum (power * time)
            df['solar_energy_kwh'] = (df['pv_power_w'] * df['time_diff_hours']) / 1000.0
            df['load_energy_kwh'] = (df['load_power_w'] * df['time_diff_hours']) / 1000.0
            df['battery_energy_kwh'] = (df['battery_power_w'] * df['time_diff_hours']) / 1000.0
            df['grid_energy_kwh'] = (df['grid_power_w'] * df['time_diff_hours']) / 1000.0
            
            # Separate battery charge and discharge
            df['battery_charge_energy_kwh'] = df['battery_energy_kwh'].where(df['battery_energy_kwh'] > 0, 0)
            df['battery_discharge_energy_kwh'] = df['battery_energy_kwh'].where(df['battery_energy_kwh'] < 0, 0).abs()
            
            # Separate grid import and export
            df['grid_import_energy_kwh'] = df['grid_energy_kwh'].where(df['grid_energy_kwh'] > 0, 0)
            df['grid_export_energy_kwh'] = df['grid_energy_kwh'].where(df['grid_energy_kwh'] < 0, 0).abs()
            
            # Sum up the energy for the period
            energy_data = {
                'solar_energy_kwh': df['solar_energy_kwh'].sum(),
                'load_energy_kwh': df['load_energy_kwh'].sum(),
                'battery_charge_energy_kwh': df['battery_charge_energy_kwh'].sum(),
                'battery_discharge_energy_kwh': df['battery_discharge_energy_kwh'].sum(),
                'grid_import_energy_kwh': df['grid_import_energy_kwh'].sum(),
                'grid_export_energy_kwh': df['grid_export_energy_kwh'].sum(),
                'avg_solar_power_w': df['pv_power_w'].mean(),
                'avg_load_power_w': df['load_power_w'].mean(),
                'avg_battery_power_w': df['battery_power_w'].mean(),
                'avg_grid_power_w': df['grid_power_w'].mean(),
                'sample_count': len(df)
            }
            
            log.info(f"Calculated energy for {inverter_id}: {energy_data}")
            return energy_data
            
        except Exception as e:
            log.error(f"Failed to calculate hourly energy: {e}", exc_info=True)
            return self._empty_energy_dict()
        finally:
            conn.close()
    
    def _get_inverter_system_id_and_array_id(self, cursor, inverter_id: str) -> tuple:
        """Get system_id and array_id for an inverter from database."""
        try:
            cursor.execute("SELECT system_id, array_id FROM inverters WHERE inverter_id = ?", (inverter_id,))
            result = cursor.fetchone()
            if result:
                return result[0], result[1]
            # Fallback: try to get from array if inverter not in catalog
            cursor.execute("""
                SELECT a.system_id, a.array_id FROM arrays a
                JOIN energy_samples e ON e.array_id = a.array_id
                WHERE e.inverter_id = ?
                LIMIT 1
            """, (inverter_id,))
            result = cursor.fetchone()
            if result:
                return result[0], result[1]
            # Final fallback: default system
            return 'system', None
        except sqlite3.OperationalError:
            # Table might not exist yet
            return 'system', None
    
    def store_hourly_energy(self, inverter_id: str, hour_start: datetime, energy_data: Dict[str, float]):
        """Store calculated energy data in the hourly_energy table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Convert hour_start to configured timezone
            hour_start_configured = to_configured(hour_start)
            
            # Extract date and hour from hour_start in configured timezone
            date = hour_start_configured.strftime('%Y-%m-%d')
            hour = hour_start_configured.hour
            
            # Get system_id and array_id from database
            system_id, array_id = self._get_inverter_system_id_and_array_id(cursor, inverter_id)
            
            cursor.execute("""
                INSERT OR REPLACE INTO hourly_energy 
                (inverter_id, array_id, system_id, date, hour_start, solar_energy_kwh, load_energy_kwh, 
                 battery_charge_energy_kwh, battery_discharge_energy_kwh,
                 grid_import_energy_kwh, grid_export_energy_kwh,
                 avg_solar_power_w, avg_load_power_w, avg_battery_power_w, avg_grid_power_w,
                 sample_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inverter_id,
                array_id,
                system_id,
                date,
                hour,
                energy_data['solar_energy_kwh'],
                energy_data['load_energy_kwh'],
                energy_data['battery_charge_energy_kwh'],
                energy_data['battery_discharge_energy_kwh'],
                energy_data['grid_import_energy_kwh'],
                energy_data['grid_export_energy_kwh'],
                energy_data['avg_solar_power_w'],
                energy_data['avg_load_power_w'],
                energy_data['avg_battery_power_w'],
                energy_data['avg_grid_power_w'],
                energy_data['sample_count']
            ))
            
            conn.commit()
            log.debug(f"Stored hourly energy data for {inverter_id} at {hour_start}")
            
        except Exception as e:
            log.error(f"Failed to store hourly energy data: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def get_hourly_energy_data(self, inverter_id: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get hourly energy data from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Convert times to configured timezone
            start_time_configured = to_configured(start_time)
            end_time_configured = to_configured(end_time)
            start_date_str = start_time_configured.strftime('%Y-%m-%d')
            end_date_str = end_time_configured.strftime('%Y-%m-%d')
            
            # Handle "all" inverter_id by aggregating across all inverters
            if inverter_id == "all":
                # Query to aggregate across all inverters, grouped by date and hour
                # Note: For power values, we sum them (representing total array power)
                # For energy values, we also sum them (representing total array energy)
                query = """
                    SELECT 
                        date,
                        hour_start,
                        SUM(solar_energy_kwh) as solar_energy_kwh,
                        SUM(load_energy_kwh) as load_energy_kwh,
                        SUM(battery_charge_energy_kwh) as battery_charge_energy_kwh,
                        SUM(battery_discharge_energy_kwh) as battery_discharge_energy_kwh,
                        SUM(grid_import_energy_kwh) as grid_import_energy_kwh,
                        SUM(grid_export_energy_kwh) as grid_export_energy_kwh,
                        SUM(avg_solar_power_w) as avg_solar_power_w,
                        SUM(avg_load_power_w) as avg_load_power_w,
                        SUM(avg_battery_power_w) as avg_battery_power_w,
                        SUM(avg_grid_power_w) as avg_grid_power_w,
                        SUM(sample_count) as sample_count
                    FROM hourly_energy 
                    WHERE date >= ? 
                    AND date <= ?
                    GROUP BY date, hour_start
                    ORDER BY date, hour_start
                """
                
                cursor.execute(query, (start_date_str, end_date_str))
            else:
                # Single inverter query
                query = """
                    SELECT 
                        date,
                        hour_start,
                        solar_energy_kwh,
                        load_energy_kwh,
                        battery_charge_energy_kwh,
                        battery_discharge_energy_kwh,
                        grid_import_energy_kwh,
                        grid_export_energy_kwh,
                        avg_solar_power_w,
                        avg_load_power_w,
                        avg_battery_power_w,
                        avg_grid_power_w,
                        sample_count
                    FROM hourly_energy 
                    WHERE inverter_id = ? 
                    AND date >= ? 
                    AND date <= ?
                    ORDER BY date, hour_start
                """
                
                cursor.execute(query, (inverter_id, start_date_str, end_date_str))
            
            rows = cursor.fetchall()
            
            log.debug(f"get_hourly_energy_data: inverter_id={inverter_id}, "
                     f"start={start_time_configured}, end={end_time_configured}, "
                     f"rows_returned={len(rows)}")
            
            data = []
            for row in rows:
                date, hour_start, solar_kwh, load_kwh, batt_charge_kwh, batt_discharge_kwh, grid_import_kwh, grid_export_kwh, avg_solar_w, avg_load_w, avg_batt_w, avg_grid_w, sample_count = row
                
                # Format hour as HH:00
                hour = f"{hour_start:02d}:00"
                # Include date+hour for precise matching in fallback logic
                date_hour = f"{date} {hour}"
                
                data.append({
                    'time': hour,  # Keep for backward compatibility
                    'date_hour': date_hour,  # New: date+hour for precise matching
                    'date': date,  # Include date separately
                    'hour': hour_start,  # Include hour as integer
                    'solar': round(solar_kwh or 0, 3),
                    'load': round(load_kwh or 0, 3),
                    'battery_charge': round(batt_charge_kwh or 0, 3),
                    'battery_discharge': round(batt_discharge_kwh or 0, 3),
                    'grid_import': round(grid_import_kwh or 0, 3),
                    'grid_export': round(grid_export_kwh or 0, 3),
                    'avg_solar_power_w': round(avg_solar_w or 0),
                    'avg_load_power_w': round(avg_load_w or 0),
                    'avg_battery_power_w': round(avg_batt_w or 0),
                    'avg_grid_power_w': round(avg_grid_w or 0),
                    'sample_count': sample_count or 0
                })
            
            return data
            
        except Exception as e:
            log.error(f"Failed to get hourly energy data: {e}", exc_info=True)
            return []
        finally:
            conn.close()
    
    def calculate_and_store_hourly_energy(self, inverter_id: str, hour_start: datetime):
        """Calculate and store energy data for a specific hour."""
        hour_end = hour_start + timedelta(hours=1)
        
        # Calculate energy for this hour
        energy_data = self.calculate_hourly_energy(inverter_id, hour_start, hour_end)
        
        # Store in database
        self.store_hourly_energy(inverter_id, hour_start, energy_data)
        
        return energy_data
    
    def _empty_energy_dict(self) -> Dict[str, float]:
        """Return empty energy dictionary with all fields set to 0."""
        return {
            'solar_energy_kwh': 0.0,
            'load_energy_kwh': 0.0,
            'battery_charge_energy_kwh': 0.0,
            'battery_discharge_energy_kwh': 0.0,
            'grid_import_energy_kwh': 0.0,
            'grid_export_energy_kwh': 0.0,
            'avg_solar_power_w': 0.0,
            'avg_load_power_w': 0.0,
            'avg_battery_power_w': 0.0,
            'avg_grid_power_w': 0.0,
            'sample_count': 0
        }
    
    def get_daily_energy_summary(self, inverter_id: str, date) -> Dict[str, float]:
        """Get daily energy summary for a specific date."""
        # Handle both date and datetime objects
        if hasattr(date, 'replace') and hasattr(date, 'hour'):
            # datetime object - convert to configured timezone
            date_configured = to_configured(date)
            date_str = date_configured.strftime('%Y-%m-%d')
        else:
            # date object - assume it's already in configured timezone
            date_str = date.strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    SUM(solar_energy_kwh) as total_solar,
                    SUM(load_energy_kwh) as total_load,
                    SUM(battery_charge_energy_kwh) as total_battery_charge,
                    SUM(battery_discharge_energy_kwh) as total_battery_discharge,
                    SUM(grid_import_energy_kwh) as total_grid_import,
                    SUM(grid_export_energy_kwh) as total_grid_export,
                    AVG(avg_solar_power_w) as avg_solar_power,
                    AVG(avg_load_power_w) as avg_load_power,
                    AVG(avg_battery_power_w) as avg_battery_power,
                    AVG(avg_grid_power_w) as avg_grid_power,
                    SUM(sample_count) as total_samples
                FROM hourly_energy 
                WHERE inverter_id = ? 
                AND date = ?
            """
            
            cursor.execute(query, (inverter_id, date_str))
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'total_solar_kwh': row[0] or 0.0,
                    'total_load_kwh': row[1] or 0.0,
                    'total_battery_charge_kwh': row[2] or 0.0,
                    'total_battery_discharge_kwh': row[3] or 0.0,
                    'total_grid_import_kwh': row[4] or 0.0,
                    'total_grid_export_kwh': row[5] or 0.0,
                    'avg_solar_power_w': row[6] or 0.0,
                    'avg_load_power_w': row[7] or 0.0,
                    'avg_battery_power_w': row[8] or 0.0,
                    'avg_grid_power_w': row[9] or 0.0,
                    'total_samples': row[10] or 0
                }
            else:
                return self._empty_energy_dict()
                
        except Exception as e:
            log.error(f"Failed to get daily energy summary: {e}", exc_info=True)
            return self._empty_energy_dict()
        finally:
            conn.close()
    
    def ensure_24_hour_data(self, inverter_id: str, date: datetime) -> List[Dict]:
        """Ensure we have data for all 24 hours of a day, filling missing hours with zeros."""
        # Convert date to configured timezone
        date_configured = to_configured(date)
        date_str = date_configured.strftime('%Y-%m-%d')
        
        # Get existing data for the day
        start_time = date_configured.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        existing_data = self.get_hourly_energy_data(inverter_id, start_time, end_time)
        
        # Create a map of existing hours
        existing_hours = {int(item['time'].split(':')[0]): item for item in existing_data}
        
        # Create 24-hour data structure
        complete_data = []
        for hour in range(24):
            time_str = f"{hour:02d}:00"
            if hour in existing_hours:
                complete_data.append(existing_hours[hour])
            else:
                # Fill missing hour with zeros
                complete_data.append({
                    'time': time_str,
                    'solar': 0.0,
                    'load': 0.0,
                    'battery_charge': 0.0,
                    'battery_discharge': 0.0,
                    'grid_import': 0.0,
                    'grid_export': 0.0,
                    'avg_solar_power_w': 0.0,
                    'avg_load_power_w': 0.0,
                    'avg_battery_power_w': 0.0,
                    'avg_grid_power_w': 0.0,
                    'sample_count': 0
                })
        
        return complete_data
    
    def calculate_array_hourly_energy(self, array_id: str, inverter_ids: List[str], start_time: datetime, end_time: datetime) -> Dict[str, float]:
        """
        Calculate hourly energy for an array by aggregating data from multiple inverters.
        
        Args:
            array_id: The array ID
            inverter_ids: List of inverter IDs in this array
            start_time: Start time for calculation
            end_time: End time for calculation
            
        Returns:
            Dictionary with aggregated energy values in kWh
        """
        if not inverter_ids:
            log.warning(f"No inverters provided for array {array_id}")
            return self._empty_energy_dict()
        
        # Calculate energy for each inverter
        array_energy = self._empty_energy_dict()
        total_samples = 0
        
        for inverter_id in inverter_ids:
            try:
                inv_energy = self.calculate_hourly_energy(inverter_id, start_time, end_time)
                # Sum up all energy values
                for key in array_energy:
                    if key != 'sample_count':
                        array_energy[key] += inv_energy.get(key, 0.0)
                total_samples += inv_energy.get('sample_count', 0)
            except Exception as e:
                log.warning(f"Failed to calculate energy for inverter {inverter_id} in array {array_id}: {e}")
                continue
        
        array_energy['sample_count'] = total_samples
        
        log.info(f"Calculated array energy for {array_id}: {array_energy}")
        return array_energy
    
    def get_array_hourly_energy_data(self, array_id: str, inverter_ids: List[str], start_time: datetime, end_time: datetime) -> List[Dict]:
        """
        Get hourly energy data for an array by aggregating data from multiple inverters.
        
        Args:
            array_id: The array ID
            inverter_ids: List of inverter IDs in this array
            start_time: Start time for query
            end_time: End time for query
            
        Returns:
            List of hourly energy data dictionaries
        """
        if not inverter_ids:
            return []
        
        # Get hourly data for each inverter
        all_hourly_data = {}
        
        for inverter_id in inverter_ids:
            try:
                inv_data = self.get_hourly_energy_data(inverter_id, start_time, end_time)
                for hour_data in inv_data:
                    hour = hour_data['time']
                    if hour not in all_hourly_data:
                        all_hourly_data[hour] = {
                            'time': hour,
                            'solar': 0.0,
                            'load': 0.0,
                            'battery_charge': 0.0,
                            'battery_discharge': 0.0,
                            'grid_import': 0.0,
                            'grid_export': 0.0,
                            'avg_solar_power_w': 0.0,
                            'avg_load_power_w': 0.0,
                            'avg_battery_power_w': 0.0,
                            'avg_grid_power_w': 0.0,
                            'sample_count': 0
                        }
                    
                    # Aggregate values
                    all_hourly_data[hour]['solar'] += hour_data.get('solar', 0.0)
                    all_hourly_data[hour]['load'] += hour_data.get('load', 0.0)
                    all_hourly_data[hour]['battery_charge'] += hour_data.get('battery_charge', 0.0)
                    all_hourly_data[hour]['battery_discharge'] += hour_data.get('battery_discharge', 0.0)
                    all_hourly_data[hour]['grid_import'] += hour_data.get('grid_import', 0.0)
                    all_hourly_data[hour]['grid_export'] += hour_data.get('grid_export', 0.0)
                    all_hourly_data[hour]['sample_count'] += hour_data.get('sample_count', 0)
                    
                    # For average powers, we'll calculate weighted average later
                    # For now, just sum (we'll divide by inverter count if needed)
                    all_hourly_data[hour]['avg_solar_power_w'] += hour_data.get('avg_solar_power_w', 0.0)
                    all_hourly_data[hour]['avg_load_power_w'] += hour_data.get('avg_load_power_w', 0.0)
                    all_hourly_data[hour]['avg_battery_power_w'] += hour_data.get('avg_battery_power_w', 0.0)
                    all_hourly_data[hour]['avg_grid_power_w'] += hour_data.get('avg_grid_power_w', 0.0)
            except Exception as e:
                log.warning(f"Failed to get hourly energy data for inverter {inverter_id} in array {array_id}: {e}")
                continue
        
        # Convert to sorted list
        result = sorted(all_hourly_data.values(), key=lambda x: x['time'])
        
        # Round values
        for hour_data in result:
            for key in ['solar', 'load', 'battery_charge', 'battery_discharge', 'grid_import', 'grid_export']:
                hour_data[key] = round(hour_data[key], 3)
            for key in ['avg_solar_power_w', 'avg_load_power_w', 'avg_battery_power_w', 'avg_grid_power_w']:
                hour_data[key] = round(hour_data[key], 0)
        
        return result
    
    def get_array_daily_energy_summary(self, array_id: str, inverter_ids: List[str], date) -> Dict[str, float]:
        """
        Get daily energy summary for an array by aggregating data from multiple inverters.
        
        Args:
            array_id: The array ID
            inverter_ids: List of inverter IDs in this array
            date: Date for summary
            
        Returns:
            Dictionary with aggregated daily energy summary
        """
        if not inverter_ids:
            return self._empty_energy_dict()
        
        # Get daily summary for each inverter
        array_summary = self._empty_energy_dict()
        total_samples = 0
        
        for inverter_id in inverter_ids:
            try:
                inv_summary = self.get_daily_energy_summary(inverter_id, date)
                # Sum up all energy values
                array_summary['solar_energy_kwh'] += inv_summary.get('total_solar_kwh', 0.0)
                array_summary['load_energy_kwh'] += inv_summary.get('total_load_kwh', 0.0)
                array_summary['battery_charge_energy_kwh'] += inv_summary.get('total_battery_charge_kwh', 0.0)
                array_summary['battery_discharge_energy_kwh'] += inv_summary.get('total_battery_discharge_kwh', 0.0)
                array_summary['grid_import_energy_kwh'] += inv_summary.get('total_grid_import_kwh', 0.0)
                array_summary['grid_export_energy_kwh'] += inv_summary.get('total_grid_export_kwh', 0.0)
                
                # For average powers, we'll use the sum (representing total array power)
                array_summary['avg_solar_power_w'] += inv_summary.get('avg_solar_power_w', 0.0)
                array_summary['avg_load_power_w'] += inv_summary.get('avg_load_power_w', 0.0)
                array_summary['avg_battery_power_w'] += inv_summary.get('avg_battery_power_w', 0.0)
                array_summary['avg_grid_power_w'] += inv_summary.get('avg_grid_power_w', 0.0)
                
                total_samples += inv_summary.get('total_samples', 0)
            except Exception as e:
                log.warning(f"Failed to get daily summary for inverter {inverter_id} in array {array_id}: {e}")
                continue
        
        array_summary['sample_count'] = total_samples
        
        return array_summary