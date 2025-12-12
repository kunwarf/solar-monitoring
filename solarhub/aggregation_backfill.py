"""
Aggregation Backfill: Populate aggregated tables from existing sample data.
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from solarhub.energy_calculator import EnergyCalculator
from solarhub.timezone_utils import to_configured

log = logging.getLogger(__name__)


def backfill_array_hourly_energy(db_path: str, array_id: str, system_id: str, inverter_ids: List[str], 
                                 start_date: datetime, end_date: datetime):
    """
    Backfill array_hourly_energy table from hourly_energy table.
    
    Args:
        db_path: Path to database
        array_id: Array ID
        system_id: System ID
        inverter_ids: List of inverter IDs in this array
        start_date: Start date for backfill
        end_date: End date for backfill
    """
    if not inverter_ids:
        log.warning(f"No inverters provided for array {array_id}")
        return
    
    energy_calc = EnergyCalculator(db_path)
    
    # Iterate through each hour in the date range
    current_hour = start_date.replace(minute=0, second=0, microsecond=0)
    end_hour = end_date.replace(minute=0, second=0, microsecond=0)
    
    log.info(f"Backfilling array hourly energy for {array_id} from {current_hour} to {end_hour}")
    
    while current_hour <= end_hour:
        try:
            energy_calc.calculate_and_store_array_hourly_energy(
                array_id, system_id, inverter_ids, current_hour
            )
        except Exception as e:
            log.error(f"Failed to backfill array hourly energy for {array_id} at {current_hour}: {e}")
        
        current_hour += timedelta(hours=1)


def backfill_system_hourly_energy(db_path: str, system_id: str, array_ids: List[str],
                                  start_date: datetime, end_date: datetime):
    """
    Backfill system_hourly_energy table from array_hourly_energy table.
    
    Args:
        db_path: Path to database
        system_id: System ID
        array_ids: List of array IDs in this system
        start_date: Start date for backfill
        end_date: End date for backfill
    """
    if not array_ids:
        log.warning(f"No arrays provided for system {system_id}")
        return
    
    energy_calc = EnergyCalculator(db_path)
    
    # Iterate through each hour in the date range
    current_hour = start_date.replace(minute=0, second=0, microsecond=0)
    end_hour = end_date.replace(minute=0, second=0, microsecond=0)
    
    log.info(f"Backfilling system hourly energy for {system_id} from {current_hour} to {end_hour}")
    
    while current_hour <= end_hour:
        try:
            energy_calc.calculate_and_store_system_hourly_energy(
                system_id, array_ids, current_hour
            )
        except Exception as e:
            log.error(f"Failed to backfill system hourly energy for {system_id} at {current_hour}: {e}")
        
        current_hour += timedelta(hours=1)


def backfill_all_aggregated_tables(db_path: str, days_back: int = 30):
    """
    Backfill all aggregated tables from existing sample data.
    
    This function:
    1. Finds all arrays and their inverters from the database
    2. Backfills array_hourly_energy from hourly_energy
    3. Backfills system_hourly_energy from array_hourly_energy
    
    Args:
        db_path: Path to database
        days_back: Number of days to backfill (default: 30)
    """
    log.info(f"Starting backfill of aggregated tables for last {days_back} days")
    
    # Use timeout for database connection
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()
    
    try:
        # Get all arrays with their system_id and inverter_ids
        cursor.execute("""
            SELECT a.array_id, a.system_id, GROUP_CONCAT(i.inverter_id) as inverter_ids
            FROM arrays a
            LEFT JOIN inverters i ON i.array_id = a.array_id
            GROUP BY a.array_id, a.system_id
        """)
        
        arrays_data = cursor.fetchall()
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        # Backfill array hourly energy
        for array_row in arrays_data:
            array_id, system_id, inverter_ids_str = array_row
            if not inverter_ids_str:
                log.warning(f"Array {array_id} has no inverters, skipping")
                continue
            
            inverter_ids = inverter_ids_str.split(',')
            backfill_array_hourly_energy(
                db_path, array_id, system_id, inverter_ids, start_date, end_date
            )
        
        # Get all systems with their array_ids
        cursor.execute("""
            SELECT system_id, GROUP_CONCAT(array_id) as array_ids
            FROM arrays
            GROUP BY system_id
        """)
        
        systems_data = cursor.fetchall()
        
        # Backfill system hourly energy
        for system_row in systems_data:
            system_id, array_ids_str = system_row
            if not array_ids_str:
                log.warning(f"System {system_id} has no arrays, skipping")
                continue
            
            array_ids = array_ids_str.split(',')
            backfill_system_hourly_energy(
                db_path, system_id, array_ids, start_date, end_date
            )
        
        log.info("Completed backfill of aggregated tables")
        
    except Exception as e:
        log.error(f"Failed to backfill aggregated tables: {e}", exc_info=True)
        raise
    finally:
        conn.close()

