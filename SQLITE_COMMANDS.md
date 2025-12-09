# SQLite Database Access Commands

Quick reference guide for accessing and managing the solar monitoring SQLite database.

## Finding the Database Location

### Using Python
```bash
# Find the default database path
python -c "from solarhub.logging.logger import DataLogger; logger = DataLogger(); print(logger.path)"
```

### Default Locations
- **Linux/macOS**: `~/.solarhub/solarhub.db`
- **Windows**: `C:\Users\<username>\.solarhub\solarhub.db`
- **Project root**: `./solarhub.db` (if specified in config)

---

## Opening the Database

### Command-Line Interface
```bash
# Open database interactively
sqlite3 solarhub.db

# Or with full path
sqlite3 ~/.solarhub/solarhub.db

# Windows
sqlite3 C:\Users\<username>\.solarhub\solarhub.db
```

### One-Line Commands (Non-Interactive)
```bash
# Run a single SQL command
sqlite3 solarhub.db "SELECT COUNT(*) FROM energy_samples;"

# Run multiple commands
sqlite3 solarhub.db "SELECT COUNT(*) FROM energy_samples; SELECT COUNT(*) FROM pv_daily;"
```

---

## Essential SQLite Commands

### Inside SQLite CLI (Interactive Mode)

```sql
-- Show all tables
.tables

-- Show schema for all tables
.schema

-- Show schema for specific table
.schema energy_samples

-- Show database file info
.dbinfo

-- Show SQLite version
.version

-- Set output format (column mode with headers)
.mode column
.headers on

-- Set output format (CSV)
.mode csv
.headers on

-- Set output format (table)
.mode table

-- Set output format (JSON)
.mode json

-- Export query results to file
.output results.txt
SELECT * FROM energy_samples LIMIT 10;
.output stdout

-- Exit SQLite
.quit
```

---

## Common Queries

### Basic Inspection

```bash
# Count total records
sqlite3 solarhub.db "SELECT COUNT(*) as total_records FROM energy_samples;"

# Show table structure
sqlite3 solarhub.db ".schema energy_samples"

# List all tables
sqlite3 solarhub.db ".tables"

# Show recent records (last 10)
sqlite3 solarhub.db "SELECT * FROM energy_samples ORDER BY ts DESC LIMIT 10;"

# Show date range of data
sqlite3 solarhub.db "SELECT MIN(ts) as oldest, MAX(ts) as newest FROM energy_samples;"
```

### Data Queries

```bash
# Get latest telemetry for an inverter
sqlite3 solarhub.db "SELECT * FROM energy_samples WHERE inverter_id='senergy1' ORDER BY ts DESC LIMIT 1;"

# Count records per inverter
sqlite3 solarhub.db "SELECT inverter_id, COUNT(*) as count FROM energy_samples GROUP BY inverter_id;"

# Get records from last 24 hours
sqlite3 solarhub.db "SELECT * FROM energy_samples WHERE ts >= datetime('now', '-1 day') ORDER BY ts DESC;"

# Get daily PV energy totals
sqlite3 solarhub.db "SELECT * FROM pv_daily ORDER BY day DESC LIMIT 10;"

# Get battery SOC over time
sqlite3 solarhub.db "SELECT ts, inverter_id, soc, battery_soc FROM energy_samples WHERE soc IS NOT NULL ORDER BY ts DESC LIMIT 20;"
```

### Statistics

```bash
# Database size
sqlite3 solarhub.db "SELECT page_count * page_size / 1024.0 / 1024.0 as size_mb FROM pragma_page_count(), pragma_page_size();"

# Record counts by table
sqlite3 solarhub.db "
SELECT 'energy_samples' as table_name, COUNT(*) as count FROM energy_samples
UNION ALL
SELECT 'pv_daily', COUNT(*) FROM pv_daily
UNION ALL
SELECT 'configuration', COUNT(*) FROM configuration;
"

# Records per day
sqlite3 solarhub.db "SELECT date(ts) as day, COUNT(*) as count FROM energy_samples GROUP BY date(ts) ORDER BY day DESC LIMIT 10;"
```

