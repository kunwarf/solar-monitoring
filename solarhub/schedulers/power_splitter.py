"""
Power splitter for distributing array-level power targets across multiple inverters.

Supports three modes:
- headroom: Proportional to available headroom each tick
- equal: Equal shares by count
- rated: Proportional to nameplate/rated charge/discharge capability
"""
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

log = logging.getLogger(__name__)

@dataclass
class InverterCapabilities:
    """Capabilities and current state of an inverter for power splitting."""
    inverter_id: str
    online: bool
    faulted: bool = False
    
    # Rated capabilities (nameplate)
    rated_charge_kw: float = 0.0
    rated_discharge_kw: float = 0.0
    
    # Current headroom (after temps/derates/faults)
    max_charge_kw_now: float = 0.0
    max_discharge_kw_now: float = 0.0
    
    # Current power (positive = charging, negative = discharging)
    current_charge_w: float = 0.0
    current_discharge_w: float = 0.0
    
    # Power step size (adapter-specific granularity)
    power_step_w: Optional[int] = None
    
    # Whether adapter supports absolute power setpoint
    supports_abs_power_setpoint: bool = True

def calculate_headroom(inv: InverterCapabilities, action: str) -> float:
    """
    Calculate available headroom for charge or discharge.
    
    Args:
        inv: Inverter capabilities
        action: 'charge' or 'discharge'
    
    Returns:
        Headroom in watts
    """
    if action == 'charge':
        max_w = inv.max_charge_kw_now * 1000
        current_w = inv.current_charge_w
        return max(0, max_w - current_w)
    else:  # discharge
        max_w = inv.max_discharge_kw_now * 1000
        current_w = abs(inv.current_discharge_w)  # discharge is negative, take abs
        return max(0, max_w - current_w)

def split_power(
    P_target_w: float,
    inverters: List[InverterCapabilities],
    mode: str = "headroom",
    step_w: int = 50,
    min_w: int = 50,
    action: str = "charge",
    fairness: Optional[str] = None
) -> Tuple[Dict[str, float], float, float]:
    """
    Split array power target across inverters.
    
    Args:
        P_target_w: Target power for the array (positive for charge, negative for discharge)
        inverters: List of inverter capabilities
        mode: Split mode ('headroom', 'equal', 'rated')
        step_w: Default rounding step (overridden by inverter.power_step_w if set)
        min_w: Minimum power per inverter (below this -> 0)
        action: 'charge' or 'discharge'
        fairness: Fairness mode (None, 'round_robin', 'aging')
    
    Returns:
        Tuple of (allocations dict {inverter_id: power_w}, total_allocated_w, unmet_w)
    """
    # Filter candidates: online, not faulted, with headroom
    candidates = []
    for inv in inverters:
        if not inv.online or inv.faulted:
            continue
        
        headroom = calculate_headroom(inv, action)
        if headroom <= 0:
            continue
        
        # Get rating for this action
        if action == 'charge':
            rating_w = inv.rated_charge_kw * 1000
        else:
            rating_w = inv.rated_discharge_kw * 1000
        
        # Use inverter-specific step or default
        step = inv.power_step_w if inv.power_step_w is not None else step_w
        
        candidates.append((inv, headroom, rating_w, step))
    
    if not candidates or P_target_w == 0:
        return {}, 0.0, abs(P_target_w)
    
    # Calculate weights based on mode
    if mode == "equal":
        weights = [1.0] * len(candidates)
    elif mode == "rated":
        weights = [max(1.0, r) for (_, _, r, _) in candidates]
    else:  # headroom (default)
        weights = [max(1.0, h) for (_, h, _, _) in candidates]
    
    total_weight = sum(weights)
    if total_weight == 0:
        return {}, 0.0, abs(P_target_w)
    
    # Initial split
    allocations: Dict[str, float] = {}
    remaining = abs(P_target_w)
    
    for weight, (inv, headroom, _, _) in zip(weights, candidates):
        raw_share = abs(P_target_w) * (weight / total_weight)
        allocated = min(raw_share, headroom)
        allocations[inv.inverter_id] = allocated
        remaining -= allocated
    
    # Redistribute leftover
    while remaining > 0.1:  # Small threshold to avoid infinite loops
        progressed = False
        for inv, headroom, _, _ in candidates:
            if remaining <= 0.1:
                break
            
            current = allocations.get(inv.inverter_id, 0.0)
            spare = headroom - current
            if spare <= 0:
                continue
            
            give = min(spare, remaining)
            allocations[inv.inverter_id] = current + give
            remaining -= give
            progressed = True
        
        if not progressed:
            break
    
    # Step rounding + min thresholds
    final_allocations: Dict[str, float] = {}
    total_allocated = 0.0
    
    for inv, headroom, _, step in candidates:
        raw_power = allocations.get(inv.inverter_id, 0.0)
        
        # Round to step
        rounded = round(raw_power / step) * step
        
        # Apply minimum threshold
        if rounded < min_w:
            rounded = 0.0
        else:
            # Cap to headroom
            rounded = min(rounded, headroom)
        
        final_allocations[inv.inverter_id] = rounded
        total_allocated += rounded
    
    # Calculate unmet power
    unmet_w = max(0, abs(P_target_w) - total_allocated)
    
    # Apply sign based on action
    if P_target_w < 0:  # discharge
        final_allocations = {k: -v for k, v in final_allocations.items()}
    
    return final_allocations, total_allocated, unmet_w

