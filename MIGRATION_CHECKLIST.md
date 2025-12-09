# Solar Monitoring System - Migration Checklist

Use this checklist to track your migration progress. Print or save this file and check off items as you complete them.

## Pre-Migration (Old Machine)

### Backup & Documentation
- [ ] Backup entire project directory
- [ ] Export database (SQLite: copy `solarhub.db`, PostgreSQL: use `pg_dump`)
- [ ] Document all API keys and credentials
- [ ] Note current configuration settings
- [ ] List all installed packages/versions
- [ ] Document network settings (IPs, ports)
- [ ] Backup configuration files (`config.yaml`, `mosquitto.conf`, etc.)
- [ ] Note serial port device paths (if using Modbus RTU)

### Files to Transfer
- [ ] `config.yaml` (contains all settings)
- [ ] `solarhub.db` (database file)
- [ ] `register_maps/*.json` (register mapping files)
- [ ] `mosquitto.conf` (if using standalone MQTT)
- [ ] `.env` (if using Docker)
- [ ] Any custom scripts or modifications

---

## New Machine Setup

### System Prerequisites
- [ ] Operating system installed (Ubuntu 20.04+ / Debian 11+ / Windows 10+ / macOS 10.15+)
- [ ] System updated (`sudo apt update && sudo apt upgrade`)
- [ ] Git installed and configured
- [ ] Python 3.11+ installed
- [ ] Node.js 20+ installed
- [ ] npm installed (comes with Node.js)
- [ ] System dependencies installed (libmodbus-dev, build-essential, etc.)
- [ ] User added to dialout group (for serial port access)
- [ ] Logged out and back in (for group changes)

### Optional Tools
- [ ] Docker installed (if using containerized deployment)
- [ ] Docker Compose installed
- [ ] Nginx installed (for production frontend)
- [ ] MQTT broker installed (if not using Docker)
- [ ] Expo CLI installed (for mobile development)
- [ ] Android Studio installed (for Android development)
- [ ] Xcode installed (for iOS development on macOS)

---

## Backend Migration

### Project Setup
- [ ] Project files transferred/cloned to new machine
- [ ] Navigated to project directory
- [ ] Python virtual environment created (`python3.11 -m venv venv`)
- [ ] Virtual environment activated
- [ ] pip upgraded (`pip install --upgrade pip`)
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] All dependencies installed without errors

### Configuration
- [ ] `config.yaml` copied from old machine
- [ ] `config.yaml` reviewed and updated for new machine
- [ ] MQTT settings configured
- [ ] Inverter settings configured (serial ports/IPs)
- [ ] API keys added (OpenWeather, etc.)
- [ ] Timezone settings configured
- [ ] Smart scheduler parameters configured

### Database
- [ ] Database file (`solarhub.db`) transferred
- [ ] Database file permissions set correctly
- [ ] Database migrations run (if needed)
- [ ] Database accessible and readable

### Testing
- [ ] Backend imports successfully (`python -c "import solarhub"`)
- [ ] Backend starts without errors
- [ ] API endpoint responds (`curl http://localhost:8000/api/now`)
- [ ] Inverter list endpoint works (`curl http://localhost:8000/api/inverters`)
- [ ] Serial port accessible (if using Modbus RTU)

---

## Frontend Migration

### Project Setup
- [ ] Navigated to `webapp-react` directory
- [ ] Node.js version correct (20+)
- [ ] npm dependencies installed (`npm install`)
- [ ] No installation errors

### Configuration
- [ ] API endpoint updated in `src/config.ts`
- [ ] API endpoint points to correct backend URL
- [ ] Configuration tested

### Building
- [ ] Frontend builds successfully (`npm run build`)
- [ ] Build output in `dist` directory
- [ ] No build errors or warnings

### Testing
- [ ] Development server starts (`npm run dev`)
- [ ] Frontend accessible in browser
- [ ] Frontend connects to backend API
- [ ] Data displays correctly
- [ ] No console errors

---

## Mobile Migration

### Project Setup
- [ ] Navigated to `mobile` directory
- [ ] Node.js version correct (20+)
- [ ] npm dependencies installed (`npm install`)
- [ ] Expo CLI available (global or via npx)
- [ ] No installation errors

