#!/bin/bash

# Script to check if something is running on port 8090
# Usage: ./check-port-8090.sh

set -e

IP="182.180.150.107"
PORT="8090"

echo "=========================================="
echo "Checking service on $IP:$PORT"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Check if port is listening locally
echo "1. Checking if port $PORT is listening locally..."
if command -v ss &> /dev/null; then
    LISTENING=$(ss -tlnp | grep ":$PORT " || echo "")
elif command -v netstat &> /dev/null; then
    LISTENING=$(netstat -tlnp | grep ":$PORT " || echo "")
else
    LISTENING=""
fi

if [ -n "$LISTENING" ]; then
    echo -e "${GREEN}✓ Port $PORT is listening locally${NC}"
    echo "  Details: $LISTENING"
else
    echo -e "${RED}✗ Port $PORT is NOT listening locally${NC}"
fi
echo ""

# 2. Check what process is using the port
echo "2. Checking what process is using port $PORT..."
if command -v lsof &> /dev/null; then
    PROCESS=$(sudo lsof -i :$PORT 2>/dev/null || echo "")
    if [ -n "$PROCESS" ]; then
        echo -e "${GREEN}✓ Process found:${NC}"
        echo "$PROCESS"
    else
        echo -e "${RED}✗ No process found using port $PORT${NC}"
    fi
elif command -v fuser &> /dev/null; then
    PROCESS=$(sudo fuser $PORT/tcp 2>/dev/null || echo "")
    if [ -n "$PROCESS" ]; then
        echo -e "${GREEN}✓ Process found:${NC}"
        echo "$PROCESS"
    else
        echo -e "${RED}✗ No process found using port $PORT${NC}"
    fi
else
    echo -e "${YELLOW}⚠ lsof/fuser not available, skipping process check${NC}"
fi
echo ""

# 3. Test local connection
echo "3. Testing local connection to port $PORT..."
if command -v curl &> /dev/null; then
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost:$PORT 2>&1 || echo "FAILED")
    if [ "$RESPONSE" = "FAILED" ] || [ "$RESPONSE" = "000" ]; then
        echo -e "${RED}✗ Cannot connect to localhost:$PORT${NC}"
    else
        echo -e "${GREEN}✓ Local connection successful (HTTP $RESPONSE)${NC}"
        echo "  Full response:"
        curl -s -I http://localhost:$PORT | head -5
    fi
elif command -v wget &> /dev/null; then
    if wget -q --spider --timeout=5 http://localhost:$PORT 2>/dev/null; then
        echo -e "${GREEN}✓ Local connection successful${NC}"
    else
        echo -e "${RED}✗ Cannot connect to localhost:$PORT${NC}"
    fi
else
    echo -e "${YELLOW}⚠ curl/wget not available, skipping connection test${NC}"
fi
echo ""

# 4. Test remote connection
echo "4. Testing remote connection to $IP:$PORT..."
if command -v curl &> /dev/null; then
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://$IP:$PORT 2>&1 || echo "FAILED")
    if [ "$RESPONSE" = "FAILED" ] || [ "$RESPONSE" = "000" ]; then
        echo -e "${RED}✗ Cannot connect to $IP:$PORT${NC}"
        echo "  This could mean:"
        echo "    - Service is not running"
        echo "    - Firewall is blocking the port"
        echo "    - Service is only listening on localhost (127.0.0.1)"
        echo "    - Network connectivity issue"
    else
        echo -e "${GREEN}✓ Remote connection successful (HTTP $RESPONSE)${NC}"
        echo "  Full response:"
        curl -s -I http://$IP:$PORT | head -5
    fi
elif command -v wget &> /dev/null; then
    if wget -q --spider --timeout=5 http://$IP:$PORT 2>/dev/null; then
        echo -e "${GREEN}✓ Remote connection successful${NC}"
    else
        echo -e "${RED}✗ Cannot connect to $IP:$PORT${NC}"
    fi
else
    echo -e "${YELLOW}⚠ curl/wget not available, skipping remote test${NC}"
fi
echo ""

