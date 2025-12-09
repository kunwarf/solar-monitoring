#!/bin/bash

# Port diagnostic script

echo "🔍 Port 80 and 443 Diagnostic Report"
echo "======================================"

echo
echo "📊 What's using port 80:"
echo "------------------------"
if sudo lsof -i :80 2>/dev/null; then
    echo "Port 80 is in use"
else
    echo "Port 80 is free"
fi

echo
echo "📊 What's using port 443:"
echo "-------------------------"
if sudo lsof -i :443 2>/dev/null; then
    echo "Port 443 is in use"
else
    echo "Port 443 is free"
fi

echo
echo "🌐 Active web server services:"
echo "------------------------------"
services=("apache2" "nginx" "lighttpd" "httpd" "tomcat" "caddy")

for service in "${services[@]}"; do
    if systemctl is-active --quiet $service 2>/dev/null; then
        echo "✅ $service is running"
    elif systemctl is-enabled --quiet $service 2>/dev/null; then
        echo "⏸️  $service is enabled but not running"
    else
        echo "❌ $service is not active"
    fi
done

echo
echo "🔧 Quick fixes:"
echo "---------------"
echo "1. Stop Apache: sudo systemctl stop apache2"
echo "2. Stop other nginx: sudo systemctl stop nginx"
echo "3. Kill port 80 processes: sudo fuser -k 80/tcp"
echo "4. Use different port: Edit nginx config to use port 8080"
echo "5. Use Docker: docker-compose up -d (uses different ports)"

echo
echo "🚀 Recommended solution:"
echo "-----------------------"
echo "Run: chmod +x fix-port-conflict.sh && ./fix-port-conflict.sh"
