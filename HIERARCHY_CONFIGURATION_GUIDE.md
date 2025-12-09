# Hierarchical System Configuration Guide

This guide explains how to configure the hierarchical structure: **Home → Arrays of Inverters → Arrays of Battery Banks → Battery Banks**.

## Structure Overview

```
Home
├── Array 1 (Inverters)
│   ├── Inverter 1
│   ├── Inverter 2
│   └── Battery Bank Array 1 (attached 1:1)
│       ├── Battery Bank 1
│       └── Battery Bank 2
├── Array 2 (Inverters)
│   ├── Inverter 3
│   └── Battery Bank Array 2 (attached 1:1)
│       └── Battery Bank 3
└── Meters (attached to Home or Arrays)
```

## Configuration in config.yaml

### Step 1: Define Home

```yaml
home:
  id: home
  name: "My Solar Home"
  description: "Main residential solar system"
```

### Step 2: Define Arrays of Inverters

```yaml
arrays:
  - id: array1
    name: "North Roof Array"
    inverter_ids:
      - powdrive1
      - powdrive2
  
  - id: array2
    name: "South Roof Array"
    inverter_ids:
      - powdrive3
      - powdrive4
```

### Step 3: Assign Inverters to Arrays

```yaml
inverters:
  - id: powdrive1
    name: "West Roof"
    array_id: array1  # Assign to array1
    adapter:
      type: powdrive
      # ... adapter config ...
  
  - id: powdrive2
    name: "East Roof"
    array_id: array1  # Assign to array1
    adapter:
      type: powdrive
      # ... adapter config ...
  
  - id: powdrive3
    name: "South Roof 1"
    array_id: array2  # Assign to array2
    adapter:
      type: powdrive
      # ... adapter config ...
  
  - id: powdrive4
    name: "South Roof 2"
    array_id: array2  # Assign to array2
    adapter:
      type: powdrive
      # ... adapter config ...
```

### Step 4: Define Battery Banks

```yaml
battery_banks:
  - id: battery1
    name: "Main Battery Bank"
    adapter:
      type: pytes
      serial_port: /dev/ttyUSB1
      # ... adapter config ...
  
  - id: battery2
    name: "Secondary Battery Bank"
    adapter:
      type: pytes
      serial_port: /dev/ttyUSB2
      # ... adapter config ...
  
  - id: battery3
    name: "Third Battery Bank"
    adapter:
      type: jkbms_passive
      serial_port: /dev/ttyUSB0
      # ... adapter config ...
```

### Step 5: Group Battery Banks into Arrays

```yaml
battery_bank_arrays:
  - id: battery_array1
    name: "Battery Array for North Roof"
    battery_bank_ids:
      - battery1
      - battery2
  
  - id: battery_array2
    name: "Battery Array for South Roof"
    battery_bank_ids:
      - battery3
```

### Step 6: Attach Battery Bank Arrays to Inverter Arrays (1:1)

```yaml
battery_bank_array_attachments:
  - battery_bank_array_id: battery_array1
    inverter_array_id: array1
    attached_since: "2025-01-01T00:00:00+05:00"
    detached_at: null  # null = active attachment
  
  - battery_bank_array_id: battery_array2
    inverter_array_id: array2
    attached_since: "2025-01-01T00:00:00+05:00"
    detached_at: null  # null = active attachment
```

### Step 7: Attach Meters (Optional)

Meters can be attached to an array or to the home:

```yaml
meters:
  - id: grid_meter_1
    name: "Main Grid Connection Meter"
    attachment_target: home  # Attach to home (measures total consumption)
    adapter:
      type: iammeter
      # ... adapter config ...
  
  - id: array1_meter
    name: "Array 1 Grid Meter"
    attachment_target: array1  # Attach to specific array
    adapter:
      type: iammeter
      # ... adapter config ...
```

## Complete Example

Here's a complete example with two systems:

