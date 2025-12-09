# Home Assistant Integration - Battery Optimized Smart Scheduler

## Overview

The battery-optimized smart scheduler now provides comprehensive Home Assistant integration with discovery messages for sensors, controls, and configuration options.

## MQTT Topics

### Data Topics
- `solar/fleet/battery_optimization` - Self-sufficiency metrics and battery optimization data
- `solar/fleet/enhanced_forecast` - Weather and PV forecasts
- `solar/fleet/plan` - Enhanced charging/discharging plans
- `solar/fleet/config` - Configuration data and controls

### Command Topics
- `solar/fleet/config/set` - Configuration commands from Home Assistant

## Home Assistant Sensors

### 🔋 Battery Optimization Sensors

| Sensor ID | Name | Unit | Icon | Description |
|-----------|------|------|------|-------------|
| `solar_fleet_self_sufficiency_current` | Solar Fleet Self-Sufficiency Current | % | mdi:solar-power | Current self-sufficiency percentage |
| `solar_fleet_self_sufficiency_avg` | Solar Fleet Self-Sufficiency Average | % | mdi:solar-power | 7-day average self-sufficiency |
| `solar_fleet_dynamic_soc_target` | Solar Fleet Dynamic SOC Target | % | mdi:battery-charging-high | Current dynamic SOC target |
| `solar_fleet_discharge_aggressiveness` | Solar Fleet Discharge Aggressiveness | - | mdi:gauge | Discharge aggressiveness factor |
| `solar_fleet_emergency_reserve_hours` | Solar Fleet Emergency Reserve Hours | h | mdi:shield-battery | Emergency reserve hours |
| `solar_fleet_peak_discharge_windows` | Solar Fleet Peak Discharge Windows | - | mdi:timeline-clock | Number of peak discharge windows |
| `solar_fleet_daily_grid_usage` | Solar Fleet Daily Grid Usage | kWh | mdi:transmission-tower | Daily grid energy usage |
| `solar_fleet_daily_pv_usage` | Solar Fleet Daily PV Usage | kWh | mdi:solar-panel | Daily PV energy usage |

### 🌤️ Enhanced Forecast Sensors

| Sensor ID | Name | Unit | Icon | Description |
|-----------|------|------|------|-------------|
| `solar_fleet_self_sufficiency_forecast` | Solar Fleet Self-Sufficiency Forecast | % | mdi:solar-power | Forecasted self-sufficiency |
| `solar_fleet_dynamic_soc_target_forecast` | Solar Fleet Dynamic SOC Target Forecast | % | mdi:battery-charging-high | Forecasted SOC target |
| `solar_fleet_daily_grid_usage_forecast` | Solar Fleet Daily Grid Usage Forecast | kWh | mdi:transmission-tower | Forecasted grid usage |
| `solar_fleet_daily_pv_usage_forecast` | Solar Fleet Daily PV Usage Forecast | kWh | mdi:solar-panel | Forecasted PV usage |
| `solar_fleet_emergency_reserve_hours_forecast` | Solar Fleet Emergency Reserve Hours Forecast | h | mdi:shield-battery | Forecasted emergency reserve |
| `solar_fleet_load_shift_opportunities` | Solar Fleet Load Shift Opportunities | - | mdi:swap-horizontal | Available load shift opportunities |
| `solar_fleet_peak_shaving_plan` | Solar Fleet Peak Shaving Plan | - | mdi:chart-line | Peak shaving plan status |

### 📊 Plan Sensors

| Sensor ID | Name | Unit | Icon | Description |
|-----------|------|------|------|-------------|
| `solar_fleet_sunset_hour` | Solar Fleet Sunset Hour | - | mdi:weather-sunset | Sunset hour (24h format) |
| `solar_fleet_soc_now` | Solar Fleet SOC Now | % | mdi:battery | Current battery SOC |
| `solar_fleet_end_soc_target` | Solar Fleet End SOC Target | % | mdi:battery-charging-high | Target SOC for end of day |
| `solar_fleet_required_grid_energy` | Solar Fleet Required Grid Energy | kWh | mdi:transmission-tower | Required grid energy to reach target |
| `solar_fleet_use_grid` | Solar Fleet Use Grid | - | mdi:power-plug | Whether grid charging is enabled |
| `solar_fleet_grid_power_cap` | Solar Fleet Grid Power Cap | W | mdi:lightning-bolt | Maximum grid charging power |

## Home Assistant Controls

### ⚙️ Configuration Controls

| Control ID | Name | Type | Unit | Range | Description |
|------------|------|------|------|-------|-------------|
| `solar_fleet_control_dynamic_soc` | Solar Fleet Control Dynamic SOC | Switch | - | ON/OFF | Enable/disable dynamic SOC targeting |
| `solar_fleet_control_target_self_sufficiency` | Solar Fleet Control Target Self-Sufficiency | Number | % | 50-100 | Target self-sufficiency percentage |
| `solar_fleet_control_min_self_sufficiency` | Solar Fleet Control Min Self-Sufficiency | Number | % | 50-95 | Minimum self-sufficiency percentage |
| `solar_fleet_control_max_grid_usage` | Solar Fleet Control Max Grid Usage | Number | kWh | 0-50 | Maximum daily grid usage |
| `solar_fleet_control_emergency_reserve` | Solar Fleet Control Emergency Reserve | Number | h | 1-24 | Emergency reserve hours |