---

## Python Scripts for Database Access

### Quick Python Access

```python
# Quick access script
import sqlite3
from solarhub.logging.logger import DataLogger

# Get database path
logger = DataLogger()
db_path = logger.path
print(f"Database: {db_path}")

# Connect and query
con = sqlite3.connect(db_path)
cur = con.cursor()

# Count records
cur.execute("SELECT COUNT(*) FROM energy_samples")
print(f"Total records: {cur.fetchone()[0]}")

# Get recent records
cur.execute("SELECT * FROM energy_samples ORDER BY ts DESC LIMIT 5")
for row in cur.fetchall():
    print(row)

con.close()
```

### Save as `query_db.py`:
```python
#!/usr/bin/env python3
"""Quick database query script"""
import sqlite3
import sys
from solarhub.logging.logger import DataLogger

logger = DataLogger()
con = sqlite3.connect(logger.path)
con.row_factory = sqlite3.Row  # Access columns by name
cur = con.cursor()

if len(sys.argv) > 1:
    query = sys.argv[1]
    cur.execute(query)
    rows = cur.fetchall()
    for row in rows:
        print(dict(row))
else:
    # Default: show recent records
    cur.execute("SELECT * FROM energy_samples ORDER BY ts DESC LIMIT 10")
    for row in cur.fetchall():
        print(dict(row))

con.close()
```

**Usage:**
```bash
python query_db.py "SELECT COUNT(*) as count FROM energy_samples"
```

---

## Useful One-Liners

### Quick Stats
```bash
# Total records
sqlite3 solarhub.db "SELECT COUNT(*) FROM energy_samples;"

# Database size (MB)
sqlite3 solarhub.db "SELECT ROUND(page_count * page_size / 1024.0 / 1024.0, 2) as size_mb FROM pragma_page_count(), pragma_page_size();"

# Latest timestamp
sqlite3 solarhub.db "SELECT MAX(ts) as latest FROM energy_samples;"

# Records today
sqlite3 solarhub.db "SELECT COUNT(*) FROM energy_samples WHERE date(ts) = date('now');"
```

### Export Data
```bash
# Export to CSV
sqlite3 -header -csv solarhub.db "SELECT * FROM energy_samples WHERE date(ts) = date('now')" > today_data.csv

# Export to JSON (requires jq or Python)
sqlite3 solarhub.db "SELECT json_group_array(json_object('ts', ts, 'inverter_id', inverter_id, 'pv_power_w', pv_power_w)) FROM energy_samples LIMIT 100" > data.json
```

### Backup
```bash
# Backup database
sqlite3 solarhub.db ".backup backup_$(date +%Y%m%d).db"

# Or simple copy
cp solarhub.db solarhub_backup.db  # Linux/macOS
copy solarhub.db solarhub_backup.db  # Windows
```

---

## Table-Specific Queries

### energy_samples Table
```bash
# Latest telemetry
sqlite3 solarhub.db "SELECT * FROM energy_samples ORDER BY ts DESC LIMIT 1;"

# Power flow summary
sqlite3 solarhub.db "
SELECT 
    ts,
    inverter_id,
    pv_power_w,
    load_power_w,
    grid_power_w,
    soc,
    battery_voltage_v
FROM energy_samples 
ORDER BY ts DESC 
LIMIT 10;
"

# Average power by hour
sqlite3 solarhub.db "
SELECT 
    strftime('%H', ts) as hour,
    AVG(pv_power_w) as avg_pv,
    AVG(load_power_w) as avg_load
FROM energy_samples
GROUP BY hour
ORDER BY hour;
"
```

### pv_daily Table
```bash
# Daily PV totals
sqlite3 solarhub.db "SELECT * FROM pv_daily ORDER BY day DESC;"

# Total PV by inverter
sqlite3 solarhub.db "SELECT inverter_id, SUM(pv_kwh) as total_kwh FROM pv_daily GROUP BY inverter_id;"

# This month's PV
sqlite3 solarhub.db "
SELECT SUM(pv_kwh) as total_kwh 
FROM pv_daily 
WHERE strftime('%Y-%m', day) = strftime('%Y-%m', 'now');
"
```

