# Python Dependencies Guide

This document explains the different requirements files and how to use them.

## Requirements Files

### `requirements.txt` - Production Dependencies
**Use this for:** Production deployments, Docker containers, CI/CD pipelines

Contains all the essential dependencies needed to run the solar monitoring system:
- FastAPI and Uvicorn for the web API
- PyModbus and PySerial for Modbus communication
- Paho MQTT for MQTT messaging
- Pandas, NumPy for data processing
- pvlib for solar forecasting
- And other core dependencies

**Installation:**
```bash
pip install -r requirements.txt
```

### `requirements-test.txt` - Testing Dependencies
**Use this for:** Running tests, CI/CD test pipelines

Includes all production dependencies plus testing tools:
- pytest and pytest plugins
- Testing utilities

**Installation:**
```bash
pip install -r requirements-test.txt
```

### `requirements-dev.txt` - Development Dependencies
**Use this for:** Local development, contributing to the project

Includes all production dependencies plus:
- Testing tools (pytest, etc.)
- Code quality tools (black, flake8, mypy)
- Development utilities

**Installation:**
```bash
pip install -r requirements-dev.txt
```

## Quick Start

### For Production
```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate      # Windows

# Upgrade pip
pip install --upgrade pip

# Install production dependencies
pip install -r requirements.txt
```

### For Development
```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate      # Windows

# Upgrade pip
pip install --upgrade pip

# Install development dependencies (includes testing tools)
pip install -r requirements-dev.txt
```

## Dependency Categories

### Core Framework & API
- **fastapi**: Modern web framework for building APIs
- **uvicorn**: ASGI server for FastAPI
- **pydantic**: Data validation using Python type annotations
- **python-multipart**: Required for FastAPI file uploads

### Modbus Communication
- **pymodbus**: Modbus RTU/TCP client library
- **pyserial**: Serial port communication

### MQTT Communication
- **paho-mqtt**: MQTT client library

### Async & HTTP
- **uvloop**: Fast event loop implementation
- **aiohttp**: Async HTTP client/server library

### Data Processing
- **numpy**: Numerical computing
- **pandas**: Data manipulation and analysis

### Solar & Weather
- **pvlib**: Photovoltaic system modeling

### Configuration
- **pyyaml**: YAML parser for configuration files

### Date & Time
- **python-dateutil**: Date/time utilities
- **pytz**: Timezone definitions (legacy)
- **tzdata**: Timezone database

## Version Pinning Strategy

- **Exact versions (==)**: Used for critical dependencies where compatibility is crucial
- **Minimum versions (>=)**: Used for dependencies that are actively maintained
- **Upper bounds (<)**: Used to prevent breaking changes from major version updates

## Generating a Locked Requirements File

For production deployments, you may want to generate a locked requirements file with exact versions:

```bash
# Activate your virtual environment
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Generate locked requirements
pip freeze > requirements-lock.txt
```

**Note:** `requirements-lock.txt` is not included in the repository as it should be generated on each deployment to ensure compatibility with the target system.

## Troubleshooting

### Installation Issues

**Problem:** Package installation fails with hash mismatch
```bash
# Solution: Install without hash checking
pip install --no-deps -r requirements.txt
pip install pymodbus==3.11.2 paho-mqtt==1.6.1  # Install individually if needed
```

**Problem:** Build errors for packages requiring compilation
```bash
# Solution: Install build dependencies first
sudo apt install build-essential gcc g++ python3-dev  # Linux
# Then install requirements
pip install -r requirements.txt
```

**Problem:** Version conflicts
```bash
# Solution: Create a fresh virtual environment
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### System Dependencies

Some Python packages require system libraries:

**Linux (Ubuntu/Debian):**
```bash
sudo apt install \
    build-essential \
    gcc \
    g++ \
    libmodbus-dev \
    python3-dev
```

**Linux (CentOS/RHEL):**
```bash
sudo yum groupinstall "Development Tools"
sudo yum install \
    gcc \
    gcc-c++ \
    libmodbus-devel \
    python3-devel
```

## Updating Dependencies

### Check for Updates
```bash
pip list --outdated
```

### Update a Specific Package
```bash
pip install --upgrade <package-name>
```

### Update All Packages (Use with Caution)
```bash
pip install --upgrade -r requirements.txt
```

**Important:** After updating, test thoroughly and update version constraints in requirements.txt if needed.

## Python Version

This project requires **Python 3.11 or higher**.

Check your Python version:
```bash
python3 --version
```

If you need to install Python 3.11:
- **Linux:** Use `pyenv` or your distribution's package manager
- **macOS:** Use `pyenv` or Homebrew
- **Windows:** Download from python.org or use `pyenv-win`

## Additional Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [pip Documentation](https://pip.pypa.io/)
- [Virtual Environments Guide](https://docs.python.org/3/tutorial/venv.html)

