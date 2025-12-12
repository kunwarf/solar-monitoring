"""
Adapter classes for adapter base definitions and instances.
"""
from typing import Optional, Dict, Any
from datetime import datetime
import json


class AdapterBase:
    """Represents an adapter base definition (from adapter_base table)."""
    
    def __init__(
        self,
        adapter_type: str,
        device_category: str,
        name: str,
        description: Optional[str] = None,
        config_schema: Optional[Dict[str, Any]] = None,
        supported_transports: Optional[list] = None,
        default_config: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        self.adapter_type = adapter_type
        self.device_category = device_category  # 'inverter', 'battery', 'meter'
        self.name = name
        self.description = description
        self.config_schema = config_schema or {}
        self.supported_transports = supported_transports or []
        self.default_config = default_config or {}
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'AdapterBase':
        """Create AdapterBase from database row."""
        # Handle None values from database (NULL columns)
        config_schema_str = row.get('config_schema') or '{}'
        supported_transports_str = row.get('supported_transports') or '[]'
        default_config_str = row.get('default_config') or '{}'
        
        config_schema = json.loads(config_schema_str)
        supported_transports = json.loads(supported_transports_str)
        default_config = json.loads(default_config_str)
        
        return cls(
            adapter_type=row['adapter_type'],
            device_category=row['device_category'],
            name=row['name'],
            description=row.get('description'),
            config_schema=config_schema,
            supported_transports=supported_transports,
            default_config=default_config,
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert adapter base to dictionary representation."""
        return {
            'adapter_type': self.adapter_type,
            'device_category': self.device_category,
            'name': self.name,
            'description': self.description,
            'config_schema': self.config_schema,
            'supported_transports': self.supported_transports,
            'default_config': self.default_config,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    
    def __repr__(self) -> str:
        return f"AdapterBase(type={self.adapter_type}, category={self.device_category}, name={self.name})"


class AdapterInstance:
    """Represents an adapter instance (from adapters table)."""
    
    def __init__(
        self,
        adapter_id: str,
        adapter_type: str,
        device_category: str,
        config_json: Dict[str, Any],
        device_id: Optional[str] = None,
        device_type: Optional[str] = None,
        name: Optional[str] = None,
        priority: int = 1,
        enabled: bool = True,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        self.adapter_id = adapter_id
        self.adapter_type = adapter_type
        self.device_category = device_category
        self.config_json = config_json  # Complete adapter configuration
        self.device_id = device_id
        self.device_type = device_type  # 'inverter', 'battery_pack', 'meter'
        self.name = name
        self.priority = priority  # For failover adapters (lower = higher priority)
        self.enabled = enabled
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'AdapterInstance':
        """Create AdapterInstance from database row."""
        # Handle None values from database (NULL columns)
        config_json_str = row.get('config_json') or '{}'
        config_json = json.loads(config_json_str)
        
        return cls(
            adapter_id=row['adapter_id'],
            adapter_type=row['adapter_type'],
            device_category=row['device_category'],
            config_json=config_json,
            device_id=row.get('device_id'),
            device_type=row.get('device_type'),
            name=row.get('name'),
            priority=row.get('priority', 1),
            enabled=bool(row.get('enabled', True)),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from config_json."""
        return self.config_json.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert adapter instance to dictionary representation."""
        return {
            'adapter_id': self.adapter_id,
            'adapter_type': self.adapter_type,
            'device_category': self.device_category,
            'device_id': self.device_id,
            'device_type': self.device_type,
            'name': self.name,
            'priority': self.priority,
            'enabled': self.enabled,
            'config': self.config_json,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    
    def __repr__(self) -> str:
        return f"AdapterInstance(id={self.adapter_id}, type={self.adapter_type}, device_id={self.device_id}, priority={self.priority}, enabled={self.enabled})"

