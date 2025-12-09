# Solar Monitoring System Deployment Guide

This guide covers deploying both the React web application and the Python solar monitoring backend on a Linux server.

## Prerequisites

- Ubuntu 20.04+ or CentOS 8+ server
- Python 3.8+
- Node.js 16+
- Nginx
- Systemd
- Git

## 1. Backend Deployment (Python Application)

### 1.1 Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install system dependencies
sudo apt install git nginx supervisor -y

# Install Modbus dependencies (if using RTU)
sudo apt install libmodbus-dev -y
```

### 1.2 Clone and Setup Application

```bash
# Clone repository
git clone <your-repo-url> /opt/solar-monitoring
cd /opt/solar-monitoring

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Copy and configure config file
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
nano config.yaml
```

### 1.3 Configure Application

Edit `config.yaml` with your settings:

```yaml
mqtt:
  host: "localhost"
  port: 1883
  username: "your_mqtt_user"
  password: "your_mqtt_pass"
  base_topic: "solar/fleet"

inverters:
  - id: "senergy1"
    name: "Main Inverter"
    adapter:
      type: "senergy"
      unit_id: 1
      transport: "rtu"  # or "tcp"
      serial_port: "/dev/ttyUSB0"  # or IP address for TCP
      baudrate: 9600

smart:
  policy:
    enabled: true
    max_battery_soc_pct: 98
    solar_charge_deadline_hours_before_sunset: 2
    target_full_before_sunset: true
    overnight_min_soc_pct: 20
    blackout_reserve_soc_pct: 20
    max_grid_charge_power_w: 2000
    max_discharge_power_w: 5000
  
  forecast:
    provider: "openweather"  # or "weatherapi"
    api_key: "your_api_key"
    lat: 31.5497
    lon: 74.3436
    tz: "Asia/Karachi"

# Enable web API
web:
  enabled: true
  host: "0.0.0.0"
  port: 8000
```

### 1.4 Create Systemd Service

Create `/etc/systemd/system/solar-monitoring.service`:

```ini
[Unit]
Description=Solar Monitoring System
After=network.target
Wants=network.target

[Service]
Type=simple
User=solar
Group=solar
WorkingDirectory=/opt/solar-monitoring
Environment=PATH=/opt/solar-monitoring/venv/bin
ExecStart=/opt/solar-monitoring/venv/bin/python -m solarhub.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/solar-monitoring

[Install]
WantedBy=multi-user.target
```

### 1.5 Create User and Set Permissions

```bash
# Create solar user
sudo useradd -r -s /bin/false solar

# Set ownership
sudo chown -R solar:solar /opt/solar-monitoring

# Set permissions for serial port (if using RTU)
sudo usermod -a -G dialout solar

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable solar-monitoring
sudo systemctl start solar-monitoring

# Check status
sudo systemctl status solar-monitoring
```

## 2. Frontend Deployment (React Web App)

### 2.1 Install Node.js

```bash
# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version
npm --version
```

### 2.2 Build React Application

```bash
# Navigate to React app directory
cd /opt/solar-monitoring/webapp-react

# Install dependencies
npm install

# Build for production
npm run build

# The build output will be in the 'dist' directory
```

### 2.3 Configure Nginx

Create `/etc/nginx/sites-available/solar-monitoring`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or IP

    # Serve React app
    location / {
        root /opt/solar-monitoring/webapp-react/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
        
        # Enable gzip compression
        gzip on;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization";
        
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin *;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization";
            add_header Access-Control-Max-Age 1728000;
            add_header Content-Type 'text/plain; charset=utf-8';
            add_header Content-Length 0;
            return 204;
        }
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
}
```

### 2.4 Enable Nginx Site

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/solar-monitoring /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## 3. SSL/HTTPS Setup (Optional but Recommended)

### 3.1 Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 3.2 Obtain SSL Certificate