# 5. Check firewall
echo "5. Checking firewall rules..."
if command -v ufw &> /dev/null && sudo ufw status &>/dev/null; then
    UFW_STATUS=$(sudo ufw status | grep "$PORT" || echo "")
    if [ -n "$UFW_STATUS" ]; then
        echo -e "${GREEN}✓ UFW rule found:${NC}"
        echo "$UFW_STATUS"
    else
        echo -e "${YELLOW}⚠ No UFW rule found for port $PORT${NC}"
        echo "  You may need to allow the port:"
        echo "    sudo ufw allow $PORT/tcp"
    fi
elif command -v firewall-cmd &> /dev/null; then
    if sudo firewall-cmd --list-ports 2>/dev/null | grep -q "$PORT"; then
        echo -e "${GREEN}✓ Firewall rule found for port $PORT${NC}"
    else
        echo -e "${YELLOW}⚠ No firewall rule found for port $PORT${NC}"
        echo "  You may need to allow the port:"
        echo "    sudo firewall-cmd --add-port=$PORT/tcp --permanent"
        echo "    sudo firewall-cmd --reload"
    fi
else
    echo -e "${YELLOW}⚠ Firewall tool not found or not accessible${NC}"
fi
echo ""

# 6. Check if service is bound to all interfaces
echo "6. Checking if service is listening on all interfaces (0.0.0.0)..."
if command -v ss &> /dev/null; then
    ALL_INTERFACES=$(ss -tlnp | grep ":$PORT " | grep "0.0.0.0" || echo "")
    LOCALHOST_ONLY=$(ss -tlnp | grep ":$PORT " | grep "127.0.0.1" || echo "")
    
    if [ -n "$ALL_INTERFACES" ]; then
        echo -e "${GREEN}✓ Service is listening on all interfaces (0.0.0.0)${NC}"
        echo "  This means it's accessible from remote hosts"
    elif [ -n "$LOCALHOST_ONLY" ]; then
        echo -e "${RED}✗ Service is only listening on localhost (127.0.0.1)${NC}"
        echo "  This means it's NOT accessible from remote hosts"
        echo "  You need to configure the service to listen on 0.0.0.0 or the specific IP"
    else
        echo -e "${YELLOW}⚠ Could not determine listening interface${NC}"
    fi
elif command -v netstat &> /dev/null; then
    ALL_INTERFACES=$(netstat -tlnp | grep ":$PORT " | grep "0.0.0.0" || echo "")
    LOCALHOST_ONLY=$(netstat -tlnp | grep ":$PORT " | grep "127.0.0.1" || echo "")
    
    if [ -n "$ALL_INTERFACES" ]; then
        echo -e "${GREEN}✓ Service is listening on all interfaces (0.0.0.0)${NC}"
    elif [ -n "$LOCALHOST_ONLY" ]; then
        echo -e "${RED}✗ Service is only listening on localhost (127.0.0.1)${NC}"
        echo "  Configure the service to listen on 0.0.0.0"
    else
        echo -e "${YELLOW}⚠ Could not determine listening interface${NC}"
    fi
fi
echo ""

# 7. Check systemd services
echo "7. Checking systemd services that might use port $PORT..."
SYSTEMD_SERVICES=$(systemctl list-units --type=service --state=running | grep -E "(solar|monitoring|web|api|nginx|apache)" || echo "")
if [ -n "$SYSTEMD_SERVICES" ]; then
    echo -e "${GREEN}✓ Found potentially relevant services:${NC}"
    echo "$SYSTEMD_SERVICES"
else
    echo -e "${YELLOW}⚠ No obvious services found${NC}"
fi
echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "If nothing is appearing at http://$IP:$PORT, check:"
echo "  1. Is the service running? (check systemd services)"
echo "  2. Is it listening on 0.0.0.0 (not just 127.0.0.1)?"
echo "  3. Is the firewall allowing port $PORT?"
echo "  4. Is the service configured to use port $PORT?"
echo "  5. Check service logs for errors"
echo ""
echo "Quick fixes:"
echo "  - Allow firewall: sudo ufw allow $PORT/tcp"
echo "  - Check service: sudo systemctl status solar-monitoring"
echo "  - View logs: sudo journalctl -u solar-monitoring -f"
echo ""

