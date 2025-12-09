# SQLite Setup Guide

This project uses SQLite for data storage. SQLite is included with Python, but you may need to install system libraries or tools depending on your platform.

## Quick Answer

**For most users:** SQLite is already included with Python. No installation needed!

However, if you encounter errors, you may need to install the SQLite system library or command-line tools.

---

## Python's Built-in SQLite Support

Python includes the `sqlite3` module in its standard library (since Python 2.5). **No pip install is required.**

### Verify SQLite is Available

```bash
# Test if sqlite3 is available
python -c "import sqlite3; print(f'SQLite version: {sqlite3.sqlite_version}')"
```

If this works, you're all set! No further installation needed.

---

## System Requirements by Platform

### Windows

**SQLite is typically included with Python on Windows.** However, if you need the SQLite command-line tools:

#### Option 1: Download SQLite Tools (Recommended)
1. Visit: https://www.sqlite.org/download.html
2. Download "Precompiled Binaries for Windows"
3. Download `sqlite-tools-win-x64-*.zip` (or win-x86 for 32-bit)
4. Extract to a folder (e.g., `C:\sqlite`)
5. Add to PATH (optional):
   - Add `C:\sqlite` to your system PATH
   - Or use full path: `C:\sqlite\sqlite3.exe`

#### Option 2: Using Chocolatey
```powershell
choco install sqlite
```

#### Option 3: Using Scoop
```powershell
scoop install sqlite
```

### Linux (Ubuntu/Debian)

**SQLite is usually pre-installed.** If not:

```bash
# Install SQLite system library and tools
sudo apt update
sudo apt install sqlite3 libsqlite3-dev

# Verify installation
sqlite3 --version
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"
```

### Linux (CentOS/RHEL)

```bash
# Install SQLite
sudo yum install sqlite sqlite-devel

# Or for newer versions
sudo dnf install sqlite sqlite-devel
```

### macOS

**SQLite is pre-installed on macOS.** If you need a newer version:

```bash
# Using Homebrew
brew install sqlite

# Verify
sqlite3 --version
```

---

## Troubleshooting

### Error: "No module named '_sqlite3'"

This means Python was compiled without SQLite support. Solutions:

#### Windows
- Reinstall Python from python.org (official builds include SQLite)
- Or use a Python distribution like Anaconda

#### Linux
```bash
# Install SQLite development libraries
sudo apt install libsqlite3-dev python3-dev  # Ubuntu/Debian
sudo yum install sqlite-devel python3-devel  # CentOS/RHEL

# Reinstall Python or rebuild Python with SQLite support
```

#### macOS
```bash
# Install SQLite development libraries
brew install sqlite

# If using pyenv, rebuild Python
pyenv install --force 3.11.9
```

### Error: "sqlite3.OperationalError: database is locked"

This usually means:
- Another process is using the database
- Database file permissions are incorrect
- File system issues

**Solutions:**
```bash
# Check if another process is using the database
# Windows: Use Process Explorer or Task Manager
# Linux/macOS:
lsof solarhub.db

# Fix permissions (Linux/macOS)
chmod 644 solarhub.db
```

### Error: "sqlite3.DatabaseError: database disk image is malformed"

The database file may be corrupted. **Backup first**, then:

```bash
# Try to recover (using SQLite command-line tool)
sqlite3 solarhub.db ".recover" | sqlite3 solarhub_recovered.db

# Or use Python
python -c "
import sqlite3
con = sqlite3.connect('solarhub_recovered.db')
con.execute('ATTACH DATABASE \"solarhub.db\" AS corrupted')
con.execute('BEGIN')
for row in con.execute('SELECT sql FROM corrupted.sqlite_master WHERE type=\"table\"'):
    con.execute(row[0])
con.execute('INSERT INTO main.table_name SELECT * FROM corrupted.table_name')
con.commit()
"
```

---

## SQLite Command-Line Tools (Optional)

The SQLite command-line tool (`sqlite3`) is useful for:
- Manual database inspection
- Running SQL queries
- Database maintenance
- Backup and restore

