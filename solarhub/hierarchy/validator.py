"""
Hierarchy validation module.

Validates that the database hierarchy is properly structured before allowing
the application to proceed.
"""
import sqlite3
import logging
from typing import List, Tuple, Dict, Any

log = logging.getLogger(__name__)


class HierarchyValidationError(Exception):
    """Raised when hierarchy validation fails."""
    pass


def validate_hierarchy(db_path: str) -> Tuple[bool, List[str]]:
    """
    Validate the database hierarchy structure.
    
    Checks:
    1. All systems exist and are valid
    2. All arrays have valid system_id references
    3. All battery_arrays have valid system_id references
    4. All inverters have valid array_id and system_id references
    5. All battery_packs have valid battery_array_id and system_id references
    6. All meters have valid system_id references
    7. All adapters have valid adapter_type references (foreign key to adapter_base)
    8. All battery_pack_adapters have valid pack_id and adapter_id references
    9. All battery_array_attachments have valid battery_array_id and inverter_array_id references
    10. No orphaned records (entities without parents)
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    try:
        # Enable foreign key constraints
        cur.execute("PRAGMA foreign_keys = ON")
        
        # ============= 1. VALIDATE SYSTEMS =============
        cur.execute("SELECT system_id FROM systems")
        system_ids = {row[0] for row in cur.fetchall()}
        
        if not system_ids:
            errors.append("No systems found in database. At least one system must exist.")
        
        # ============= 2. VALIDATE ARRAYS =============
        cur.execute("""
            SELECT array_id, system_id 
            FROM arrays 
            WHERE system_id IS NULL OR system_id NOT IN (SELECT system_id FROM systems)
        """)
        invalid_arrays = cur.fetchall()
        for row in invalid_arrays:
            errors.append(f"Array {row['array_id']} has invalid or NULL system_id: {row['system_id']}")
        
        # ============= 3. VALIDATE BATTERY ARRAYS =============
        cur.execute("""
            SELECT battery_array_id, system_id 
            FROM battery_arrays 
            WHERE system_id IS NULL OR system_id NOT IN (SELECT system_id FROM systems)
        """)
        invalid_battery_arrays = cur.fetchall()
        for row in invalid_battery_arrays:
            errors.append(f"Battery array {row['battery_array_id']} has invalid or NULL system_id: {row['system_id']}")
        
        # ============= 4. VALIDATE INVERTERS =============
        cur.execute("""
            SELECT inverter_id, array_id, system_id 
            FROM inverters 
            WHERE array_id IS NULL 
               OR array_id NOT IN (SELECT array_id FROM arrays)
               OR system_id IS NULL 
               OR system_id NOT IN (SELECT system_id FROM systems)
        """)
        invalid_inverters = cur.fetchall()
        for row in invalid_inverters:
            errors.append(f"Inverter {row['inverter_id']} has invalid array_id ({row['array_id']}) or system_id ({row['system_id']})")
        
        # Check that inverter system_id matches array system_id
        cur.execute("""
            SELECT i.inverter_id, i.array_id, i.system_id, a.system_id as array_system_id
            FROM inverters i
            LEFT JOIN arrays a ON i.array_id = a.array_id
            WHERE i.system_id != a.system_id
        """)
        mismatched_inverters = cur.fetchall()
        for row in mismatched_inverters:
            errors.append(f"Inverter {row['inverter_id']} system_id ({row['system_id']}) doesn't match array {row['array_id']} system_id ({row['array_system_id']})")
        
        # ============= 5. VALIDATE BATTERY PACKS =============
        cur.execute("""
            SELECT pack_id, battery_array_id, system_id 
            FROM battery_packs 
            WHERE battery_array_id IS NULL 
               OR battery_array_id NOT IN (SELECT battery_array_id FROM battery_arrays)
               OR system_id IS NULL 
               OR system_id NOT IN (SELECT system_id FROM systems)
        """)
        invalid_battery_packs = cur.fetchall()
        for row in invalid_battery_packs:
            errors.append(f"Battery pack {row['pack_id']} has invalid battery_array_id ({row['battery_array_id']}) or system_id ({row['system_id']})")
        
        # Check that battery_pack system_id matches battery_array system_id
        cur.execute("""
            SELECT bp.pack_id, bp.battery_array_id, bp.system_id, ba.system_id as array_system_id
            FROM battery_packs bp
            LEFT JOIN battery_arrays ba ON bp.battery_array_id = ba.battery_array_id
            WHERE bp.system_id != ba.system_id
        """)
        mismatched_battery_packs = cur.fetchall()
        for row in mismatched_battery_packs:
            errors.append(f"Battery pack {row['pack_id']} system_id ({row['system_id']}) doesn't match battery_array {row['battery_array_id']} system_id ({row['array_system_id']})")
        
        # ============= 6. VALIDATE METERS =============
        cur.execute("""
            SELECT meter_id, system_id 
            FROM meters 
            WHERE system_id IS NULL 
               OR system_id NOT IN (SELECT system_id FROM systems)
        """)
        invalid_meters = cur.fetchall()
        for row in invalid_meters:
            errors.append(f"Meter {row['meter_id']} has invalid or NULL system_id: {row['system_id']}")
        
        # ============= 7. VALIDATE ADAPTERS =============
        cur.execute("""
            SELECT adapter_id, adapter_type 
            FROM adapters 
            WHERE adapter_type IS NULL 
               OR adapter_type NOT IN (SELECT adapter_type FROM adapter_base)
        """)
        invalid_adapters = cur.fetchall()
        for row in invalid_adapters:
            errors.append(f"Adapter {row['adapter_id']} has invalid or NULL adapter_type: {row['adapter_type']}")
        
        # ============= 8. VALIDATE BATTERY PACK ADAPTERS =============
        cur.execute("""
            SELECT pack_id, adapter_id 
            FROM battery_pack_adapters 
            WHERE pack_id NOT IN (SELECT pack_id FROM battery_packs)
               OR adapter_id NOT IN (SELECT adapter_id FROM adapters)
        """)
        invalid_pack_adapters = cur.fetchall()
        for row in invalid_pack_adapters:
            errors.append(f"Battery pack adapter link: pack_id {row['pack_id']} or adapter_id {row['adapter_id']} is invalid")
        
        # ============= 9. VALIDATE BATTERY ARRAY ATTACHMENTS =============
        cur.execute("""
            SELECT battery_array_id, inverter_array_id 
            FROM battery_array_attachments 
            WHERE battery_array_id NOT IN (SELECT battery_array_id FROM battery_arrays)
               OR inverter_array_id NOT IN (SELECT array_id FROM arrays)
        """)
        invalid_attachments = cur.fetchall()
        for row in invalid_attachments:
            errors.append(f"Battery array attachment: battery_array_id {row['battery_array_id']} or inverter_array_id {row['inverter_array_id']} is invalid")
        
        # Check that attached arrays belong to the same system
        cur.execute("""
            SELECT baa.battery_array_id, baa.inverter_array_id, ba.system_id as battery_array_system, a.system_id as inverter_array_system
            FROM battery_array_attachments baa
            LEFT JOIN battery_arrays ba ON baa.battery_array_id = ba.battery_array_id
            LEFT JOIN arrays a ON baa.inverter_array_id = a.array_id
            WHERE ba.system_id != a.system_id
        """)
        mismatched_attachments = cur.fetchall()
        for row in mismatched_attachments:
            errors.append(f"Battery array attachment: battery_array {row['battery_array_id']} (system {row['battery_array_system']}) and inverter_array {row['inverter_array_id']} (system {row['inverter_array_system']}) belong to different systems")
        
        # ============= 10. CHECK FOR ORPHANED RECORDS =============
        # Check for batteries without packs
        cur.execute("""
            SELECT battery_id, pack_id 
            FROM batteries 
            WHERE pack_id NOT IN (SELECT pack_id FROM battery_packs)
        """)
        orphaned_batteries = cur.fetchall()
        for row in orphaned_batteries:
            errors.append(f"Battery {row['battery_id']} references non-existent pack_id: {row['pack_id']}")
        
        # Check for battery cells without batteries
        cur.execute("""
            SELECT cell_id, battery_id 
            FROM battery_cells 
            WHERE battery_id NOT IN (SELECT battery_id FROM batteries)
        """)
        orphaned_cells = cur.fetchall()
        for row in orphaned_cells:
            errors.append(f"Battery cell {row['cell_id']} references non-existent battery_id: {row['battery_id']}")
        
        # ============= 11. CHECK SYSTEM_ID CONSISTENCY =============
        # Ensure all entities in a system use the same system_id
        # This is already checked above, but we can add a summary check
        if system_ids:
            for system_id in system_ids:
                # Check arrays
                cur.execute("SELECT COUNT(*) FROM arrays WHERE system_id = ?", (system_id,))
                array_count = cur.fetchone()[0]
                
                # Check battery_arrays
                cur.execute("SELECT COUNT(*) FROM battery_arrays WHERE system_id = ?", (system_id,))
                battery_array_count = cur.fetchone()[0]
                
                # Check inverters
                cur.execute("SELECT COUNT(*) FROM inverters WHERE system_id = ?", (system_id,))
                inverter_count = cur.fetchone()[0]
                
                # Check battery_packs
                cur.execute("SELECT COUNT(*) FROM battery_packs WHERE system_id = ?", (system_id,))
                battery_pack_count = cur.fetchone()[0]
                
                # Check meters
                cur.execute("SELECT COUNT(*) FROM meters WHERE system_id = ?", (system_id,))
                meter_count = cur.fetchone()[0]
                
                log.debug(f"System {system_id}: {array_count} arrays, {battery_array_count} battery_arrays, {inverter_count} inverters, {battery_pack_count} battery_packs, {meter_count} meters")
        
        is_valid = len(errors) == 0
        return is_valid, errors
        
    except Exception as e:
        log.error(f"Error during hierarchy validation: {e}", exc_info=True)
        errors.append(f"Validation error: {str(e)}")
        return False, errors
    finally:
        con.close()


def validate_and_raise(db_path: str) -> None:
    """
    Validate hierarchy and raise exception if invalid.
    
    Args:
        db_path: Path to SQLite database
        
    Raises:
        HierarchyValidationError: If validation fails
    """
    is_valid, errors = validate_hierarchy(db_path)
    
    if not is_valid:
        error_msg = "Hierarchy validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
        log.error(error_msg)
        raise HierarchyValidationError(error_msg)
    
    log.info("Hierarchy validation passed successfully")

