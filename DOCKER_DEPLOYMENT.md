# Docker Deployment Guide

This guide covers deploying the Solar Monitoring System using Docker and Docker Compose for easy containerized deployment.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Git

## 1. Quick Start

### 1.1 Clone Repository

```bash
git clone <your-repo-url> solar-monitoring
cd solar-monitoring
```

### 1.2 Configure Environment

```bash
# Copy and edit configuration
cp config.example.yaml config.yaml
nano config.yaml
```

### 1.3 Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

## 2. Configuration

### 2.1 Backend Configuration

Edit `config.yaml`:

```yaml
mqtt:
  host: "mosquitto"  # Docker service name
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
    provider: "openweather"
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

### 2.2 Environment Variables

Create `.env` file:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password

# MQTT
MQTT_USERNAME=your_mqtt_user
MQTT_PASSWORD=your_mqtt_password

# Weather API
OPENWEATHER_API_KEY=your_api_key

# Timezone
TZ=Asia/Karachi
```

## 3. Service Management

### 3.1 Basic Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f [service_name]

# Scale services (if needed)
docker-compose up -d --scale solar-backend=2
```

### 3.2 Individual Service Management

```bash
# Start only backend
docker-compose up -d solar-backend

# Start only frontend
docker-compose up -d solar-frontend

# Rebuild and restart specific service
docker-compose up -d --build solar-backend
```

## 4. Data Persistence

### 4.1 Volumes

The following data is persisted:

- **Database**: `postgres-data` volume
- **Redis Cache**: `redis-data` volume
- **MQTT Data**: `./mosquitto-data` directory
- **Application Database**: `./solarhub.db` file
- **Configuration**: `./config.yaml` file

### 4.2 Backup

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"

mkdir -p $BACKUP_DIR

# Backup volumes
docker run --rm -v solar-monitoring_postgres-data:/data -v $(pwd)/$BACKUP_DIR:/backup alpine tar czf /backup/postgres_$DATE.tar.gz -C /data .
docker run --rm -v solar-monitoring_redis-data:/data -v $(pwd)/$BACKUP_DIR:/backup alpine tar czf /backup/redis_$DATE.tar.gz -C /data .

# Backup application files
tar czf $BACKUP_DIR/app_$DATE.tar.gz config.yaml solarhub.db

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x backup.sh
```

## 5. Monitoring and Health Checks

### 5.1 Health Checks

All services include health checks:

```bash
# Check service health
docker-compose ps

# View health check logs
docker inspect solar-monitoring-backend | grep -A 10 Health
```

### 5.2 Monitoring Script

```bash
# Create monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash

echo "=== Solar Monitoring System Status ==="
echo

# Check Docker services
echo "Docker Services:"
docker-compose ps
echo

# Check API health
echo "API Health:"
curl -s http://localhost/api/now | jq . || echo "API not responding"
echo

# Check web app
echo "Web App:"
curl -s -o /dev/null -w "%{http_code}" http://localhost/ && echo " - OK" || echo " - FAILED"
echo

# Check MQTT
echo "MQTT Broker:"
docker-compose exec mosquitto mosquitto_pub -h localhost -t test -m "test" && echo " - OK" || echo " - FAILED"
echo

echo "=== System Resources ==="
docker stats --no-stream
EOF

chmod +x monitor.sh
```

## 6. SSL/HTTPS Setup

### 6.1 Generate SSL Certificates

```bash
# Create SSL directory
mkdir -p ssl

# Generate self-signed certificate (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# For production, use Let's Encrypt or your CA
```

### 6.2 Update Nginx Configuration

Uncomment the HTTPS server block in `nginx.conf` and update the SSL certificate paths.

## 7. Production Deployment

### 7.1 Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  solar-backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    restart: unless-stopped
    environment:
      - NODE_ENV=production
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./solarhub.db:/app/solarhub.db
    networks:
      - solar-network

  solar-frontend:
    build:
      context: ./webapp-react
      dockerfile: Dockerfile
    restart: unless-stopped
    networks:
      - solar-network

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - solar-backend
      - solar-frontend
    networks:
      - solar-network

networks:
  solar-network:
    driver: bridge
```

### 7.2 Deploy to Production

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Or override specific services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 8. Updates and Maintenance

### 8.1 Update Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose up -d --build

# Or update specific service
docker-compose up -d --build solar-backend
```

### 8.2 Cleanup

```bash
# Remove unused images
docker image prune -f

# Remove unused volumes (be careful!)
docker volume prune -f

# Remove unused networks
docker network prune -f
```

## 9. Troubleshooting

### 9.1 Common Issues

1. **Port conflicts**: Check if ports 80, 443, 8000, 1883 are available
2. **Permission issues**: Ensure Docker has access to serial devices
3. **Network issues**: Check if containers can communicate
4. **Volume issues**: Verify volume mounts and permissions

### 9.2 Debug Commands

```bash
# View detailed logs
docker-compose logs --tail=100 -f

# Execute commands in container
docker-compose exec solar-backend bash
docker-compose exec solar-frontend sh

# Check container resources
docker stats

# Inspect container configuration
docker inspect solar-monitoring-backend
```

### 9.3 Reset Everything

```bash
# Stop and remove all containers, networks, and volumes
docker-compose down -v

# Remove all images
docker-compose down --rmi all

# Start fresh
docker-compose up -d --build
```

## 10. Access Points

After deployment, access your application at:

- **Web Application**: `http://localhost` or `https://localhost`
- **API**: `http://localhost/api/now`
- **MQTT Broker**: `localhost:1883`
- **MQTT WebSocket**: `ws://localhost:9001`

## 11. Security Considerations

1. **Change default passwords** in `.env` file
2. **Use SSL certificates** for production
3. **Limit network access** with firewall rules
4. **Regular updates** of Docker images
5. **Monitor logs** for suspicious activity
6. **Backup data** regularly

This Docker deployment provides a robust, scalable, and maintainable solution for your solar monitoring system.
