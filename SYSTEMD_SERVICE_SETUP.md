# Systemd Service Setup Commands

Complete guide for creating and managing the solar monitoring systemd service.

## Quick Setup Commands

### Step 1: Determine Your Project Path

```bash
# Find your current project directory
pwd
# Example output: /home/faisal/solar-hub

# Or if you're in a different location
realpath .
```

### Step 2: Create Service User (Optional but Recommended)

```bash
# Create a dedicated user for the service (more secure)
sudo useradd -r -s /bin/false solar

# Or use your existing user (less secure but simpler)
# Skip this step if using your own user
```

### Step 3: Create Service File

```bash
# Edit the service file (adjust paths as needed)
sudo nano /etc/systemd/system/solar-monitoring.service
```

**Or create it directly:**

```bash
# Get your project path
PROJECT_DIR=$(pwd)
VENV_PATH="$PROJECT_DIR/venv"
USER_NAME=$(whoami)

# Create service file
sudo tee /etc/systemd/system/solar-monitoring.service > /dev/null <<EOF
[Unit]
Description=Solar Monitoring System
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_PATH/bin
ExecStart=$VENV_PATH/bin/python -m solarhub.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Optional: Set config file path
# Environment=SOLARHUB_CONFIG=$PROJECT_DIR/config.yaml

# Security settings (adjust if needed)
NoNewPrivileges=true
PrivateTmp=true
# ProtectSystem=strict  # Comment out if you need to write to system directories
# ProtectHome=true      # Comment out if database is in home directory
ReadWritePaths=$PROJECT_DIR
ReadWritePaths=/home/$USER_NAME/.solarhub

[Install]
WantedBy=multi-user.target
EOF
```

### Step 4: Reload Systemd and Enable Service

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable solar-monitoring

# Start the service
sudo systemctl start solar-monitoring

# Check status
sudo systemctl status solar-monitoring
```

---

## Complete Setup Script

Save this as `setup-service.sh`:

```bash
#!/bin/bash

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Setting up Solar Monitoring Systemd Service${NC}"
echo ""

# Get current directory
PROJECT_DIR=$(pwd)
VENV_PATH="$PROJECT_DIR/venv"
USER_NAME=$(whoami)

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_PATH${NC}"
    echo "Please create it first: python3 -m venv venv"
    exit 1
fi

# Check if config.yaml exists
if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
    echo -e "${YELLOW}Warning: config.yaml not found. Service may not work correctly.${NC}"
fi

echo "Project directory: $PROJECT_DIR"
echo "Virtual environment: $VENV_PATH"
echo "User: $USER_NAME"
echo ""

# Create service file
echo "Creating service file..."
sudo tee /etc/systemd/system/solar-monitoring.service > /dev/null <<EOF
[Unit]
Description=Solar Monitoring System
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_PATH/bin
ExecStart=$VENV_PATH/bin/python -m solarhub.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Optional: Set config file path
Environment=SOLARHUB_CONFIG=$PROJECT_DIR/config.yaml

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ReadWritePaths=$PROJECT_DIR
ReadWritePaths=/home/$USER_NAME/.solarhub

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Service file created${NC}"

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"

# Enable service
echo "Enabling service..."
sudo systemctl enable solar-monitoring
echo -e "${GREEN}✓ Service enabled${NC}"

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  sudo systemctl start solar-monitoring    # Start the service"
echo "  sudo systemctl status solar-monitoring   # Check status"
echo "  sudo journalctl -u solar-monitoring -f   # View logs"
```

Make it executable and run:
```bash
chmod +x setup-service.sh
./setup-service.sh
```

---

## Service Management Commands

### Start/Stop/Restart

```bash
# Start the service
sudo systemctl start solar-monitoring

# Stop the service
sudo systemctl stop solar-monitoring

# Restart the service
sudo systemctl restart solar-monitoring

# Reload configuration (if service file changed)
sudo systemctl daemon-reload
sudo systemctl restart solar-monitoring
```

### Check Status

```bash
# Check current status
sudo systemctl status solar-monitoring

# Check if service is running
sudo systemctl is-active solar-monitoring

# Check if service is enabled
sudo systemctl is-enabled solar-monitoring
```

### View Logs

```bash
# View recent logs
sudo journalctl -u solar-monitoring

# View logs with timestamps
sudo journalctl -u solar-monitoring -o short-precise

# Follow logs in real-time (like tail -f)
sudo journalctl -u solar-monitoring -f

# View last 100 lines
sudo journalctl -u solar-monitoring -n 100

# View logs since today
sudo journalctl -u solar-monitoring --since today

# View logs since specific time
sudo journalctl -u solar-monitoring --since "2024-01-01 10:00:00"

