#!/bin/bash

# API Connection Debug Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header "API Connection Debug"

# Check if backend is running
echo "1. Checking if backend service is running..."
if systemctl is-active --quiet solar-monitoring 2>/dev/null; then
    print_success "Solar monitoring service is running"
elif docker-compose ps | grep -q "solar-backend.*Up" 2>/dev/null; then
    print_success "Docker solar-backend is running"
else
    print_error "Backend service is not running"
    echo "Start with: sudo systemctl start solar-monitoring"
    echo "Or Docker: docker-compose up -d"
fi

# Check if port 8000 is listening
echo
echo "2. Checking if port 8000 is listening..."
if netstat -tlnp 2>/dev/null | grep -q ":8000 "; then
    print_success "Port 8000 is listening"
    netstat -tlnp | grep ":8000 "
else
    print_error "Port 8000 is not listening"
fi

# Test API endpoint directly
echo
echo "3. Testing API endpoint directly..."
if curl -s http://localhost:8000/api/now >/dev/null 2>&1; then
    print_success "API endpoint is responding"
    echo "API Response:"
    curl -s http://localhost:8000/api/now | head -5
else
    print_error "API endpoint is not responding"
    echo "Trying with verbose output:"
    curl -v http://localhost:8000/api/now 2>&1 | head -10
fi

# Check nginx configuration
echo
echo "4. Checking nginx configuration..."
if [ -f "/etc/nginx/sites-available/solar-monitoring" ]; then
    print_success "Nginx config exists"
    echo "Nginx config location block:"
    grep -A 10 "location /api/" /etc/nginx/sites-available/solar-monitoring
else
    print_warning "Nginx config not found at /etc/nginx/sites-available/solar-monitoring"
fi

# Check if nginx is running
echo
echo "5. Checking nginx status..."
if systemctl is-active --quiet nginx 2>/dev/null; then
    print_success "Nginx is running"
else
    print_error "Nginx is not running"
fi

# Test nginx proxy
echo
echo "6. Testing nginx proxy..."
if curl -s http://localhost/api/now >/dev/null 2>&1; then
    print_success "Nginx proxy is working"
else
    print_error "Nginx proxy is not working"
    echo "Trying with verbose output:"
    curl -v http://localhost/api/now 2>&1 | head -10
fi

# Check React app configuration
echo
echo "7. Checking React app configuration..."
if [ -f "webapp-react/src/config.ts" ]; then
    print_success "React config found"
    echo "API Base URL:"
    cat webapp-react/src/config.ts
else
    print_warning "React config not found"
fi

# Check backend logs
echo
echo "8. Checking backend logs..."
if systemctl is-active --quiet solar-monitoring 2>/dev/null; then
    print_warning "Recent backend logs:"
    sudo journalctl -u solar-monitoring --no-pager -n 20
elif docker-compose ps | grep -q "solar-backend.*Up" 2>/dev/null; then
    print_warning "Recent Docker backend logs:"
    docker-compose logs --tail=20 solar-backend
fi

# Check nginx logs
echo
echo "9. Checking nginx logs..."
if [ -f "/var/log/nginx/error.log" ]; then
    print_warning "Recent nginx error logs:"
    sudo tail -10 /var/log/nginx/error.log
fi

if [ -f "/var/log/nginx/access.log" ]; then
    print_warning "Recent nginx access logs:"
    sudo tail -5 /var/log/nginx/access.log
fi

print_header "Common Solutions"

echo "1. If backend is not running:"
echo "   sudo systemctl start solar-monitoring"
echo "   # or"
echo "   docker-compose up -d"

echo
echo "2. If port 8000 is not listening:"
echo "   Check config.yaml has web.enabled: true"
echo "   Check config.yaml has web.port: 8000"

echo
echo "3. If nginx proxy is not working:"
echo "   sudo nginx -t"
echo "   sudo systemctl restart nginx"

echo
echo "4. If React can't connect:"
echo "   Check webapp-react/src/config.ts API_BASE_URL"
echo "   Make sure it matches your server setup"

echo
echo "5. Check firewall:"
echo "   sudo ufw status"
echo "   sudo ufw allow 8000"
echo "   sudo ufw allow 80"
