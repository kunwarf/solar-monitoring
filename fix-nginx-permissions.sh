#!/bin/bash

# Fix Nginx permissions for Solar Monitoring frontend
# This script fixes file permissions so nginx can read the frontend files

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Fixing Nginx Permissions${NC}"
echo ""

# Get project directory
PROJECT_DIR=$(pwd)
FRONTEND_DIR="$PROJECT_DIR/webapp-react"
DIST_DIR="$FRONTEND_DIR/dist"

echo "Project directory: $PROJECT_DIR"
echo "Frontend directory: $FRONTEND_DIR"
echo "Dist directory: $DIST_DIR"
echo ""

# Check if dist directory exists
if [ ! -d "$DIST_DIR" ]; then
    echo -e "${RED}✗ Dist directory not found: $DIST_DIR${NC}"
    echo "Please build the frontend first:"
    echo "  cd webapp-react && npm run build"
    exit 1
fi

# Detect nginx user
if id "www-data" &>/dev/null; then
    NGINX_USER="www-data"
    NGINX_GROUP="www-data"
elif id "nginx" &>/dev/null; then
    NGINX_USER="nginx"
    NGINX_GROUP="nginx"
else
    echo -e "${YELLOW}⚠ Could not detect nginx user. Using www-data as default.${NC}"
    NGINX_USER="www-data"
    NGINX_GROUP="www-data"
fi

echo "Detected nginx user: $NGINX_USER"
echo ""

# Get current user
CURRENT_USER=$(whoami)
echo "Current user: $CURRENT_USER"
echo ""

# Option 1: Make files readable by nginx (Recommended)
echo "Option 1: Making files readable by nginx..."
echo "Setting permissions on dist directory..."

# Make dist directory and files readable by others
sudo chmod -R 755 "$DIST_DIR"
# Make files readable
sudo find "$DIST_DIR" -type f -exec chmod 644 {} \;
# Make directories executable
sudo find "$DIST_DIR" -type d -exec chmod 755 {} \;

echo -e "${GREEN}✓ Permissions set${NC}"
echo ""

# Option 2: Add nginx user to your group (Alternative)
echo "Option 2: Adding nginx user to your group..."
CURRENT_GROUP=$(id -gn)
echo "Your group: $CURRENT_GROUP"

# Add nginx user to your group
if sudo usermod -a -G "$CURRENT_GROUP" "$NGINX_USER" 2>/dev/null; then
    echo -e "${GREEN}✓ Added $NGINX_USER to group $CURRENT_GROUP${NC}"
    echo "  Note: You may need to restart nginx for this to take effect"
else
    echo -e "${YELLOW}⚠ Could not add nginx user to group (may already be added)${NC}"
fi
echo ""

# Option 3: Set ownership (if needed)
read -p "Set ownership of dist directory to nginx user? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo chown -R "$NGINX_USER:$NGINX_GROUP" "$DIST_DIR"
    echo -e "${GREEN}✓ Ownership set to $NGINX_USER:$NGINX_GROUP${NC}"
else
    echo "Keeping current ownership"
fi
echo ""

# Verify permissions
echo "Verifying permissions..."
if [ -r "$DIST_DIR/index.html" ]; then
    echo -e "${GREEN}✓ index.html is readable${NC}"
    ls -la "$DIST_DIR/index.html"
else
    echo -e "${RED}✗ index.html is NOT readable${NC}"
fi
echo ""

# Restart nginx
echo "Restarting nginx..."
sudo systemctl restart nginx
echo -e "${GREEN}✓ Nginx restarted${NC}"
echo ""

# Test
echo "Testing access..."
sleep 1
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8090 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Frontend is now accessible!${NC}"
else
    echo -e "${YELLOW}⚠ Still having issues. Check:${NC}"
    echo "  1. sudo tail -f /var/log/nginx/error.log"
    echo "  2. ls -la $DIST_DIR"
    echo "  3. sudo -u $NGINX_USER test -r $DIST_DIR/index.html && echo 'Readable' || echo 'Not readable'"
fi
echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Permissions fixed. If issues persist:"
echo ""
echo "1. Check if nginx can read the file:"
echo "   sudo -u $NGINX_USER test -r $DIST_DIR/index.html && echo 'OK' || echo 'FAILED'"
echo ""
echo "2. Check directory permissions:"
echo "   ls -la $DIST_DIR"
echo ""
echo "3. Alternative: Move dist to /var/www:"
echo "   sudo mkdir -p /var/www/solar-monitoring"
echo "   sudo cp -r $DIST_DIR/* /var/www/solar-monitoring/"
echo "   sudo chown -R $NGINX_USER:$NGINX_GROUP /var/www/solar-monitoring"
echo "   # Then update nginx config to point to /var/www/solar-monitoring"
echo ""