# View logs between dates
sudo journalctl -u solar-monitoring --since "2024-01-01" --until "2024-01-02"

# View only errors
sudo journalctl -u solar-monitoring -p err
```

### Enable/Disable on Boot

```bash
# Enable service to start on boot
sudo systemctl enable solar-monitoring

# Disable service from starting on boot
sudo systemctl disable solar-monitoring

# Enable and start in one command
sudo systemctl enable --now solar-monitoring
```

---

## Troubleshooting Commands

### Check Service Configuration

```bash
# Show service file
cat /etc/systemd/system/solar-monitoring.service

# Check service file syntax
systemd-analyze verify /etc/systemd/system/solar-monitoring.service

# Show service properties
systemctl show solar-monitoring
```

### Debug Service Issues

```bash
# Check if Python path is correct
sudo systemctl cat solar-monitoring | grep ExecStart

# Test the command manually
/your/path/to/venv/bin/python -m solarhub.main

# Check permissions
ls -la /etc/systemd/system/solar-monitoring.service
ls -la /your/project/directory

# Check if user can access files
sudo -u $USER ls -la /your/project/directory/config.yaml
```

### Common Issues

**Service fails to start:**
```bash
# Check detailed error
sudo journalctl -u solar-monitoring -n 50

# Check if Python is found
sudo systemctl cat solar-monitoring | grep ExecStart
# Then test that path manually
```

**Permission denied:**
```bash
# Fix ownership
sudo chown -R $USER:$USER /your/project/directory

# Or if using dedicated user
sudo chown -R solar:solar /your/project/directory
```

**Database location issues:**
```bash
# Ensure database directory is writable
mkdir -p ~/.solarhub
chmod 755 ~/.solarhub

# Or adjust service file ReadWritePaths
```

---

## Advanced Configuration

### Service File with Custom Config Path

```bash
sudo nano /etc/systemd/system/solar-monitoring.service
```

Add environment variable:
```ini
[Service]
...
Environment=SOLARHUB_CONFIG=/path/to/your/config.yaml
...
```

### Service File with Serial Port Access

If using Modbus RTU (serial port), add user to dialout group:

```bash
# Add user to dialout group for serial port access
sudo usermod -a -G dialout $USER

# Update service file to include device access
# Add to [Service] section:
DeviceAllow=/dev/ttyUSB0 rw
```

### Service File with Resource Limits

```ini
[Service]
...
# Limit memory usage (512MB)
MemoryLimit=512M

# Limit CPU usage (50%)
CPUQuota=50%

# Restart if memory limit exceeded
Restart=on-failure
...
```

### Service File with Network Dependency

```ini
[Unit]
...
After=network-online.target
Wants=network-online.target
...
```

---

## Quick Reference

```bash
# Setup
sudo systemctl daemon-reload
sudo systemctl enable solar-monitoring
sudo systemctl start solar-monitoring

# Status
sudo systemctl status solar-monitoring

# Logs
sudo journalctl -u solar-monitoring -f

# Restart
sudo systemctl restart solar-monitoring

# Stop
sudo systemctl stop solar-monitoring

# Disable
sudo systemctl disable solar-monitoring
```

---

## Example: Complete Setup for Your System

Based on your setup (`/home/faisal/solar-hub`):

```bash
# 1. Navigate to project
cd ~/solar-hub

# 2. Create service file
sudo tee /etc/systemd/system/solar-monitoring.service > /dev/null <<EOF
[Unit]
Description=Solar Monitoring System
After=network.target
Wants=network.target

[Service]
Type=simple
User=faisal
Group=faisal
WorkingDirectory=/home/faisal/solar-hub
Environment=PATH=/home/faisal/solar-hub/venv/bin
ExecStart=/home/faisal/solar-hub/venv/bin/python -m solarhub.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=SOLARHUB_CONFIG=/home/faisal/solar-hub/config.yaml
NoNewPrivileges=true
PrivateTmp=true
ReadWritePaths=/home/faisal/solar-hub
ReadWritePaths=/home/faisal/.solarhub

[Install]
WantedBy=multi-user.target
EOF

# 3. Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable solar-monitoring
sudo systemctl start solar-monitoring

# 4. Check status
sudo systemctl status solar-monitoring
```

---

## Verification

After setup, verify everything works:

```bash
# 1. Check service is running
sudo systemctl status solar-monitoring

# 2. Check logs for errors
sudo journalctl -u solar-monitoring -n 50

# 3. Test API endpoint (if web API is enabled)
curl http://localhost:8000/api/now

# 4. Check if process is running
ps aux | grep solarhub
```

That's it! Your service should now be running and will start automatically on boot.