## Home Assistant Configuration

### MQTT Integration Setup

1. **Add MQTT Integration** in Home Assistant
2. **Configure Broker** with your MQTT broker details
3. **Enable Discovery** - The system automatically publishes discovery messages

### Example Home Assistant Configuration

```yaml
# configuration.yaml
mqtt:
  discovery: true
  discovery_prefix: homeassistant

# Example automation for self-sufficiency monitoring
automation:
  - alias: "Low Self-Sufficiency Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.solar_fleet_self_sufficiency_current
      below: 80
    action:
      service: notify.mobile_app_your_phone
      data:
        message: "Solar self-sufficiency is below 80%: {{ states('sensor.solar_fleet_self_sufficiency_current') }}%"

# Example dashboard card
type: entities
title: Solar Fleet Battery Optimization
entities:
  - sensor.solar_fleet_self_sufficiency_current
  - sensor.solar_fleet_dynamic_soc_target
  - sensor.solar_fleet_daily_grid_usage
  - sensor.solar_fleet_daily_pv_usage
  - switch.solar_fleet_control_dynamic_soc
  - number.solar_fleet_control_target_self_sufficiency
```

## Dashboard Examples

### Self-Sufficiency Overview Card
```yaml
type: gauge
entity: sensor.solar_fleet_self_sufficiency_current
name: Self-Sufficiency
min: 0
max: 100
severity:
  green: 90
  yellow: 80
  red: 70
```

### Battery Status Card
```yaml
type: entities
title: Battery Status
entities:
  - sensor.solar_fleet_soc_now
  - sensor.solar_fleet_dynamic_soc_target
  - sensor.solar_fleet_emergency_reserve_hours
  - sensor.solar_fleet_peak_discharge_windows
```

### Energy Usage Card
```yaml
type: statistics-graph
entities:
  - sensor.solar_fleet_daily_pv_usage
  - sensor.solar_fleet_daily_grid_usage
period: day
```

### Configuration Controls Card
```yaml
type: entities
title: Battery Optimization Controls
entities:
  - switch.solar_fleet_control_dynamic_soc
  - number.solar_fleet_control_target_self_sufficiency
  - number.solar_fleet_control_min_self_sufficiency
  - number.solar_fleet_control_max_grid_usage
  - number.solar_fleet_control_emergency_reserve
```

## Automation Examples

### Dynamic SOC Control
```yaml
automation:
  - alias: "Enable Dynamic SOC for High Self-Sufficiency"
    trigger:
      platform: numeric_state
      entity_id: sensor.solar_fleet_self_sufficiency_avg
      above: 90
    action:
      service: switch.turn_on
      entity_id: switch.solar_fleet_control_dynamic_soc
```

### Grid Usage Monitoring
```yaml
automation:
  - alias: "High Grid Usage Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.solar_fleet_daily_grid_usage
      above: 5
    action:
      service: notify.mobile_app_your_phone
      data:
        message: "High grid usage detected: {{ states('sensor.solar_fleet_daily_grid_usage') }} kWh"
```

### Emergency Reserve Monitoring
```yaml
automation:
  - alias: "Low Emergency Reserve Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.solar_fleet_emergency_reserve_hours
      below: 4
    action:
      service: notify.mobile_app_your_phone
      data:
        message: "Emergency reserve is low: {{ states('sensor.solar_fleet_emergency_reserve_hours') }} hours"
```

## Data Flow

1. **Battery Optimized Scheduler** calculates metrics and publishes to MQTT topics
2. **Home Assistant** receives data via MQTT integration
3. **Discovery Messages** automatically create sensors and controls
4. **User** can view data in dashboards and create automations
5. **Configuration Changes** are sent back to the scheduler via MQTT commands

## Troubleshooting

### Sensors Not Appearing
- Check MQTT broker connection
- Verify discovery is enabled in Home Assistant
- Check MQTT logs for discovery messages

### Controls Not Working
- Verify MQTT command topic subscription
- Check Home Assistant logs for command errors
- Ensure configuration values are within valid ranges

### Data Not Updating
- Check if smart scheduler is running
- Verify MQTT topic publishing
- Check Home Assistant MQTT integration status

## Advanced Configuration

### Custom Dashboards
Create custom dashboards using the Lovelace UI with the new sensors and controls.

### Integration with Other Systems
Use the MQTT data to integrate with other home automation systems or external monitoring tools.

### Historical Data
Use Home Assistant's history and statistics features to track long-term trends in self-sufficiency and battery optimization.

## Support

For issues or questions about the Home Assistant integration:
1. Check the MQTT logs in Home Assistant
2. Verify the smart scheduler is running and publishing data
3. Check the configuration values are within valid ranges
4. Review the Home Assistant MQTT integration documentation

