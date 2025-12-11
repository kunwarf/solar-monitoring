"""
Database loader for hierarchy objects.

This module loads the complete hierarchy structure from the database
and builds the object-oriented representation using the hierarchy classes.
"""
import sqlite3
import json
import logging
from typing import Dict, List, Optional
from solarhub.hierarchy.system import System
from solarhub.hierarchy.arrays import InverterArray, BatteryArray
from solarhub.hierarchy.devices import Inverter, BatteryPack, Meter
from solarhub.hierarchy.batteries import Battery, BatteryCell
from solarhub.hierarchy.adapters import AdapterBase, AdapterInstance

log = logging.getLogger(__name__)


class HierarchyLoader:
    """Loads hierarchy structure from database and builds object representation."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def load_hierarchy(self) -> Dict[str, System]:
        """
        Load complete hierarchy from database.
        
        Returns:
            Dictionary mapping system_id to System objects
        """
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row  # Enable column access by name
        cur = con.cursor()
        
        try:
            systems = {}
            
            # 1. Load all systems
            systems_data = self._load_systems(cur)
            
            # 2. Load adapter bases (for reference)
            adapter_bases = self._load_adapter_bases(cur)
            
            # 3. Load adapter instances
            adapters = self._load_adapters(cur)
            
            # 4. Load inverter arrays
            inverter_arrays_data = self._load_inverter_arrays(cur)
            
            # 5. Load battery arrays
            battery_arrays_data = self._load_battery_arrays(cur)
            
            # 6. Load battery array attachments
            battery_array_attachments = self._load_battery_array_attachments(cur)
            
            # 7. Load inverters
            inverters_data = self._load_inverters(cur)
            
            # 8. Load battery packs
            battery_packs_data = self._load_battery_packs(cur)
            
            # 9. Load battery pack adapters
            battery_pack_adapters = self._load_battery_pack_adapters(cur)
            
            # 10. Load batteries (if table exists)
            batteries_data = self._load_batteries(cur)
            
            # 11. Load battery cells (if table exists)
            battery_cells_data = self._load_battery_cells(cur)
            
            # 12. Load meters
            meters_data = self._load_meters(cur)
            
            # Build hierarchy objects
            for system_row in systems_data:
                system = self._build_system(system_row)
                systems[system.system_id] = system
                
                # Add inverter arrays
                for array_row in inverter_arrays_data:
                    if array_row['system_id'] == system.system_id:
                        inverter_array = self._build_inverter_array(array_row)
                        system.add_inverter_array(inverter_array)
                        
                        # Add inverters to array
                        for inv_row in inverters_data:
                            if inv_row['array_id'] == inverter_array.array_id:
                                inverter = self._build_inverter(inv_row)
                                
                                # Link adapter if available
                                if inv_row['adapter_id'] and inv_row['adapter_id'] in adapters:
                                    adapter = adapters[inv_row['adapter_id']]
                                    inverter.set_adapter(adapter)
                                
                                inverter_array.add_inverter(inverter)
                
                # Add battery arrays
                for battery_array_row in battery_arrays_data:
                    if battery_array_row['system_id'] == system.system_id:
                        battery_array = self._build_battery_array(battery_array_row)
                        system.add_battery_array(battery_array)
                        
                        # Link to inverter array if attached
                        attachment = battery_array_attachments.get(battery_array.battery_array_id)
                        if attachment:
                            inverter_array_id = attachment['inverter_array_id']
                            inverter_array = system.get_inverter_array(inverter_array_id)
                            if inverter_array:
                                battery_array.attach_inverter_array(inverter_array)
                        
                        # Add battery packs to array
                        for pack_row in battery_packs_data:
                            if pack_row['battery_array_id'] == battery_array.battery_array_id:
                                battery_pack = self._build_battery_pack(pack_row)
                                
                                # Link adapters if available
                                pack_adapters = battery_pack_adapters.get(battery_pack.pack_id, [])
                                for adapter_id in pack_adapters:
                                    if adapter_id in adapters:
                                        adapter = adapters[adapter_id]
                                        battery_pack.add_adapter(adapter)
                                
                                battery_array.add_battery_pack(battery_pack)
                                
                                # Add batteries to pack
                                for battery_row in batteries_data:
                                    if battery_row['pack_id'] == battery_pack.pack_id:
                                        battery = self._build_battery(battery_row)
                                        battery_pack.add_battery(battery)
                                        
                                        # Add cells to battery
                                        for cell_row in battery_cells_data:
                                            if cell_row['battery_id'] == battery.battery_id:
                                                cell = self._build_battery_cell(cell_row)
                                                battery.add_cell(cell)
                
                # Add system-level meters (array_id is NULL)
                for meter_row in meters_data:
                    if meter_row['system_id'] == system.system_id and meter_row['array_id'] is None:
                        meter = self._build_meter(meter_row)
                        
                        # Link adapter if available
                        if meter_row['adapter_id'] and meter_row['adapter_id'] in adapters:
                            adapter = adapters[meter_row['adapter_id']]
                            meter.set_adapter(adapter)
                        
                        system.add_meter(meter)
            
            log.info(f"Loaded {len(systems)} system(s) from database")
            return systems
            
        except Exception as e:
            log.error(f"Failed to load hierarchy from database: {e}", exc_info=True)
            raise
        finally:
            con.close()
    
    def _load_systems(self, cur) -> List[sqlite3.Row]:
        """Load all systems from database."""
        try:
            cur.execute("SELECT * FROM systems ORDER BY created_at")
            return cur.fetchall()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.warning("systems table does not exist yet")
                return []
            raise
    
    def _load_adapter_bases(self, cur) -> Dict[str, AdapterBase]:
        """Load adapter base definitions."""
        adapter_bases = {}
        try:
            cur.execute("SELECT * FROM adapter_base")
            for row in cur.fetchall():
                adapter_base = AdapterBase.from_db_row(dict(row))
                adapter_bases[adapter_base.adapter_type] = adapter_base
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.warning("adapter_base table does not exist yet")
            else:
                raise
        return adapter_bases
    
    def _load_adapters(self, cur) -> Dict[str, AdapterInstance]:
        """Load adapter instances."""
        adapters = {}
        try:
            cur.execute("SELECT * FROM adapters")
            for row in cur.fetchall():
                adapter = AdapterInstance.from_db_row(dict(row))
                adapters[adapter.adapter_id] = adapter
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.warning("adapters table does not exist yet")
            else:
                raise
        return adapters
    
    def _load_inverter_arrays(self, cur) -> List[sqlite3.Row]:
        """Load all inverter arrays."""
        try:
            # Check if created_at column exists
            cur.execute("PRAGMA table_info(arrays)")
            columns = [row[1] for row in cur.fetchall()]
            order_by = "ORDER BY created_at" if "created_at" in columns else ""
            cur.execute(f"SELECT * FROM arrays WHERE system_id IS NOT NULL {order_by}")
            return cur.fetchall()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.warning("arrays table does not exist yet")
                return []
            raise
    
    def _load_battery_arrays(self, cur) -> List[sqlite3.Row]:
        """Load all battery arrays."""
        try:
            # Check if created_at column exists
            cur.execute("PRAGMA table_info(battery_arrays)")
            columns = [row[1] for row in cur.fetchall()]
            order_by = "ORDER BY created_at" if "created_at" in columns else ""
            cur.execute(f"SELECT * FROM battery_arrays {order_by}")
            return cur.fetchall()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.warning("battery_arrays table does not exist yet")
                return []
            raise
    
    def _load_battery_array_attachments(self, cur) -> Dict[str, Dict]:
        """Load battery array to inverter array attachments."""
        attachments = {}
        try:
            cur.execute("SELECT * FROM battery_array_attachments WHERE detached_at IS NULL")
            for row in cur.fetchall():
                row_dict = dict(row)
                battery_array_id = row_dict['battery_array_id']
                attachments[battery_array_id] = row_dict
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.warning("battery_array_attachments table does not exist yet")
            else:
                raise
        return attachments
    
    def _load_inverters(self, cur) -> List[sqlite3.Row]:
        """Load all inverters."""
        try:
            # Check if created_at column exists
            cur.execute("PRAGMA table_info(inverters)")
            columns = [row[1] for row in cur.fetchall()]
            order_by = "ORDER BY created_at" if "created_at" in columns else ""
            cur.execute(f"SELECT * FROM inverters {order_by}")
            return cur.fetchall()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.warning("inverters table does not exist yet")
                return []
            raise
    
    def _load_battery_packs(self, cur) -> List[sqlite3.Row]:
        """Load all battery packs."""
        try:
            # Check if created_at column exists
            cur.execute("PRAGMA table_info(battery_packs)")
            columns = [row[1] for row in cur.fetchall()]
            order_by = "ORDER BY created_at" if "created_at" in columns else ""
            cur.execute(f"SELECT * FROM battery_packs WHERE battery_array_id IS NOT NULL {order_by}")
            return cur.fetchall()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.warning("battery_packs table does not exist yet")
                return []
            raise
    
    def _load_battery_pack_adapters(self, cur) -> Dict[str, List[str]]:
        """Load battery pack to adapter associations."""
        pack_adapters = {}
        try:
            cur.execute("SELECT * FROM battery_pack_adapters WHERE enabled = 1 ORDER BY priority")
            for row in cur.fetchall():
                row_dict = dict(row)
                pack_id = row_dict['pack_id']
                adapter_id = row_dict['adapter_id']
                if pack_id not in pack_adapters:
                    pack_adapters[pack_id] = []
                pack_adapters[pack_id].append(adapter_id)
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.warning("battery_pack_adapters table does not exist yet")
            else:
                raise
        return pack_adapters
    
    def _load_batteries(self, cur) -> List[sqlite3.Row]:
        """Load all batteries (individual battery units)."""
        try:
            cur.execute("SELECT * FROM batteries ORDER BY battery_index")
            return cur.fetchall()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.debug("batteries table does not exist yet (optional)")
                return []
            raise
    
    def _load_battery_cells(self, cur) -> List[sqlite3.Row]:
        """Load all battery cells."""
        try:
            cur.execute("SELECT * FROM battery_cells ORDER BY cell_index")
            return cur.fetchall()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.debug("battery_cells table does not exist yet (optional)")
                return []
            raise
    
    def _load_meters(self, cur) -> List[sqlite3.Row]:
        """Load all meters."""
        try:
            # Check if created_at column exists
            cur.execute("PRAGMA table_info(meters)")
            columns = [row[1] for row in cur.fetchall()]
            order_by = "ORDER BY created_at" if "created_at" in columns else ""
            cur.execute(f"SELECT * FROM meters {order_by}")
            return cur.fetchall()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.warning("meters table does not exist yet")
                return []
            raise
    
    def _build_system(self, row: sqlite3.Row) -> System:
        """Build System object from database row."""
        row_dict = dict(row)
        return System(
            system_id=row_dict['system_id'],
            name=row_dict['name'],
            description=row_dict.get('description'),
            timezone=row_dict.get('timezone', 'Asia/Karachi'),
            created_at=row_dict.get('created_at'),
            updated_at=row_dict.get('updated_at')
        )
    
    def _build_inverter_array(self, row: sqlite3.Row) -> InverterArray:
        """Build InverterArray object from database row."""
        row_dict = dict(row)
        return InverterArray(
            array_id=row_dict['array_id'],
            name=row_dict.get('name', row_dict['array_id']),
            system_id=row_dict['system_id'],
            created_at=row_dict.get('created_at'),
            updated_at=row_dict.get('updated_at')
        )
    
    def _build_battery_array(self, row: sqlite3.Row) -> BatteryArray:
        """Build BatteryArray object from database row."""
        row_dict = dict(row)
        return BatteryArray(
            battery_array_id=row_dict['battery_array_id'],
            name=row_dict.get('name', row_dict['battery_array_id']),
            system_id=row_dict['system_id'],
            created_at=row_dict.get('created_at'),
            updated_at=row_dict.get('updated_at')
        )
    
    def _build_inverter(self, row: sqlite3.Row) -> Inverter:
        """Build Inverter object from database row."""
        row_dict = dict(row)
        return Inverter(
            inverter_id=row_dict['inverter_id'],
            name=row_dict['name'],
            array_id=row_dict['array_id'],
            system_id=row_dict['system_id'],
            adapter_id=row_dict.get('adapter_id'),
            model=row_dict.get('model'),
            serial_number=row_dict.get('serial_number'),
            vendor=row_dict.get('vendor'),
            phase_type=row_dict.get('phase_type'),
            created_at=row_dict.get('created_at'),
            updated_at=row_dict.get('updated_at')
        )
    
    def _build_battery_pack(self, row: sqlite3.Row) -> BatteryPack:
        """Build BatteryPack object from database row."""
        row_dict = dict(row)
        return BatteryPack(
            pack_id=row_dict['pack_id'],
            name=row_dict.get('name', row_dict['pack_id']),
            battery_array_id=row_dict['battery_array_id'],
            system_id=row_dict['system_id'],
            chemistry=row_dict.get('chemistry'),
            nominal_kwh=row_dict.get('nominal_kwh'),
            max_charge_kw=row_dict.get('max_charge_kw'),
            max_discharge_kw=row_dict.get('max_discharge_kw'),
            created_at=row_dict.get('created_at'),
            updated_at=row_dict.get('updated_at')
        )
    
    def _build_battery(self, row: sqlite3.Row) -> Battery:
        """Build Battery object from database row."""
        row_dict = dict(row)
        return Battery(
            battery_id=row_dict['battery_id'],
            pack_id=row_dict['pack_id'],
            battery_array_id=row_dict['battery_array_id'],
            system_id=row_dict['system_id'],
            battery_index=row_dict.get('battery_index', 0),
            serial_number=row_dict.get('serial_number'),
            model=row_dict.get('model'),
            created_at=row_dict.get('created_at')
        )
    
    def _build_battery_cell(self, row: sqlite3.Row) -> BatteryCell:
        """Build BatteryCell object from database row."""
        row_dict = dict(row)
        return BatteryCell(
            cell_id=row_dict['cell_id'],
            battery_id=row_dict['battery_id'],
            pack_id=row_dict['pack_id'],
            battery_array_id=row_dict['battery_array_id'],
            system_id=row_dict['system_id'],
            cell_index=row_dict.get('cell_index', 0),
            nominal_voltage=row_dict.get('nominal_voltage'),
            created_at=row_dict.get('created_at')
        )
    
    def _build_meter(self, row: sqlite3.Row) -> Meter:
        """Build Meter object from database row."""
        row_dict = dict(row)
        return Meter(
            meter_id=row_dict['meter_id'],
            name=row_dict.get('name', row_dict['meter_id']),
            system_id=row_dict['system_id'],
            array_id=row_dict.get('array_id'),
            adapter_id=row_dict.get('adapter_id'),
            model=row_dict.get('model'),
            meter_type=row_dict.get('type'),
            attachment_target=row_dict.get('attachment_target'),
            created_at=row_dict.get('created_at'),
            updated_at=row_dict.get('updated_at')
        )

