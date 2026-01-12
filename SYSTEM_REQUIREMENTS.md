# Solar Monitoring System - Comprehensive Requirements Document

## Document Information

- **Version**: 1.0
- **Date**: January 2025
- **Status**: Active
- **Last Updated**: January 2025

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Backend Requirements](#backend-requirements)
4. [Frontend Requirements](#frontend-requirements)
5. [Integration Requirements](#integration-requirements)
6. [Non-Functional Requirements](#non-functional-requirements)
7. [Security Requirements](#security-requirements)
8. [Deployment Requirements](#deployment-requirements)

---

## Executive Summary

The Solar Monitoring System is a comprehensive platform for real-time monitoring, control, and optimization of solar energy systems. It supports multiple inverters, battery banks, and energy meters, providing intelligent scheduling, forecasting, billing calculations, and Home Assistant integration.

### Key Capabilities

- **Real-time Telemetry**: Monitor solar production, battery status, grid interaction, and consumption
- **Device Management**: Support for multiple inverter types, battery banks, and meters
- **Smart Scheduling**: Tariff-aware battery optimization
- **Forecasting**: Solar, load, and grid power predictions
- **Billing Management**: Automated billing calculations with TOU (Time-of-Use) support
- **Home Assistant Integration**: Full MQTT discovery and control
- **Multi-Device Hierarchy**: Support for systems, arrays, and device groupings

---

## System Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Solar Monitoring System                    │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐        ┌─────▼─────┐      ┌────▼────┐
   │ Device  │        │   Smart  │      │   API   │
   │Adapter  │───────▶│Scheduler │──────▶│ Server  │
   └────┬────┘        └─────┬─────┘      └────┬────┘
        │                  │                   │
        │             ┌────▼─────┐             │
        │             │Forecast  │             │
        │             │ Engine   │             │
        │             └────┬─────┘             │
   ┌────▼────┐        ┌────▼─────┐        ┌────▼────┐
   │ Logger  │        │   MQTT   │        │Frontend │
   │(SQLite) │        │Publisher │        │ (React) │
   └─────────┘        └────┬─────┘        └─────────┘
                           │
                    ┌──────▼──────┐
                    │Home Assistant│
                    └─────────────┘
```

### Technology Stack

**Backend:**
- Python 3.8+
- FastAPI (REST API)
- SQLite (Data Storage)
- PyModbus (Modbus Communication)
- Paho MQTT (MQTT Publishing)
- AsyncIO (Asynchronous Operations)

**Frontend:**
- React 18+
- TypeScript
- Vite (Build Tool)
- Tailwind CSS (Styling)
- Framer Motion (Animations)
- Recharts (Data Visualization)
- React Query (Data Fetching)
- React Router (Routing)

---

## Backend Requirements

### 1. Device Communication & Adapters

#### 1.1 Inverter Adapters

**Requirement ID**: BE-001

**Description**: Support multiple inverter types through adapter pattern

**Requirements**:
- Support Powdrive inverters (Modbus RTU/TCP)
- Support Senergy inverters (Modbus RTU/TCP)
- Extensible architecture for adding new inverter types
- Automatic device type detection
- Connection management with auto-reconnection
- Register map-based communication (JSON configuration)
- Support for both single-phase and three-phase inverters
- Standardized field name mapping

**Technical Details**:
- Base adapter class: `InverterAdapter`
- Register map files: `register_maps/*.json`
- Telemetry mapper for field name standardization
- Command queue for write operations
- Phase detection from register data

**Acceptance Criteria**:
- [ ] Can connect to Powdrive inverters via Modbus RTU/TCP
- [ ] Can connect to Senergy inverters via Modbus RTU/TCP
- [ ] Automatically detects phase type (single/three)
- [ ] Handles connection failures gracefully
- [ ] Maps device-specific fields to standardized names
- [ ] Supports read and write operations

#### 1.2 Battery Adapters

**Requirement ID**: BE-002

**Description**: Support battery bank communication

**Requirements**:
- Support Pytes battery banks
- Support JKBMS battery banks (BLE and TCP/IP)
- Battery pack-level telemetry
- SOC (State of Charge) monitoring
- Charge/discharge power monitoring
- Temperature monitoring
- Voltage and current monitoring

**Technical Details**:
- Adapter classes: `PytesBatteryAdapter`, `JKBMSBatteryAdapter`
- Battery pack aggregation
- Cell-level monitoring (where supported)

**Acceptance Criteria**:
- [ ] Can connect to Pytes battery banks
- [ ] Can connect to JKBMS battery banks (BLE/TCP)
- [ ] Reads battery SOC, voltage, current, temperature
- [ ] Supports multiple battery packs per array
- [ ] Aggregates pack-level data to array level

#### 1.3 Meter Adapters

**Requirement ID**: BE-003

**Description**: Support energy meter communication

**Requirements**:
- Support IAMMeter devices
- Grid import/export monitoring
- Power factor monitoring
- Frequency monitoring
- Energy accumulation (import/export kWh)

**Technical Details**:
- Adapter class: `IAMMeterAdapter`
- Meter energy calculator for daily totals

**Acceptance Criteria**:
- [ ] Can connect to IAMMeter devices
- [ ] Reads real-time power (import/export)
- [ ] Reads cumulative energy (kWh)
- [ ] Monitors power factor and frequency

### 2. Data Management & Storage

#### 2.1 Database Schema

**Requirement ID**: BE-004

**Description**: SQLite database for historical data storage

**Requirements**:
- Store telemetry samples (inverter, battery, meter)
- Store hourly energy aggregations
- Store daily energy summaries
- Store billing data
- Support hierarchy (systems, arrays, devices)
- Index optimization for query performance
- Data retention policies

**Database Tables**:
- `energy_samples` - Inverter telemetry samples
- `battery_bank_samples` - Battery telemetry samples
- `meter_samples` - Meter telemetry samples
- `energy_hourly` - Hourly energy aggregations
- `energy_daily` - Daily energy summaries
- `battery_bank_hourly` - Battery hourly aggregations
- `billing_running` - Running billing calculations
- `billing_monthly` - Monthly billing summaries
- `systems` - System definitions
- `arrays` - Inverter array definitions
- `battery_arrays` - Battery array definitions
- `battery_packs` - Battery pack definitions
- `battery_pack_attachments` - Battery-to-array attachments
- `inverters` - Inverter device definitions
- `meters` - Meter device definitions
- `adapters` - Adapter instance definitions
- `adapter_base` - Adapter type definitions

**Acceptance Criteria**:
- [ ] All tables created with proper schema
- [ ] Indexes created for performance
- [ ] Foreign key relationships maintained
- [ ] Migration scripts for schema updates
- [ ] Data retention policies implemented

#### 2.2 Data Logging

**Requirement ID**: BE-005

**Description**: Log telemetry data to database

**Requirements**:
- Log inverter telemetry at configurable intervals (default: 1 minute)
- Log battery telemetry at configurable intervals
- Log meter telemetry at configurable intervals
- Handle logging errors gracefully
- Support batch inserts for performance
- Automatic aggregation to hourly/daily summaries

**Acceptance Criteria**:
- [ ] Telemetry logged to database
- [ ] Configurable logging intervals
- [ ] Error handling for logging failures
- [ ] Batch insert optimization
- [ ] Automatic hourly/daily aggregation

#### 2.3 Data Aggregation

**Requirement ID**: BE-006

**Description**: Aggregate telemetry data to hourly and daily summaries

**Requirements**:
- Aggregate inverter energy to hourly summaries
- Aggregate battery energy to hourly summaries
- Aggregate meter energy to hourly summaries
- Calculate daily totals
- Handle missing data gracefully
- Support backfilling of historical data

**Acceptance Criteria**:
- [ ] Hourly aggregations calculated correctly
- [ ] Daily summaries calculated correctly
- [ ] Missing data handled appropriately
- [ ] Backfill functionality works
- [ ] Aggregation runs on schedule

### 3. API Server

#### 3.1 Telemetry Endpoints

**Requirement ID**: BE-007

**Description**: REST API endpoints for real-time telemetry

**Endpoints**:
- `GET /api/now?inverter_id={id}` - Get current inverter telemetry
- `GET /api/now?inverter_id=all` - Get consolidated telemetry for all inverters
- `GET /api/battery/now?bank_id={id}` - Get current battery telemetry
- `GET /api/meter/now?meter_id={id}` - Get current meter telemetry
- `GET /api/telemetry?device={id}` - Get device telemetry (unified endpoint)

**Response Format**:
```json
{
  "device_id": "powdrive1",
  "timestamp": "2025-01-10T12:00:00Z",
  "telemetry": {
    "pv_power_w": 5000,
    "load_power_w": 3000,
    "grid_power_w": -2000,
    "batt_power_w": 1000,
    "batt_soc_pct": 75.5,
    ...
  },
  "_metadata": {
    "phase_type": "three",
    "inverter_count": 1
  }
}
```

**Acceptance Criteria**:
- [ ] All telemetry endpoints return standardized data
- [ ] Metadata included in responses
- [ ] Supports filtering by device ID
- [ ] Handles missing devices gracefully
- [ ] Returns appropriate HTTP status codes

#### 3.2 Historical Data Endpoints

**Requirement ID**: BE-008

**Description**: REST API endpoints for historical data

**Endpoints**:
- `GET /api/energy/hourly?inverter_id={id}&start_date={date}&end_date={date}` - Hourly energy data
- `GET /api/energy/daily?inverter_id={id}&start_date={date}&end_date={date}` - Daily energy summaries
- `GET /api/battery/hourly?bank_id={id}&start_date={date}&end_date={date}` - Battery hourly data
- `GET /api/battery/daily?bank_id={id}&start_date={date}&end_date={date}` - Battery daily summaries
- `GET /api/meter/hourly?meter_id={id}&start_date={date}&end_date={date}` - Meter hourly data

**Response Format**:
```json
{
  "device_id": "powdrive1",
  "data": [
    {
      "timestamp": "2025-01-10T00:00:00Z",
      "solar_kwh": 5.2,
      "load_kwh": 3.1,
      "grid_import_kwh": 0.5,
      "grid_export_kwh": 2.6,
      ...
    }
  ]
}
```

**Acceptance Criteria**:
- [ ] Returns data for specified date range
- [ ] Supports filtering by device/system/array
- [ ] Handles timezone correctly
- [ ] Returns empty array if no data
- [ ] Supports pagination for large datasets

#### 3.3 Configuration Endpoints

**Requirement ID**: BE-009

**Description**: REST API endpoints for system configuration

**Endpoints**:
- `GET /api/config` - Get system configuration
- `POST /api/config` - Update system configuration
- `GET /api/hierarchy` - Get system hierarchy
- `POST /api/hierarchy` - Update system hierarchy

**Configuration Includes**:
- System name, description, timezone
- Location (latitude, longitude)
- MQTT settings
- Billing configuration
- Forecast settings
- Inverter arrays
- Battery arrays
- Device attachments

**Acceptance Criteria**:
- [ ] Returns complete configuration
- [ ] Updates configuration correctly
- [ ] Validates configuration data
- [ ] Returns error messages for invalid data
- [ ] Persists configuration to database

#### 3.4 Device Management Endpoints

**Requirement ID**: BE-010

**Description**: REST API endpoints for device management

**Endpoints**:
- `GET /api/devices` - List all devices
- `GET /api/inverters` - List all inverters
- `GET /api/batteries` - List all battery banks
- `GET /api/meters` - List all meters
- `GET /api/device/{id}/settings` - Get device settings
- `POST /api/device/{id}/settings` - Update device settings
- `GET /api/inverter/{id}/specification` - Get inverter specification
- `GET /api/inverter/{id}/grid-settings` - Get grid settings
- `GET /api/inverter/{id}/battery-type` - Get battery type settings
- `GET /api/inverter/{id}/work-mode` - Get work mode settings
- `GET /api/inverter/{id}/tou-windows` - Get TOU windows
- `POST /api/inverter/{id}/grid-settings` - Update grid settings
- `POST /api/inverter/{id}/battery-type` - Update battery type settings
- `POST /api/inverter/{id}/work-mode` - Update work mode
- `POST /api/inverter/{id}/tou-windows` - Update TOU windows

**Acceptance Criteria**:
- [ ] Lists all devices correctly
- [ ] Returns device settings in standardized format
- [ ] Updates device settings via Modbus writes
- [ ] Validates settings before writing
- [ ] Returns read-back values after write

#### 3.5 Billing Endpoints

**Requirement ID**: BE-011

**Description**: REST API endpoints for billing data

**Endpoints**:
- `GET /api/billing/running?inverter_id={id}&date={date}` - Get running billing data
- `GET /api/billing/summary?year={year}` - Get billing summary for year
- `POST /api/billing/trigger?date={date}&backfill={bool}` - Trigger billing calculation

**Response Format**:
```json
{
  "status": "ok",
  "date": "2025-01-10",
  "billing_month_id": "2025-01",
  "import_off_kwh": 100.5,
  "export_off_kwh": 250.3,
  "import_peak_kwh": 50.2,
  "export_peak_kwh": 120.1,
  "bill_final_rs_to_date": 1500.75,
  ...
}
```

**Acceptance Criteria**:
- [ ] Calculates billing data correctly
- [ ] Supports TOU (Time-of-Use) tariffs
- [ ] Handles peak/off-peak periods
- [ ] Returns running totals for current month
- [ ] Supports manual trigger for calculations

#### 3.6 Hierarchy Management Endpoints

**Requirement ID**: BE-012

**Description**: REST API endpoints for system hierarchy management

**Endpoints**:
- `GET /api/systems` - List all systems
- `GET /api/systems/{id}` - Get system details
- `POST /api/systems` - Create system
- `PUT /api/systems/{id}` - Update system
- `DELETE /api/systems/{id}` - Delete system
- `GET /api/arrays` - List all arrays
- `POST /api/arrays` - Create array
- `PUT /api/arrays/{id}` - Update array
- `DELETE /api/arrays/{id}` - Delete array
- `GET /api/battery-arrays` - List battery arrays
- `POST /api/battery-arrays` - Create battery array
- `PUT /api/battery-arrays/{id}` - Update battery array
- `DELETE /api/battery-arrays/{id}` - Delete battery array
- `POST /api/battery-array-attachments` - Attach battery array to inverter array
- `DELETE /api/battery-array-attachments/{battery_array_id}/{inverter_array_id}` - Detach battery array

**Acceptance Criteria**:
- [ ] CRUD operations for all hierarchy entities
- [ ] Validates relationships (e.g., devices belong to arrays)
- [ ] Prevents orphaned devices
- [ ] Returns complete hierarchy structure
- [ ] Supports filtering by parent entity

### 4. Smart Scheduler

#### 4.1 Battery Optimization

**Requirement ID**: BE-013

**Description**: Intelligent battery charging/discharging optimization

**Requirements**:
- Tariff-aware scheduling
- TOU (Time-of-Use) window support
- Peak shaving capability
- Grid charge/discharge control
- Target SOC management
- Forecast integration for optimization

**Scheduling Modes**:
- Grid charging (charge from grid during off-peak)
- Solar priority (use solar first, then battery)
- Peak shaving (discharge during peak hours)
- Custom TOU windows

**Acceptance Criteria**:
- [ ] Schedules battery operations based on tariffs
- [ ] Respects TOU windows
- [ ] Optimizes for cost savings
- [ ] Handles forecast data
- [ ] Updates schedules dynamically

#### 4.2 Forecast Integration

**Requirement ID**: BE-014

**Description**: Integration with weather forecast services

**Requirements**:
- Solar production forecasting
- Load consumption forecasting
- Weather data integration (OpenWeather, WeatherAPI)
- Forecast accuracy tracking
- Multi-day forecast support

**Acceptance Criteria**:
- [ ] Fetches weather data from providers
- [ ] Calculates solar production forecasts
- [ ] Estimates load consumption
- [ ] Updates forecasts regularly
- [ ] Tracks forecast accuracy

### 5. MQTT Integration

#### 5.1 Home Assistant Discovery

**Requirement ID**: BE-015

**Description**: MQTT publishing for Home Assistant integration

**Requirements**:
- Auto-discovery configuration
- Device entities (sensors, switches, numbers)
- Real-time state updates
- Command handling
- Topic structure: `{base_topic}/{device_type}/{device_id}/{entity}`

**Entity Types**:
- Sensors: Power, energy, voltage, current, temperature, SOC
- Switches: Grid charge enable, TOU window enable
- Numbers: Target SOC, charge/discharge power limits

**Acceptance Criteria**:
- [ ] Publishes discovery configuration
- [ ] Updates entity states in real-time
- [ ] Handles commands from Home Assistant
- [ ] Supports custom topic structure
- [ ] Handles MQTT connection failures

### 6. Authentication & Security

#### 6.1 API Authentication

**Requirement ID**: BE-016

**Description**: Secure API access

**Requirements**:
- API key authentication
- Key management (create, revoke, list)
- Rate limiting
- CORS configuration
- Request logging

**Endpoints**:
- `POST /api/auth/keys` - Create API key
- `GET /api/auth/keys` - List API keys
- `DELETE /api/auth/keys/{key_id}` - Revoke API key

**Acceptance Criteria**:
- [ ] API keys required for protected endpoints
- [ ] Keys can be created and revoked
- [ ] Rate limiting prevents abuse
- [ ] CORS configured correctly
- [ ] Security best practices followed

---

## Frontend Requirements

### 1. Application Structure

#### 1.1 Multi-App Architecture

**Requirement ID**: FE-001

**Description**: Support multiple frontend applications

**Applications**:
- `start` - Main production application
- `default` - Default/legacy application
- `v0` - Version 0 application

**Shared Components**:
- Common API layer
- Shared UI components
- Shared hooks and utilities
- Shared contexts (Auth, Theme)

**Acceptance Criteria**:
- [ ] Multiple apps can run independently
- [ ] Shared code is properly organized
- [ ] Apps can be built and deployed separately
- [ ] No code duplication between apps

#### 1.2 Routing

**Requirement ID**: FE-002

**Description**: Client-side routing with React Router

**Routes**:
- `/` - Dashboard
- `/devices` - Device list
- `/devices/:deviceId/settings` - Device settings
- `/telemetry?device={id}` - Telemetry view
- `/billing` - Billing page
- `/billing/settings` - Billing configuration
- `/settings` - System settings
- `/smart-scheduler` - Smart scheduler configuration
- `/notifications` - Notifications
- `/profile` - User profile
- `/auth` - Authentication

**Acceptance Criteria**:
- [ ] All routes work correctly
- [ ] Protected routes require authentication
- [ ] URL parameters handled correctly
- [ ] Browser navigation works
- [ ] 404 page for unknown routes

### 2. Dashboard

#### 2.1 Dashboard Overview

**Requirement ID**: FE-003

**Description**: Main dashboard with key metrics and visualizations

**Components**:
- Stat cards (7 cards: Monthly Bill, Savings, CO₂, Production, Self-Consumption, Prediction, Avg kWh/kWp)
- Energy flow diagram
- Billing summary
- Energy overview chart (hourly)
- System overview (hierarchical device view)

**Stat Cards**:
1. Monthly Bill Estimate
2. Today's Savings
3. Total Savings
4. CO₂ Saved Today
5. Today's Production
6. Self-Consumption
7. Predicted vs Actual
8. Avg kWh/kWp

**Mobile Responsiveness**:
- 2-column grid on mobile
- Expandable additional stats
- Responsive padding and spacing
- Touch-friendly interface

**Acceptance Criteria**:
- [ ] All stat cards display correct data
- [ ] Energy flow diagram shows real-time data
- [ ] Billing summary displays current month data
- [ ] Energy chart shows hourly data
- [ ] System overview shows all devices
- [ ] Mobile view is fully responsive
- [ ] Data updates in real-time

#### 2.2 Energy Flow Diagram

**Requirement ID**: FE-004

**Description**: Visual representation of energy flow

**Requirements**:
- Solar panel icon with power value
- Battery icon with SOC and power
- Grid icon with import/export
- Load icon with consumption
- Animated flow indicators
- Color coding (green for export, orange for import)
- Real-time updates

**Acceptance Criteria**:
- [ ] Shows all energy flows
- [ ] Updates in real-time
- [ ] Animations work smoothly
- [ ] Color coding is correct
- [ ] Responsive on mobile

#### 2.3 Energy Chart

**Requirement ID**: FE-005

**Description**: Hourly energy overview chart

**Requirements**:
- Area chart showing solar, consumption, battery, grid
- 24-hour view (today)
- Stacked areas for visualization
- Tooltips with detailed values
- Responsive design
- Color coding for each series

**Data Series**:
- Solar (yellow/orange)
- Consumption (blue)
- Battery (cyan) - charge only (positive values)
- Grid (green for export, red for import)

**Acceptance Criteria**:
- [ ] Chart displays 24 hours of data
- [ ] All series visible and correctly colored
- [ ] Tooltips show accurate values
- [ ] Responsive on all screen sizes
- [ ] Updates when new data available

#### 2.4 System Overview

**Requirement ID**: FE-006

**Description**: Hierarchical view of all devices

**Requirements**:
- System-level grouping
- Inverter arrays with devices
- Battery arrays with packs
- Meters (home-level and system-level)
- Device status indicators
- Clickable device icons (navigate to telemetry)
- Hover cards with detailed metrics
- Aggregate statistics per section

**Layout**:
- Home meters section (if any)
- Systems list
- Each system shows:
  - Inverter array(s) with devices
  - Battery array(s) with packs
  - System-level meters

**Acceptance Criteria**:
- [ ] Shows complete hierarchy
- [ ] Device icons are clickable
- [ ] Hover cards show detailed info
- [ ] Status indicators are accurate
- [ ] Aggregate stats are correct
- [ ] Mobile responsive

### 3. Device Management

#### 3.1 Device List Page

**Requirement ID**: FE-007

**Description**: List all devices with filtering and search

**Features**:
- Device cards showing key metrics
- Search by name or serial number
- Filter by type (inverter, battery, meter)
- Filter by status (online, offline, warning)
- Device count display
- Add device button
- Click to view telemetry or configure

**Device Card Display**:
- Device icon and name
- Status indicator
- Key metrics grid (6 metrics)
- Model and serial number
- Action buttons (Telemetry, Configure)

**Mobile Responsiveness**:
- Single column layout
- Reduced padding
- Stacked action buttons
- Truncated text with break-words

**Acceptance Criteria**:
- [ ] Lists all devices
- [ ] Search works correctly
- [ ] Filters work correctly
- [ ] Device cards show accurate data
- [ ] Navigation to telemetry/settings works
- [ ] Mobile responsive

#### 3.2 Device Settings Page

**Requirement ID**: FE-008

**Description**: Configure device settings

**Device Types**:
- Inverter settings
- Battery settings
- Meter settings

**Inverter Settings Tabs**:
1. **System Tab**:
   - General settings (name, model, serial)
   - Adapter settings (connection parameters)
   - Safety settings (voltage/current limits, grid parameters)

2. **Power Tab**:
   - Solar array configuration
   - Battery configuration
   - Grid settings
   - Work mode settings

3. **Scheduling Tab**:
   - TOU (Time-of-Use) windows
   - Window configuration (start time, end time, power, target SOC, mode)
   - Enable/disable windows
   - Timeline visualization

**Settings Components**:
- `SettingRow` - Label and value display/edit
- `ToggleRow` - Boolean settings
- `SliderRow` - Numeric range settings
- `TOUWindowRow` - TOU window configuration
- `TOUTimeline` - Visual timeline of TOU windows

**Acceptance Criteria**:
- [ ] All settings load from backend
- [ ] Settings can be saved
- [ ] Validation prevents invalid values
- [ ] TOU windows display correctly
- [ ] Timeline visualization works
- [ ] Save confirmation shown
- [ ] Error handling for save failures

### 4. Telemetry Page

#### 4.1 Telemetry Overview

**Requirement ID**: FE-009

**Description**: Real-time device telemetry display

**Features**:
- Device selector dropdown
- Last updated timestamp
- Refresh button
- Export button
- Device type indicator card
- Device-specific telemetry view
- Alerts panel

**Device-Specific Views**:
- **Inverter**: Power flow cards, efficiency, temperature, historical charts
- **Battery**: Cell grid (if supported), SOC, voltage, current, temperature, charge/discharge
- **Meter**: Import/export power, cumulative energy, frequency, power factor

**Mobile Responsiveness**:
- Full-width device selector
- Stacked controls
- Icon-only buttons on mobile
- Responsive card layouts

**Acceptance Criteria**:
- [ ] Device selector works
- [ ] Telemetry updates in real-time
- [ ] Device-specific views display correctly
- [ ] Charts render properly
- [ ] Mobile responsive
- [ ] Refresh functionality works

#### 4.2 Inverter Telemetry

**Requirement ID**: FE-010

**Description**: Detailed inverter telemetry view

**Components**:
- Power flow cards (Solar, Grid, Load, Battery)
- Efficiency display
- Temperature display
- Historical charts (24-hour power, efficiency, temperature)
- Three-phase data (if applicable)

**Acceptance Criteria**:
- [ ] All power flows displayed
- [ ] Efficiency calculated correctly
- [ ] Charts show historical data
- [ ] Three-phase data shown when applicable
- [ ] Updates in real-time

#### 4.3 Battery Telemetry

**Requirement ID**: FE-011

**Description**: Detailed battery telemetry view

**Components**:
- Battery cell grid (if supported)
- SOC (State of Charge) display
- Voltage and current
- Temperature
- Charge/discharge power
- Historical charts

**Acceptance Criteria**:
- [ ] SOC displayed accurately
- [ ] Cell grid shows individual cells (if supported)
- [ ] Charge/discharge direction indicated
- [ ] Charts show historical data
- [ ] Updates in real-time

#### 4.4 Meter Telemetry

**Requirement ID**: FE-012

**Description**: Detailed meter telemetry view

**Components**:
- Current power (import/export)
- Cumulative energy (import/export)
- Net balance
- Frequency
- Power factor
- Historical charts

**Acceptance Criteria**:
- [ ] Import/export clearly indicated
- [ ] Cumulative energy accurate
- [ ] Net balance calculated correctly
- [ ] Charts show historical data
- [ ] Updates in real-time

### 5. Billing Management

#### 5.1 Billing Dashboard

**Requirement ID**: FE-013

**Description**: Billing overview and analysis

**Components**:
- Current month estimate
- Last month bill
- Export credits
- Total savings
- Monthly bill chart
- Energy breakdown chart
- TOU period breakdown
- Manual trigger for billing calculation

**Stats Cards**:
- Energy Produced
- Energy Consumed
- Net Import
- Net Export
- Bill Amount
- Savings

**Charts**:
- Monthly bill trend
- Energy breakdown (solar, import, export)
- TOU period comparison

**Acceptance Criteria**:
- [ ] All billing data displayed correctly
- [ ] Charts render properly
- [ ] Currency formatting correct
- [ ] Manual trigger works
- [ ] Data updates after trigger

#### 5.2 Billing Settings

**Requirement ID**: FE-014

**Description**: Configure billing parameters

**Settings**:
- Currency selection
- Import rate (off-peak, peak)
- Export rate (off-peak, peak)
- Fixed charges
- TOU periods (start/end times)
- Peak hours configuration

**Acceptance Criteria**:
- [ ] All settings load from backend
- [ ] Settings can be saved
- [ ] Validation prevents invalid values
- [ ] Currency changes reflected immediately
- [ ] TOU periods configurable

### 6. Smart Scheduler

#### 6.1 Scheduler Configuration

**Requirement ID**: FE-015

**Description**: Configure smart scheduling

**Settings**:
- Enable/disable scheduler
- Weather provider selection
- API keys for weather services
- Battery capacity
- Forecast settings
- Optimization preferences

**Tabs**:
- Forecast Settings
- Battery Optimization
- TOU Configuration
- Advanced Settings

**Acceptance Criteria**:
- [ ] All settings load from backend
- [ ] Settings can be saved
- [ ] Weather provider selection works
- [ ] Forecast preview available
- [ ] Optimization settings configurable

### 7. System Settings

#### 7.1 General Settings

**Requirement ID**: FE-016

**Description**: System-wide configuration

**Settings**:
- System name
- Description/Address
- Timezone
- Location (latitude, longitude)
- MQTT configuration
- Theme preferences

**Acceptance Criteria**:
- [ ] All settings load from backend
- [ ] Settings can be saved
- [ ] Timezone changes reflected
- [ ] Location can be set via map
- [ ] MQTT settings validated

#### 7.2 Hierarchy Management

**Requirement ID**: FE-017

**Description**: Manage system hierarchy

**Features**:
- Create/edit systems
- Create/edit inverter arrays
- Create/edit battery arrays
- Assign devices to arrays
- Attach battery arrays to inverter arrays
- Drag-and-drop interface (future)

**Acceptance Criteria**:
- [ ] Can create systems
- [ ] Can create arrays
- [ ] Can assign devices
- [ ] Can attach battery arrays
- [ ] Hierarchy displayed correctly
- [ ] Validation prevents invalid configurations

### 8. User Interface

#### 8.1 Layout Components

**Requirement ID**: FE-018

**Description**: Consistent layout across application

**Components**:
- `AppLayout` - Main layout wrapper
- `AppHeader` - Page header with title and subtitle
- `AppSidebar` - Navigation sidebar
- `MobileBottomNav` - Mobile navigation bar
- `ProtectedRoute` - Route protection component

**Sidebar Navigation**:
- Dashboard
- Devices
- Telemetry
- Billing
- Smart Scheduler
- Settings
- Notifications
- Profile

**Acceptance Criteria**:
- [ ] Layout consistent across pages
- [ ] Sidebar navigation works
- [ ] Mobile navigation works
- [ ] Header displays correct title
- [ ] Protected routes redirect to auth

#### 8.2 UI Components

**Requirement ID**: FE-019

**Description**: Reusable UI components

**Component Library** (Shadcn/ui):
- Button
- Input
- Select
- Switch
- Slider
- Card
- Tabs
- Accordion
- Dialog
- Toast
- Tooltip
- HoverCard
- Badge
- And more...

**Custom Components**:
- `StatCard` - Dashboard stat card
- `DeviceCard` - Device list card
- `LiveMetricCard` - Real-time metric display
- `EnergyFlowDiagram` - Energy flow visualization
- `VisualSystemDiagram` - System hierarchy view

**Acceptance Criteria**:
- [ ] All components work correctly
- [ ] Consistent styling
- [ ] Accessible (keyboard navigation, screen readers)
- [ ] Responsive design
- [ ] Dark mode support

#### 8.3 Responsive Design

**Requirement ID**: FE-020

**Description**: Mobile-first responsive design

**Breakpoints**:
- Mobile: < 640px (sm)
- Tablet: 640px - 1024px (md)
- Desktop: > 1024px (lg, xl)

**Mobile Optimizations**:
- Reduced padding and spacing
- Stacked layouts
- Icon-only buttons
- Collapsible sections
- Touch-friendly targets
- Optimized font sizes

**Acceptance Criteria**:
- [ ] All pages responsive
- [ ] Mobile navigation works
- [ ] Touch targets adequate size
- [ ] Text readable on small screens
- [ ] No horizontal scrolling
- [ ] Images scale properly

### 9. Data Management

#### 9.1 Data Fetching

**Requirement ID**: FE-021

**Description**: Efficient data fetching and caching

**Technology**: React Query (TanStack Query)

**Features**:
- Automatic caching
- Background refetching
- Stale-while-revalidate
- Request deduplication
- Error handling
- Loading states

**Cache Strategy**:
- Telemetry: 5 seconds TTL
- Configuration: 5 minutes TTL
- Historical data: 1 minute TTL
- Billing: 5 minutes TTL

**Acceptance Criteria**:
- [ ] Data cached appropriately
- [ ] Background updates work
- [ ] Loading states shown
- [ ] Error states handled
- [ ] No unnecessary requests

#### 9.2 Real-time Updates

**Requirement ID**: FE-022

**Description**: Real-time telemetry updates

**Implementation**:
- Polling service (DataSyncService)
- Configurable poll interval (default: 5 seconds)
- WebSocket support (future)
- Optimistic updates

**Acceptance Criteria**:
- [ ] Telemetry updates automatically
- [ ] Configurable poll interval
- [ ] No performance degradation
- [ ] Handles connection failures
- [ ] Resumes polling after reconnection

#### 9.3 Data Transformation

**Requirement ID**: FE-023

**Description**: Transform backend data for frontend use

**Transformations**:
- Hierarchy normalization
- Telemetry standardization
- Energy data aggregation
- Billing calculations
- Chart data formatting

**Acceptance Criteria**:
- [ ] Data transformed correctly
- [ ] Consistent data structure
- [ ] Performance optimized
- [ ] Error handling for invalid data

### 10. Authentication

#### 10.1 Authentication Flow

**Requirement ID**: FE-024

**Description**: User authentication

**Features**:
- Login page
- API key management
- Session management
- Protected routes
- Logout functionality

**Acceptance Criteria**:
- [ ] Login works correctly
- [ ] Protected routes redirect
- [ ] Session persists
- [ ] Logout clears session
- [ ] API key management works

---

## Integration Requirements

### 1. Backend-Frontend Integration

#### 1.1 API Communication

**Requirement ID**: INT-001

**Description**: Seamless API communication

**Requirements**:
- Consistent API client
- Error handling
- Request/response logging
- Type safety (TypeScript)
- API versioning support

**Acceptance Criteria**:
- [ ] All API calls use common client
- [ ] Errors handled gracefully
- [ ] TypeScript types match API
- [ ] Logging works correctly

### 2. Home Assistant Integration

#### 2.1 MQTT Integration

**Requirement ID**: INT-002

**Description**: Home Assistant MQTT integration

**Requirements**:
- Auto-discovery
- Entity state updates
- Command handling
- Topic structure
- Reconnection handling

**Acceptance Criteria**:
- [ ] Discovery messages published
- [ ] States update in real-time
- [ ] Commands handled correctly
- [ ] Reconnection works

---

## Non-Functional Requirements

### 1. Performance

**Requirement ID**: NFR-001

**Requirements**:
- API response time < 200ms (p95)
- Page load time < 2 seconds
- Real-time updates < 5 seconds latency
- Database queries optimized with indexes
- Frontend bundle size < 2MB (gzipped)

### 2. Scalability

**Requirement ID**: NFR-002

**Requirements**:
- Support 100+ devices
- Handle 1 million+ data points
- Concurrent API requests
- Efficient data aggregation

### 3. Reliability

**Requirement ID**: NFR-003

**Requirements**:
- 99.9% uptime
- Automatic error recovery
- Data backup and recovery
- Graceful degradation

### 4. Maintainability

**Requirement ID**: NFR-004

**Requirements**:
- Code documentation
- TypeScript for type safety
- Modular architecture
- Unit tests
- Integration tests

### 5. Usability

**Requirement ID**: NFR-005

**Requirements**:
- Intuitive user interface
- Mobile-friendly design
- Accessible (WCAG 2.1 AA)
- Fast response times
- Clear error messages

---

## Security Requirements

### 1. API Security

**Requirement ID**: SEC-001

**Requirements**:
- API key authentication
- HTTPS support
- Rate limiting
- Input validation
- SQL injection prevention
- XSS prevention

### 2. Data Security

**Requirement ID**: SEC-002

**Requirements**:
- Encrypted database (optional)
- Secure API key storage
- No sensitive data in logs
- Secure MQTT connection (TLS)

---

## Deployment Requirements

### 1. Backend Deployment

**Requirement ID**: DEP-001

**Requirements**:
- Python 3.8+ environment
- SQLite database
- Systemd service (Linux)
- Log rotation
- Health check endpoint

### 2. Frontend Deployment

**Requirement ID**: DEP-002

**Requirements**:
- Static file hosting
- Nginx/Apache configuration
- HTTPS support
- Service worker (PWA)
- Build optimization

### 3. Monitoring

**Requirement ID**: DEP-003

**Requirements**:
- Application logs
- Error tracking
- Performance monitoring
- Health checks

---

## Appendix

### A. API Endpoint Reference

See `API_REFERENCE.md` for complete API documentation.

### B. Database Schema

See `DATABASE_SCHEMA.md` for complete database schema.

### C. Component Library

See component documentation in `webapp-react/src/components/ui/`.

### D. Glossary

- **TOU**: Time-of-Use (tariff periods)
- **SOC**: State of Charge (battery percentage)
- **MPPT**: Maximum Power Point Tracking
- **Modbus**: Industrial communication protocol
- **MQTT**: Message Queuing Telemetry Transport
- **PWA**: Progressive Web App

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | January 2025 | System Analysis | Initial comprehensive requirements document |

---

**End of Document**