```yaml
# Home Configuration
home:
  id: home
  name: "My Solar Home"
  description: "Residential solar system with two arrays"

# Arrays of Inverters
arrays:
  - id: array1
    name: "North Roof System"
    inverter_ids:
      - powdrive1
      - powdrive2
  
  - id: array2
    name: "South Roof System"
    inverter_ids:
      - powdrive3

# Inverters
inverters:
  - id: powdrive1
    name: "West Roof"
    array_id: array1
    adapter:
      type: powdrive
      transport: rtu
      unit_id: 1
      serial_port: /dev/ttyUSB2
      baudrate: 9600
    safety:
      max_batt_voltage_v: 52
      max_charge_a: 100
      max_discharge_a: 100
    solar:
      - pv_dc_kw: 14.5
        tilt_deg: 28
        azimuth_deg: 180
        perf_ratio: 0.82
        albedo: 0.2

  - id: powdrive2
    name: "East Roof"
    array_id: array1
    adapter:
      type: powdrive
      transport: rtu
      unit_id: 1
      serial_port: /dev/ttyUSB3
      baudrate: 9600
    safety:
      max_batt_voltage_v: 52
      max_charge_a: 100
      max_discharge_a: 100
    solar:
      - pv_dc_kw: 15.8
        tilt_deg: 28
        azimuth_deg: 180
        perf_ratio: 0.82
        albedo: 0.2

  - id: powdrive3
    name: "South Roof"
    array_id: array2
    adapter:
      type: powdrive
      transport: rtu
      unit_id: 1
      serial_port: /dev/ttyUSB4
      baudrate: 9600
    safety:
      max_batt_voltage_v: 52
      max_charge_a: 100
      max_discharge_a: 100
    solar:
      - pv_dc_kw: 12.0
        tilt_deg: 28
        azimuth_deg: 180
        perf_ratio: 0.82
        albedo: 0.2

# Battery Banks
battery_banks:
  - id: battery1
    name: "Main Battery Bank"
    adapter:
      type: pytes
      serial_port: /dev/ttyUSB1
      baudrate: 115200
      batteries: 4
      cells_per_battery: 15
      dev_name: pytes
      manufacturer: PYTES Energy Co.Ltd
      model: USP5000

  - id: battery2
    name: "Secondary Battery Bank"
    adapter:
      type: pytes
      serial_port: /dev/ttyUSB5
      baudrate: 115200
      batteries: 2
      cells_per_battery: 15
      dev_name: pytes
      manufacturer: PYTES Energy Co.Ltd
      model: USP5000

  - id: battery3
    name: "Third Battery Bank"
    adapter:
      type: jkbms_passive
      serial_port: /dev/ttyUSB0
      baudrate: 115200
      batteries: 3
      cells_per_battery: 16
      bms_broadcasting: true
      dev_name: jkbms
      manufacturer: JK BMS
      model: JK-PB2A16S20P

# Arrays of Battery Banks
battery_bank_arrays:
  - id: battery_array1
    name: "Battery Array for North Roof"
    battery_bank_ids:
      - battery1
      - battery2
  
  - id: battery_array2
    name: "Battery Array for South Roof"
    battery_bank_ids:
      - battery3

# Attach Battery Bank Arrays to Inverter Arrays (1:1 relationship)
battery_bank_array_attachments:
  - battery_bank_array_id: battery_array1
    inverter_array_id: array1
    attached_since: "2025-01-01T00:00:00+05:00"
    detached_at: null
  
  - battery_bank_array_id: battery_array2
    inverter_array_id: array2
    attached_since: "2025-01-01T00:00:00+05:00"
    detached_at: null

# Meters (attached to home or arrays)
meters:
  - id: grid_meter_1
    name: "Main Grid Connection Meter"
    attachment_target: home  # Attach to home
    adapter:
      type: iammeter
      transport: tcp
      host: 192.168.88.23
      port: 502
      unit_id: 1
      prefer_legacy_registers: true
```

## Key Rules

1. **Home**: Top-level container (optional, but recommended)
2. **Arrays of Inverters**: Group multiple inverters together
3. **Battery Banks**: Individual battery banks with adapters
4. **Arrays of Battery Banks**: Group multiple battery banks together
5. **Attachments**: 1:1 relationship between Battery Bank Arrays and Inverter Arrays
6. **Meters**: Can be attached to an array or to "home"

## Notes

- Each inverter must have an `array_id` that matches an array in the `arrays` list
- Each battery bank array can only be attached to one inverter array (1:1)
- A battery bank array can be attached to multiple inverter arrays, but only one at a time (use `detached_at` to switch)
- Meters attached to "home" measure total consumption across all arrays
- Meters attached to an array measure consumption for that specific array

