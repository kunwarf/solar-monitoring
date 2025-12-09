#!/bin/bash

# Setup Nginx for Solar Monitoring Frontend
# This script installs nginx, builds the frontend, and configures nginx

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Setting up Nginx for Solar Monitoring${NC}"
echo ""

# Get current directory (should be project root)
PROJECT_DIR=$(pwd)
FRONTEND_DIR="$PROJECT_DIR/webapp-react"
NGINX_PORT="8090"
BACKEND_PORT="8000"

echo "Project directory: $PROJECT_DIR"
echo "Frontend directory: $FRONTEND_DIR"
echo "Nginx port: $NGINX_PORT"
echo "Backend port: $BACKEND_PORT"
echo ""

# 1. Check if nginx is installed
echo "1. Checking if nginx is installed..."
if command -v nginx &> /dev/null; then
    echo -e "${GREEN}✓ Nginx is installed${NC}"
    nginx -v
else
    echo -e "${YELLOW}Nginx not found. Installing...${NC}"
    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y nginx
    elif command -v yum &> /dev/null; then
        sudo yum install -y nginx
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y nginx
    else
        echo -e "${RED}✗ Cannot install nginx automatically. Please install it manually.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Nginx installed${NC}"
fi
echo ""

# 2. Check if Node.js is installed (needed to build frontend)
echo "2. Checking if Node.js is installed..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js is installed: $NODE_VERSION${NC}"
    
    # Check if version is 20+
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_MAJOR" -lt 20 ]; then
        echo -e "${YELLOW}⚠ Warning: Node.js 20+ recommended. Found: $NODE_VERSION${NC}"
    fi
else
    echo -e "${RED}✗ Node.js not found. Please install Node.js 20+ first.${NC}"
    echo "  Install with: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs"
    exit 1
fi
echo ""

# 3. Build the frontend
echo "3. Building frontend..."
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}✗ Frontend directory not found: $FRONTEND_DIR${NC}"
    exit 1
fi

cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Build the frontend
echo "Building frontend (this may take a minute)..."
npm run build

if [ ! -d "dist" ]; then
    echo -e "${RED}✗ Build failed - dist directory not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Frontend built successfully${NC}"
cd "$PROJECT_DIR"
echo ""

# 4. Create nginx configuration
echo "4. Creating nginx configuration..."
NGINX_SITE="/etc/nginx/sites-available/solar-monitoring"
NGINX_ENABLED="/etc/nginx/sites-enabled/solar-monitoring"

# Create the nginx site configuration
sudo tee "$NGINX_SITE" > /dev/null <<EOF
server {
    listen $NGINX_PORT;
    server_name _;

    # Serve React app
    location / {
        root $FRONTEND_DIR/dist;
        index index.html;
        try_files \$uri \$uri/ /index.html;
        
        # Enable gzip compression
        gzip on;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # CORS headers
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization";
        
        # Handle preflight requests
        if (\$request_method = 'OPTIONS') {
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
EOF

echo -e "${GREEN}✓ Nginx configuration created${NC}"
echo ""

# 5. Enable the site
echo "5. Enabling nginx site..."
if [ -L "$NGINX_ENABLED" ]; then
    echo "Site already enabled, removing old link..."
    sudo rm "$NGINX_ENABLED"
fi

sudo ln -s "$NGINX_SITE" "$NGINX_ENABLED"
echo -e "${GREEN}✓ Site enabled${NC}"
echo ""

# 6. Remove default site (optional)
read -p "Remove default nginx site? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -L "/etc/nginx/sites-enabled/default" ]; then
        sudo rm /etc/nginx/sites-enabled/default
        echo -e "${GREEN}✓ Default site removed${NC}"
    fi
fi
echo ""

# 7. Test nginx configuration
echo "6. Testing nginx configuration..."
if sudo nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration has errors${NC}"
    exit 1
fi
echo ""

# 8. Start/restart nginx
echo "7. Starting nginx..."
if sudo systemctl is-active --quiet nginx; then
    echo "Nginx is running, reloading configuration..."
    sudo systemctl reload nginx
else
    echo "Starting nginx..."
    sudo systemctl start nginx
fi

sudo systemctl enable nginx
echo -e "${GREEN}✓ Nginx started and enabled${NC}"
echo ""

# 9. Check status
echo "8. Checking nginx status..."
sudo systemctl status nginx --no-pager | head -10
echo ""

# 10. Test connection
echo "9. Testing connection..."
sleep 2
if curl -s -o /dev/null -w "%{http_code}" http://localhost:$NGINX_PORT | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Frontend is accessible at http://localhost:$NGINX_PORT${NC}"
else
    echo -e "${YELLOW}⚠ Frontend may not be accessible yet. Check logs:${NC}"
    echo "  sudo tail -f /var/log/nginx/error.log"
fi
echo ""

# 11. Check firewall
echo "10. Checking firewall..."
if command -v ufw &> /dev/null && sudo ufw status &>/dev/null; then
    if sudo ufw status | grep -q "$NGINX_PORT"; then
        echo -e "${GREEN}✓ Firewall rule exists for port $NGINX_PORT${NC}"
    else
        echo -e "${YELLOW}⚠ No firewall rule for port $NGINX_PORT${NC}"
        read -p "Allow port $NGINX_PORT in firewall? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo ufw allow $NGINX_PORT/tcp
            echo -e "${GREEN}✓ Firewall rule added${NC}"
        fi
    fi
fi
echo ""

echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Frontend should now be accessible at:"
echo "  Local:  http://localhost:$NGINX_PORT"
echo "  Remote: http://182.180.150.107:$NGINX_PORT"
echo ""
echo "If you can't access it remotely:"
echo "  1. Check firewall: sudo ufw allow $NGINX_PORT/tcp"
echo "  2. Check nginx logs: sudo tail -f /var/log/nginx/error.log"
echo "  3. Check if backend is running: curl http://localhost:$BACKEND_PORT/api/now"
echo "  4. Verify nginx is listening: sudo ss -tlnp | grep :$NGINX_PORT"
echo ""