### Basic Usage

```bash
# Open database
sqlite3 solarhub.db

# Run SQL commands
sqlite3 solarhub.db "SELECT COUNT(*) FROM energy_samples;"

# Export database
sqlite3 solarhub.db ".dump" > backup.sql

# Import database
sqlite3 new_database.db < backup.sql

# Show tables
sqlite3 solarhub.db ".tables"

# Show schema
sqlite3 solarhub.db ".schema"

# Exit
.quit
```

### Useful SQLite Commands

```sql
-- Show all tables
.tables

-- Show schema for a table
.schema energy_samples

-- Show database info
.dbinfo

-- Export to CSV
.mode csv
.headers on
.output data.csv
SELECT * FROM energy_samples LIMIT 100;

-- Set output mode
.mode column
.headers on

-- Show query results nicely
SELECT * FROM energy_samples LIMIT 10;
```

---

## Database Location

The project stores the SQLite database at:

**Default location:**
- Linux/macOS: `~/.solarhub/solarhub.db`
- Windows: `C:\Users\<username>\.solarhub\solarhub.db`

**Project root (if specified):**
- `./solarhub.db` (in the project directory)

### Find Your Database

```bash
# Python script to find database
python -c "
from solarhub.logging.logger import DataLogger
logger = DataLogger()
print(f'Database path: {logger.path}')
"
```

---

## Database Management

### Backup Database

```bash
# Using SQLite command-line tool
sqlite3 solarhub.db ".backup backup.db"

# Or copy the file directly
cp solarhub.db solarhub_backup.db  # Linux/macOS
copy solarhub.db solarhub_backup.db  # Windows
```

### Check Database Size

```bash
# Linux/macOS
ls -lh solarhub.db

# Windows
dir solarhub.db

# Or using SQLite
sqlite3 solarhub.db "SELECT page_count * page_size / 1024.0 / 1024.0 as size_mb FROM pragma_page_count(), pragma_page_size();"
```

### Optimize Database

```bash
# Using SQLite
sqlite3 solarhub.db "VACUUM;"

# Or using Python
python -c "
from solarhub.database_optimizer import DatabaseOptimizer
from solarhub.logging.logger import DataLogger
logger = DataLogger()
optimizer = DatabaseOptimizer(logger.path)
optimizer.optimize_database()
"
```

---

## Python SQLite Usage in This Project

The project uses SQLite for:

1. **Telemetry Storage** (`solarhub/logging/logger.py`)
   - Stores energy samples, battery data, inverter telemetry

2. **Configuration Storage** (`solarhub/config_manager.py`)
   - Stores configuration changes from Home Assistant

3. **API Key Management** (`solarhub/api_key_manager.py`)
   - Stores encrypted API keys

4. **Data Analysis** (`solarhub/schedulers/`)
   - Load learning, bias learning, reliability tracking

### Example: Check Database Contents

```python
import sqlite3
from solarhub.logging.logger import DataLogger

logger = DataLogger()
con = sqlite3.connect(logger.path)
cur = con.cursor()

# Count records
cur.execute("SELECT COUNT(*) FROM energy_samples")
print(f"Total records: {cur.fetchone()[0]}")

# Show recent records
cur.execute("SELECT * FROM energy_samples ORDER BY ts DESC LIMIT 5")
for row in cur.fetchall():
    print(row)

con.close()
```

---

## Summary

1. **SQLite is included with Python** - No pip install needed
2. **Verify it works:** `python -c "import sqlite3; print(sqlite3.sqlite_version)"`
3. **If errors occur:** Install SQLite system library for your platform
4. **Optional:** Install SQLite command-line tools for manual database operations

The project will automatically create and manage the SQLite database when you run it. No manual setup required!

---

## Additional Resources

- [SQLite Official Website](https://www.sqlite.org/)
- [Python sqlite3 Documentation](https://docs.python.org/3/library/sqlite3.html)
- [SQLite Tutorial](https://www.sqlitetutorial.net/)

