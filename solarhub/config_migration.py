"""
Configuration migration helper for backward compatibility.
Creates default arrays for legacy configs that don't have arrays defined.
"""
import logging
from typing import Dict, List, Optional
from solarhub.config import HubConfig, ArrayConfig, InverterConfig, BatteryPackConfig, BatteryPackAttachment, BatteryBankArrayConfig, BatteryBankArrayAttachment
from solarhub.array_models import Array, BatteryPack, BatteryBankArray

log = logging.getLogger(__name__)


def migrate_config_to_arrays(cfg: HubConfig) -> HubConfig:
    """
    Migrate legacy configuration to array-based structure.
    
    If config has no arrays defined:
    1. Create a default array
    2. Assign all inverters to the default array
    3. Migrate battery_bank to battery_packs if present
    
    Args:
        cfg: HubConfig (may be legacy format)
        
    Returns:
        HubConfig with arrays populated
    """
    # If arrays already defined, return as-is
    if cfg.arrays:
        log.info("Configuration already has arrays defined, skipping migration")
        return cfg
    
    log.info("Migrating legacy configuration to array-based structure")
    
    # Create default array
    default_array_id = "default_array"
    default_array = ArrayConfig(
        id=default_array_id,
        name="Default Array",
        inverter_ids=[inv.id for inv in cfg.inverters],
        scheduler=None  # Use global scheduler config
    )
    
    # Update inverters to include array_id if missing
    updated_inverters = []
    for inv in cfg.inverters:
        # Check if array_id is missing or None
        array_id = getattr(inv, 'array_id', None)
        if not array_id:
            # Create new inverter config with array_id
            inv_dict = inv.model_dump()
            inv_dict['array_id'] = default_array_id
            updated_inverters.append(InverterConfig(**inv_dict))
        else:
            updated_inverters.append(inv)
    
    # Migrate battery_bank to battery_packs if present
    battery_packs = list(cfg.battery_packs) if cfg.battery_packs else []
    attachments = list(cfg.attachments) if cfg.attachments else []
    
    if cfg.battery_bank:
        log.info(f"Migrating battery_bank '{cfg.battery_bank.id}' to battery_packs")
        # Create a pack from battery_bank
        pack_id = f"{cfg.battery_bank.id}_pack"
        pack = BatteryPackConfig(
            id=pack_id,
            name=cfg.battery_bank.name or f"Battery Pack from {cfg.battery_bank.id}",
            chemistry="LFP",  # Default, should be configurable
            nominal_kwh=20.0,  # Default, should be configurable
            max_charge_kw=5.0,  # Default, should be configurable
            max_discharge_kw=5.0,  # Default, should be configurable
            units=[]  # Will be populated from adapter if available
        )
        battery_packs.append(pack)
        
        # Create attachment to default array
        from solarhub.timezone_utils import now_configured
        attachment = BatteryPackAttachment(
            pack_id=pack_id,
            array_id=default_array_id,
            attached_since=now_configured().isoformat(),
            detached_at=None
        )
        attachments.append(attachment)
    
    # Create updated config
    cfg_dict = cfg.model_dump()
    cfg_dict['arrays'] = [default_array]
    cfg_dict['inverters'] = updated_inverters
    cfg_dict['battery_packs'] = battery_packs if battery_packs else None
    cfg_dict['attachments'] = attachments if attachments else None
    
    migrated_cfg = HubConfig(**cfg_dict)
    log.info(f"Migration complete: Created default array '{default_array_id}' with {len(updated_inverters)} inverters")
    
    return migrated_cfg


def build_inverter_to_array_map(cfg: HubConfig) -> Dict[str, str]:
    """
    Build a mapping from inverter_id to array_id.
    
    Args:
        cfg: HubConfig
        
    Returns:
        Dict mapping inverter_id -> array_id
    """
    mapping = {}
    
    # If arrays are defined, use them
    if cfg.arrays:
        for array in cfg.arrays:
            for inv_id in array.inverter_ids:
                mapping[inv_id] = array.id
    
    # Also check inverters directly (for backward compatibility)
    for inv in cfg.inverters:
        if hasattr(inv, 'array_id') and inv.array_id:
            mapping[inv.id] = inv.array_id
    
    return mapping