### Configuration
- [ ] API endpoint updated in `src/config.ts`
- [ ] API endpoint points to correct backend URL
- [ ] Network configuration verified (LAN/tunnel mode)

### Testing
- [ ] Expo development server starts (`npm start`)
- [ ] QR code generated successfully
- [ ] Expo Go app installed on mobile device
- [ ] App connects to backend
- [ ] Data loads correctly in app
- [ ] All screens functional
- [ ] No connection errors

---

## Integration Testing

### Full Stack Verification
- [ ] Backend running and accessible
- [ ] Frontend connects to backend
- [ ] Mobile app connects to backend
- [ ] All three modules show consistent data
- [ ] Real-time updates working
- [ ] Historical data accessible
- [ ] No network connectivity issues

### Functionality Testing
- [ ] Telemetry data displays correctly
- [ ] Battery status accurate
- [ ] Inverter information correct
- [ ] Energy statistics accurate
- [ ] Charts/graphs render properly
- [ ] Navigation works (mobile)
- [ ] Settings/config accessible

---

## Production Deployment (Optional)

### Backend Service
- [ ] Systemd service file created/configured
- [ ] Service enabled (`sudo systemctl enable solar-monitoring`)
- [ ] Service started (`sudo systemctl start solar-monitoring`)
- [ ] Service status verified (`sudo systemctl status solar-monitoring`)
- [ ] Logs accessible (`journalctl -u solar-monitoring`)

### Frontend Deployment
- [ ] Frontend built for production
- [ ] Nginx configured (if using)
- [ ] Nginx configuration tested
- [ ] Nginx service restarted
- [ ] Frontend accessible via web browser

### Docker Deployment (Alternative)
- [ ] Docker Compose file configured
- [ ] All services start successfully
- [ ] Containers healthy
- [ ] Volumes mounted correctly
- [ ] Network connectivity verified

---

## Post-Migration

### Security
- [ ] Firewall rules configured
- [ ] Default passwords changed
- [ ] API keys secured
- [ ] File permissions set correctly
- [ ] Unnecessary services disabled

### Monitoring
- [ ] Logging configured
- [ ] Monitoring tools set up (optional)
- [ ] Health check scripts working
- [ ] Backup scripts configured

### Documentation
- [ ] New machine setup documented
- [ ] Configuration changes noted
- [ ] Network settings documented
- [ ] Access credentials secured
- [ ] Migration notes saved

### Cleanup
- [ ] Old machine data backed up
- [ ] Temporary files removed
- [ ] Test data cleaned up (if needed)
- [ ] Old machine decommissioned (if applicable)

---

## Troubleshooting Notes

Use this section to note any issues encountered and their solutions:

### Issue 1:
- **Problem:**
- **Solution:**
- **Date:**

### Issue 2:
- **Problem:**
- **Solution:**
- **Date:**

---

## Migration Completion

- [ ] All critical items checked
- [ ] All modules functional
- [ ] Integration tests passed
- [ ] Production deployment successful (if applicable)
- [ ] Documentation updated
- [ ] Team notified (if applicable)
- [ ] Old machine backed up and secured

**Migration Date:** _______________

**Completed By:** _______________

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

## Quick Reference

### Important Commands

**Backend:**
```bash
source venv/bin/activate
python -m solarhub.main
```

**Frontend:**
```bash
cd webapp-react
npm run dev
```

**Mobile:**
```bash
cd mobile
npm start
```

**Check Services:**
```bash
# Backend API
curl http://localhost:8000/api/now

# Service status (systemd)
sudo systemctl status solar-monitoring

# Docker
docker-compose ps
```

### Important Files
- `config.yaml` - Main configuration
- `solarhub.db` - Database
- `src/config.ts` - Frontend/Mobile API endpoint
- `requirements.txt` - Python dependencies
- `package.json` - Node.js dependencies (frontend & mobile)

### Support Resources
- `MIGRATION_GUIDE.md` - Detailed migration guide
- `DEPLOYMENT_GUIDE.md` - Deployment instructions
- `DOCKER_DEPLOYMENT.md` - Docker setup guide
- `mobile/README.md` - Mobile app documentation

