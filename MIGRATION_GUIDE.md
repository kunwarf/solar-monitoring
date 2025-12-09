# Solar Monitoring System - New Machine Setup & Migration Guide

This comprehensive guide will help you set up a new machine and migrate your solar monitoring system (backend, frontend, and mobile) from your current machine.

## Table of Contents
1. [Prerequisites & Installation](#prerequisites--installation)
2. [Backend Migration](#backend-migration)
3. [Frontend Migration](#frontend-migration)
4. [Mobile Migration](#mobile-migration)
5. [Configuration Files](#configuration-files)
6. [Database Migration](#database-migration)
7. [Verification & Testing](#verification--testing)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites & Installation

### System Requirements

**Operating System:**
- **Linux**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / RHEL 8+
- **Windows**: Windows 10/11 (for development)
- **macOS**: macOS 10.15+ (for development, especially mobile)

### Required Software

#### 1. Python 3.11+ (Backend)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev python3-pip -y

# Verify installation
python3 --version  # Should show 3.11 or higher
pip3 --version
```

**Alternative: Using pyenv (Recommended)**
```bash
# Install pyenv
curl https://pyenv.run | bash

# Add to shell profile (~/.bashrc or ~/.zshrc)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Install Python 3.11
pyenv install 3.11.9
pyenv global 3.11.9
```

#### 2. Node.js 20+ (Frontend & Mobile)
```bash
# Using NodeSource (Recommended)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version  # Should show v20.x.x or higher
npm --version
```

**Alternative: Using nvm (Recommended for Development)**
```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Reload shell
source ~/.bashrc

# Install Node.js 20
nvm install 20
nvm use 20
nvm alias default 20
```

#### 3. Git
```bash
sudo apt install git -y
git --version
```

#### 4. System Dependencies (Backend)
```bash
# For Modbus RTU support
sudo apt install libmodbus-dev -y

# For serial port access (Linux)
sudo apt install setserial -y

# Build tools (for some Python packages)
sudo apt install build-essential gcc g++ -y
```

#### 5. Additional Tools (Optional but Recommended)
```bash
# Docker & Docker Compose (for containerized deployment)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Nginx (for production frontend deployment)
sudo apt install nginx -y

# MQTT Broker (if not using Docker)
sudo apt install mosquitto mosquitto-clients -y
```

#### 6. Mobile Development Tools (For Mobile Module)

**For iOS Development (macOS only):**
```bash
# Install Xcode from App Store
# Install CocoaPods
sudo gem install cocoapods
```

**For Android Development:**
```bash
# Install Android Studio from https://developer.android.com/studio
# Set up Android SDK and environment variables
export ANDROID_HOME=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/tools/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

**Expo CLI (for Mobile):**
```bash
npm install -g expo-cli
# Or use npx (no global install needed)
```

---

## Backend Migration

### Step 1: Transfer Project Files

**Option A: Using Git (Recommended)**
```bash
# On new machine
cd ~
git clone <your-repository-url> solar-monitoring
cd solar-monitoring
```

**Option B: Using SCP/RSYNC**
```bash
# From old machine
cd /path/to/solar-monitoring
tar -czf solar-monitoring-backup.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='node_modules' \
    --exclude='.git' \
    .

# Transfer to new machine
scp solar-monitoring-backup.tar.gz user@new-machine:/home/user/

# On new machine
cd ~
tar -xzf solar-monitoring-backup.tar.gz -C solar-monitoring
cd solar-monitoring
```

### Step 2: Set Up Python Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Backend

```bash
# Copy example config
cp config.example.yaml config.yaml

# Edit configuration (see Configuration Files section)
nano config.yaml  # or use your preferred editor
```

### Step 4: Set Permissions (Linux)

```bash
# If using serial ports (Modbus RTU)
sudo usermod -a -G dialout $USER
# Log out and back in for group changes to take effect

# Set proper permissions for database
chmod 644 solarhub.db  # if database exists
```

### Step 5: Test Backend

```bash
# Activate virtual environment
source venv/bin/activate

# Test import
python -c "import solarhub; print('Backend imports OK')"

# Run backend (for testing)
python -m solarhub.main
```

---

## Frontend Migration

### Step 1: Navigate to Frontend Directory

```bash
cd webapp-react
```

### Step 2: Install Dependencies

```bash
# Install Node.js dependencies
npm install

# If you encounter issues, try:
npm install --legacy-peer-deps
```

### Step 3: Configure Frontend

Check and update API endpoint in `src/config.ts`:
```typescript
export const API_BASE_URL = 'http://your-backend-url:8000';
```

### Step 4: Build Frontend (Production)

```bash
# Build for production
npm run build

# Output will be in 'dist' directory
```

### Step 5: Test Frontend

```bash
# Development server
npm run dev

# Preview production build
npm run preview
```

---

## Mobile Migration

### Step 1: Navigate to Mobile Directory

```bash
cd mobile
```

### Step 2: Install Dependencies

```bash
# Install Node.js dependencies
npm install

# If you encounter issues, try:
npm install --legacy-peer-deps
```

### Step 3: Configure Mobile App

Update API endpoint in `src/config.ts`:
```typescript
export const API_BASE_URL = 'http://your-backend-url:8000';
```

**Important:** For mobile devices:
- Use your machine's local IP address (e.g., `http://192.168.1.100:8000`)
- Or use a tunnel service if testing remotely
- Ensure backend allows connections from mobile device network

### Step 4: Test Mobile App

```bash
# Start Expo development server
npm start

# Or use specific commands
npm run start:simple    # LAN mode (same network)
npm run start:tunnel    # Tunnel mode (works from anywhere)

# For specific platforms
npm run android         # Android
npm run ios            # iOS (macOS only)
npm run web            # Web browser
```

### Step 5: Install Expo Go (For Physical Device Testing)

- **iOS**: Install "Expo Go" from App Store
- **Android**: Install "Expo Go" from Google Play Store

Scan the QR code from the terminal with Expo Go app.

---

## Configuration Files

### Critical Files to Migrate

These files contain important configuration and should be transferred:

1. **`config.yaml`** - Main backend configuration
   - MQTT settings
   - Inverter configurations
   - Smart scheduler settings
   - API keys (OpenWeather, etc.)

2. **`solarhub.db`** - SQLite database (if using)
   - Contains historical data
   - Inverter configurations
   - Settings

3. **`register_maps/*.json`** - Register mapping files
   - Custom register definitions

4. **`mosquitto.conf`** - MQTT broker configuration (if using)

5. **`.env`** - Environment variables (if using Docker)

### Configuration Checklist

- [ ] MQTT broker host and credentials
- [ ] Inverter serial ports or IP addresses
- [ ] API keys (OpenWeather, WeatherAPI, etc.)
- [ ] Timezone settings
- [ ] Smart scheduler parameters
- [ ] Database path and settings
- [ ] Frontend API endpoint URL
- [ ] Mobile app API endpoint URL

---

## Database Migration

### SQLite Database (Default)

```bash
# Copy database file
scp old-machine:/path/to/solar-monitoring/solarhub.db new-machine:/path/to/solar-monitoring/

# Or if using tar backup
# Database should be included in the backup

# Set permissions
chmod 644 solarhub.db
```

### PostgreSQL (If Using)

```bash
# On old machine - Export database
pg_dump -U solar -d solar_monitoring > solar_monitoring_backup.sql

# Transfer to new machine
scp solar_monitoring_backup.sql user@new-machine:/home/user/

# On new machine - Import database
psql -U solar -d solar_monitoring < solar_monitoring_backup.sql
```

### Database Migration Scripts

If you have pending migrations:
```bash
# Run timezone migration (if needed)
python run_timezone_migration.py

# Run other migrations as needed
python database_migration_v2.py
```

---

## Verification & Testing

### 1. Backend Verification

```bash
# Check if backend starts
source venv/bin/activate
python -m solarhub.main

# In another terminal, test API
curl http://localhost:8000/api/now

# Check inverter connection
curl http://localhost:8000/api/inverters
```

### 2. Frontend Verification

```bash
cd webapp-react
npm run dev

# Open browser to http://localhost:5173 (Vite default)
# Check browser console for errors
```

### 3. Mobile Verification

```bash
cd mobile
npm start

# Scan QR code with Expo Go app
# Verify data loads correctly
# Check for connection errors
```

### 4. Integration Testing

```bash
# Test full stack
# 1. Backend running on port 8000
# 2. Frontend can connect to backend
# 3. Mobile app can connect to backend
# 4. All three modules show consistent data
```

---

## Production Deployment

### Option 1: Systemd Service (Linux)

```bash
# Copy service file
sudo cp solar-monitoring.service /etc/systemd/system/

# Edit service file to match your paths
sudo nano /etc/systemd/system/solar-monitoring.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable solar-monitoring
sudo systemctl start solar-monitoring

# Check status
sudo systemctl status solar-monitoring

# View logs
sudo journalctl -u solar-monitoring -f
```

### Option 2: Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### Option 3: Nginx for Frontend

```bash
# Copy nginx configuration
sudo cp nginx-site.conf /etc/nginx/sites-available/solar-monitoring
sudo ln -s /etc/nginx/sites-available/solar-monitoring /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

---

## Troubleshooting

### Common Issues

#### 1. Python Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 2. Node.js Version Issues
```bash
# Check Node.js version
node --version  # Should be 20+

# Use nvm to switch versions
nvm use 20
```

#### 3. Serial Port Permission Issues (Linux)
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Log out and back in
# Check permissions
ls -l /dev/ttyUSB0
```

#### 4. Port Already in Use
```bash
# Check what's using the port
sudo lsof -i :8000  # Backend
sudo lsof -i :5173  # Frontend dev server

# Kill process if needed
sudo kill -9 <PID>
```

#### 5. Database Locked
```bash
# Check if another process is using the database
lsof solarhub.db

# Stop backend service if running
sudo systemctl stop solar-monitoring
```

#### 6. Mobile App Can't Connect
- Check firewall settings
- Verify API URL in `mobile/src/config.ts`
- Ensure backend is accessible from mobile device network
- Try tunnel mode: `npm run start:tunnel`

#### 7. MQTT Connection Issues
```bash
# Test MQTT broker
mosquitto_pub -h localhost -t test -m "test"
mosquitto_sub -h localhost -t test

# Check MQTT configuration in config.yaml
```

### Getting Help

1. Check logs:
   - Backend: `journalctl -u solar-monitoring -f` (systemd) or console output
   - Frontend: Browser console
   - Mobile: Expo logs in terminal

2. Verify configurations:
   - `config.yaml` syntax
   - API endpoints
   - Network connectivity

3. Test components individually:
   - Backend API with curl
   - Frontend with browser dev tools
   - Mobile with Expo Go

---

## Quick Migration Checklist

### Pre-Migration
- [ ] Backup all files from old machine
- [ ] Export database (if applicable)
- [ ] Document current configuration
- [ ] Note API keys and credentials

### New Machine Setup
- [ ] Install Python 3.11+
- [ ] Install Node.js 20+
- [ ] Install Git
- [ ] Install system dependencies (libmodbus-dev, etc.)
- [ ] Set up serial port permissions (if needed)

### Backend
- [ ] Clone/transfer project files
- [ ] Create Python virtual environment
- [ ] Install Python dependencies
- [ ] Copy and configure `config.yaml`
- [ ] Transfer database file
- [ ] Test backend startup
- [ ] Verify API endpoints

### Frontend
- [ ] Navigate to `webapp-react` directory
- [ ] Install npm dependencies
- [ ] Update API endpoint in `src/config.ts`
- [ ] Build frontend
- [ ] Test frontend

### Mobile
- [ ] Navigate to `mobile` directory
- [ ] Install npm dependencies
- [ ] Update API endpoint in `src/config.ts`
- [ ] Test with Expo Go app

### Post-Migration
- [ ] Run all verification tests
- [ ] Set up production deployment (systemd/Docker)
- [ ] Configure firewall rules
- [ ] Set up monitoring/logging
- [ ] Document new machine setup

---

## Additional Resources

- **Backend Documentation**: See `DEPLOYMENT_GUIDE.md`
- **Docker Deployment**: See `DOCKER_DEPLOYMENT.md`
- **Mobile App**: See `mobile/README.md`
- **API Documentation**: Check backend API endpoints

---

## Support

If you encounter issues during migration:
1. Check the troubleshooting section
2. Review logs for error messages
3. Verify all configuration files
4. Test each component individually
5. Check network connectivity between components

Good luck with your migration! 🚀