### configuration Table
```bash
# Show all configuration
sqlite3 solarhub.db "SELECT * FROM configuration;"

# Show recent changes
sqlite3 solarhub.db "SELECT * FROM configuration ORDER BY updated_at DESC;"
```

---

## Maintenance Commands

### Optimize Database
```bash
# Vacuum (reclaim space, optimize)
sqlite3 solarhub.db "VACUUM;"

# Analyze (update statistics)
sqlite3 solarhub.db "ANALYZE;"

# Both
sqlite3 solarhub.db "VACUUM; ANALYZE;"
```

### Check Integrity
```bash
# Quick check
sqlite3 solarhub.db "PRAGMA quick_check;"

# Full integrity check
sqlite3 solarhub.db "PRAGMA integrity_check;"
```

### Create Indexes (if missing)
```bash
sqlite3 solarhub.db "
CREATE INDEX IF NOT EXISTS idx_energy_samples_inverter_ts 
ON energy_samples(inverter_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_energy_samples_ts 
ON energy_samples(ts DESC);
"
```

---

## Formatting Output

### Pretty Table Format
```bash
sqlite3 -header -column solarhub.db "SELECT * FROM energy_samples LIMIT 5;"
```

### CSV Format
```bash
sqlite3 -header -csv solarhub.db "SELECT * FROM energy_samples LIMIT 5;" > output.csv
```

### JSON Format
```bash
sqlite3 -json solarhub.db "SELECT * FROM energy_samples LIMIT 5;"
```

### Line Mode (one value per line)
```bash
sqlite3 -line solarhub.db "SELECT * FROM energy_samples LIMIT 1;"
```

---

## Windows-Specific Commands

```powershell
# Open database
sqlite3.exe C:\Users\<username>\.solarhub\solarhub.db

# Or if in project directory
sqlite3.exe solarhub.db

# Run query
sqlite3.exe solarhub.db "SELECT COUNT(*) FROM energy_samples;"

# Export to CSV
sqlite3.exe -header -csv solarhub.db "SELECT * FROM energy_samples LIMIT 100" > output.csv
```

---

## Quick Reference Card

```bash
# Open database
sqlite3 solarhub.db

# Show tables
.tables

# Show schema
.schema

# Count records
SELECT COUNT(*) FROM energy_samples;

# Latest record
SELECT * FROM energy_samples ORDER BY ts DESC LIMIT 1;

# Export to CSV
.mode csv
.headers on
.output data.csv
SELECT * FROM energy_samples;
.output stdout

# Exit
.quit
```

---

## Troubleshooting

### Database Locked
```bash
# Check what's using it
lsof solarhub.db  # Linux/macOS
# Windows: Use Process Explorer

# If safe, you can force unlock (use with caution)
sqlite3 solarhub.db "PRAGMA busy_timeout = 30000;"
```

### Database Not Found
```bash
# Find it
python -c "from solarhub.logging.logger import DataLogger; print(DataLogger().path)"

# Or check default location
ls ~/.solarhub/solarhub.db  # Linux/macOS
dir C:\Users\%USERNAME%\.solarhub\solarhub.db  # Windows
```

### Permission Denied
```bash
# Fix permissions (Linux/macOS)
chmod 644 solarhub.db

# Or make writable
chmod 666 solarhub.db
```

---

## Advanced: Using Python for Complex Queries

```python
import sqlite3
import pandas as pd
from solarhub.logging.logger import DataLogger

logger = DataLogger()
con = sqlite3.connect(logger.path)

# Load into pandas DataFrame
df = pd.read_sql_query(
    "SELECT * FROM energy_samples WHERE ts >= datetime('now', '-7 days')",
    con
)

# Analyze with pandas
print(df.describe())
print(df.groupby('inverter_id')['pv_power_w'].mean())

con.close()
```

---

**Tip:** Save frequently used queries in a file and run them with:
```bash
sqlite3 solarhub.db < queries.sql
```