```bash
# Replace with your domain
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add this line:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## 4. MQTT Broker Setup (Optional)

If you need MQTT for external integrations:

```bash
# Install Mosquitto MQTT broker
sudo apt install mosquitto mosquitto-clients -y

# Configure authentication
sudo mosquitto_passwd -c /etc/mosquitto/passwd your_mqtt_user

# Edit configuration
sudo nano /etc/mosquitto/mosquitto.conf
```

Add to mosquitto.conf:
```
allow_anonymous false
password_file /etc/mosquitto/passwd
listener 1883
```

```bash
# Restart MQTT broker
sudo systemctl restart mosquitto
sudo systemctl enable mosquitto
```

## 5. Monitoring and Logs

### 5.1 View Application Logs

```bash
# View systemd logs
sudo journalctl -u solar-monitoring -f

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 5.2 Health Check Script

Create `/opt/solar-monitoring/health_check.sh`:

```bash
#!/bin/bash

# Check if service is running
if systemctl is-active --quiet solar-monitoring; then
    echo "✅ Solar monitoring service is running"
else
    echo "❌ Solar monitoring service is not running"
    exit 1
fi

# Check if API is responding
if curl -s http://localhost:8000/api/now > /dev/null; then
    echo "✅ API is responding"
else
    echo "❌ API is not responding"
    exit 1
fi

# Check if web app is accessible
if curl -s http://localhost/ > /dev/null; then
    echo "✅ Web application is accessible"
else
    echo "❌ Web application is not accessible"
    exit 1
fi

echo "🎉 All systems operational!"
```

Make it executable:
```bash
chmod +x /opt/solar-monitoring/health_check.sh
```

## 6. Backup and Updates

### 6.1 Backup Script

Create `/opt/solar-monitoring/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/opt/backups/solar-monitoring"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup application files
tar -czf $BACKUP_DIR/solar-monitoring_$DATE.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    /opt/solar-monitoring

# Backup database
cp /opt/solar-monitoring/solarhub.db $BACKUP_DIR/solarhub_$DATE.db

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.db" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/solar-monitoring_$DATE.tar.gz"
```

### 6.2 Update Script

Create `/opt/solar-monitoring/update.sh`:

```bash
#!/bin/bash

cd /opt/solar-monitoring

# Stop service
sudo systemctl stop solar-monitoring

# Backup current version
./backup.sh

# Pull latest changes
git pull origin main

# Update Python dependencies
source venv/bin/activate
pip install -r requirements.txt

# Rebuild React app
cd webapp-react
npm install
npm run build
cd ..

# Set permissions
sudo chown -R solar:solar /opt/solar-monitoring

# Start service
sudo systemctl start solar-monitoring

echo "Update completed!"
```

## 7. Firewall Configuration

```bash
# Install UFW
sudo apt install ufw -y

# Allow SSH, HTTP, HTTPS
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

## 8. Access Your Application

- **Web Application**: `http://your-server-ip` or `https://your-domain.com`
- **API**: `http://your-server-ip/api/now` or `https://your-domain.com/api/now`
- **Health Check**: Run `/opt/solar-monitoring/health_check.sh`

## 9. Troubleshooting

### Common Issues:

1. **Service won't start**: Check logs with `sudo journalctl -u solar-monitoring -f`
2. **API not responding**: Verify port 8000 is not blocked and service is running
3. **Web app not loading**: Check nginx configuration and build output
4. **Serial port issues**: Ensure user is in dialout group and device exists
5. **Permission errors**: Check file ownership with `ls -la /opt/solar-monitoring`

### Useful Commands:

```bash
# Restart services
sudo systemctl restart solar-monitoring
sudo systemctl restart nginx

# Check service status
sudo systemctl status solar-monitoring
sudo systemctl status nginx

# View real-time logs
sudo journalctl -u solar-monitoring -f

# Test configuration
sudo nginx -t

# Check ports
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :80
```

This deployment guide provides a production-ready setup for your solar monitoring system with proper security, monitoring, and maintenance procedures.