def build_array_runtime_objects(cfg: HubConfig) -> Dict[str, Array]:
    """
    Build runtime Array objects from configuration.
    
    Args:
        cfg: HubConfig
        
    Returns:
        Dict mapping array_id -> Array
    """
    arrays = {}
    
    if not cfg.arrays:
        log.warning("No arrays defined in config")
        return arrays
    
    # Build pack-to-array mapping from attachments
    pack_to_array = {}
    if cfg.attachments:
        for att in cfg.attachments:
            if att.detached_at is None:  # Active attachment
                pack_to_array[att.pack_id] = att.array_id
    
    for array_cfg in cfg.arrays:
        # Find attached packs
        attached_pack_ids = [
            pack_id for pack_id, arr_id in pack_to_array.items()
            if arr_id == array_cfg.id
        ]
        
        array = Array(
            id=array_cfg.id,
            name=array_cfg.name,
            inverter_ids=array_cfg.inverter_ids,
            attached_pack_ids=attached_pack_ids,
            scheduler_config=array_cfg.scheduler
        )
        arrays[array_cfg.id] = array
    
    return arrays


def build_pack_runtime_objects(cfg: HubConfig) -> Dict[str, BatteryPack]:
    """
    Build runtime BatteryPack objects from configuration.
    
    Args:
        cfg: HubConfig
        
    Returns:
        Dict mapping pack_id -> BatteryPack
    """
    packs = {}
    
    if not cfg.battery_packs:
        return packs
    
    # Build pack-to-array mapping from attachments
    pack_to_array = {}
    if cfg.attachments:
        for att in cfg.attachments:
            if att.detached_at is None:  # Active attachment
                pack_to_array[att.pack_id] = att.array_id
    
    for pack_cfg in cfg.battery_packs:
        pack = BatteryPack(
            id=pack_cfg.id,
            name=pack_cfg.name,
            chemistry=pack_cfg.chemistry,
            nominal_kwh=pack_cfg.nominal_kwh,
            max_charge_kw=pack_cfg.max_charge_kw,
            max_discharge_kw=pack_cfg.max_discharge_kw,
            unit_ids=[unit.id for unit in pack_cfg.units],
            attached_array_id=pack_to_array.get(pack_cfg.id)
        )
        packs[pack_cfg.id] = pack
    
    return packs


def build_battery_bank_array_runtime_objects(cfg: HubConfig) -> Dict[str, BatteryBankArray]:
    """
    Build runtime BatteryBankArray objects from configuration.
    
    Args:
        cfg: HubConfig
        
    Returns:
        Dict mapping battery_bank_array_id -> BatteryBankArray
    """
    battery_bank_arrays = {}
    
    if not cfg.battery_bank_arrays:
        return battery_bank_arrays
    
    # Build battery bank array to inverter array mapping from attachments (1:1)
    battery_bank_array_to_inverter_array = {}
    if cfg.battery_bank_array_attachments:
        for att in cfg.battery_bank_array_attachments:
            if att.detached_at is None:  # Active attachment
                battery_bank_array_to_inverter_array[att.battery_bank_array_id] = att.inverter_array_id
    
    for bank_array_cfg in cfg.battery_bank_arrays:
        bank_array = BatteryBankArray(
            id=bank_array_cfg.id,
            name=bank_array_cfg.name,
            battery_bank_ids=bank_array_cfg.battery_bank_ids,
            attached_inverter_array_id=battery_bank_array_to_inverter_array.get(bank_array_cfg.id)
        )
        battery_bank_arrays[bank_array_cfg.id] = bank_array
    
    return battery_bank_arrays

