# Backend Support for Hierarchy Configuration

## Overview

The backend fully supports saving and loading the hierarchical configuration structure (Home → Arrays → Battery Bank Arrays → Attachments). The configuration is persisted to the database and automatically loaded on startup.

## Configuration Persistence

### Database Storage

The configuration is stored in the SQLite database using the `ConfigurationManager` class:

1. **Saving**: When you save configuration via the API (`/api/config`), the config is:
   - Stored in the database as key-value pairs
   - Complex structures (lists, dicts) are JSON-encoded
   - Flat keys are used (e.g., `arrays`, `battery_bank_arrays`, `battery_bank_array_attachments`)

2. **Loading**: On startup, the system:
   - First tries to load from the database
   - Falls back to `config.yaml` if database is empty
   - Parses JSON-encoded lists back to Python objects
   - Validates and creates Pydantic models (`HubConfig`, `ArrayConfig`, `BatteryBankArrayConfig`, etc.)

### Supported Fields

The following list fields are properly handled:
- `arrays` - Arrays of inverters
- `battery_bank_arrays` - Arrays of battery banks
- `battery_bank_array_attachments` - Attachments between battery bank arrays and inverter arrays
- `battery_banks` - Individual battery banks
- `battery_packs` - Battery packs (legacy)
- `attachments` - Battery pack attachments (legacy)
- `meters` - Energy meters

## Runtime Object Building

### On Startup

When the app initializes (`SolarApp.__init__`), it:
1. Loads configuration from database/file
2. Builds runtime objects:
   - `self.arrays` - Runtime `Array` objects
   - `self.battery_bank_arrays` - Runtime `BatteryBankArray` objects
   - `self.packs` - Runtime `BatteryPack` objects (legacy)

### After Config Updates

When configuration is updated via the API:
1. Config is saved to database
2. Config is reloaded (`solar_app.cfg = solar_app.config_manager.reload_config()`)
3. **Runtime objects are rebuilt** (`solar_app._build_runtime_objects(solar_app.cfg)`)
4. This ensures the app immediately uses the new configuration

## API Endpoints

### Save Configuration

**POST `/api/config`**

Saves configuration updates to the database and rebuilds runtime objects.

```json
{
  "home": {
    "id": "home",
    "name": "My Solar Home",
    "description": "Main residential solar system"
  },
  "arrays": [
    {
      "id": "array1",
      "name": "North Roof Array",
      "inverter_ids": ["powdrive1", "powdrive2"]
    }
  ],
  "battery_bank_arrays": [
    {
      "id": "battery_array1",
      "name": "Battery Array for North Roof",
      "battery_bank_ids": ["battery1", "battery2"]
    }
  ],
  "battery_bank_array_attachments": [
    {
      "battery_bank_array_id": "battery_array1",
      "inverter_array_id": "array1",
      "attached_since": "2025-01-01T00:00:00+05:00",
      "detached_at": null
    }
  ]
}
```

### Load Configuration

**GET `/api/config`**

Returns the current configuration (from database or file).

## Configuration Flow

```
Frontend (HierarchyWizard)
    ↓
POST /api/config
    ↓
ConfigurationManager.update_config_bulk()
    ↓
Database (SQLite) - JSON encoded lists
    ↓
ConfigurationManager.reload_config()
    ↓
HubConfig (Pydantic model)
    ↓
SolarApp._build_runtime_objects()
    ↓
Runtime objects (Array, BatteryBankArray, etc.)
    ↓
System uses new configuration
```

## Key Implementation Details

### 1. List Handling in Config Manager

The `_dict_to_flat_configs` method now properly handles lists:
- Lists are stored as-is (will be JSON encoded in `_save_to_database`)
- On load, JSON strings are parsed back to lists
- List fields are validated and defaulted to empty lists if missing

### 2. Runtime Object Rebuilding

The `_build_runtime_objects` method:
- Extracts arrays, battery_bank_arrays, and attachments from config
- Builds runtime objects with proper relationships
- Maps battery bank arrays to inverter arrays via attachments

### 3. Startup Sequence

1. `main.py` → `load_config()` → Loads from database/file
2. `main.py` → `migrate_config_to_arrays()` → Migrates legacy configs
3. `SolarApp.__init__()` → `_build_runtime_objects()` → Builds runtime objects
4. System is ready with full hierarchy

## Testing

To verify the backend support:

1. **Save via API**:
   ```bash
   curl -X POST http://localhost:8000/api/config \
     -H "Content-Type: application/json" \
     -d '{"home": {"id": "home", "name": "Test Home"}}'
   ```

2. **Check database**:
   ```bash
   sqlite3 solarhub.db "SELECT key, value FROM config WHERE key LIKE '%home%' OR key LIKE '%arrays%' OR key LIKE '%battery_bank%';"
   ```

3. **Restart app** and verify configuration loads correctly

## Notes

- Configuration is **persistent** - survives app restarts
- Database takes precedence over `config.yaml`
- Runtime objects are **automatically rebuilt** after config updates
- The system supports **backward compatibility** with legacy configs
- All list fields are properly JSON-encoded/decoded

