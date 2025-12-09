#!/bin/bash

# Fix permissions for building frontend
# This allows the user to write to the dist directory during build

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Fixing Build Permissions${NC}"
echo ""

PROJECT_DIR=$(pwd)
DIST_DIR="$PROJECT_DIR/dist"
CURRENT_USER=$(whoami)

echo "Project directory: $PROJECT_DIR"
echo "Dist directory: $DIST_DIR"
echo "Current user: $CURRENT_USER"
echo ""

# Check if dist directory exists
if [ -d "$DIST_DIR" ]; then
    echo "Dist directory exists. Fixing permissions..."
    
    # Change ownership to current user
    sudo chown -R "$CURRENT_USER:$CURRENT_USER" "$DIST_DIR"
    
    # Set proper permissions
    sudo chmod -R 755 "$DIST_DIR"
    sudo find "$DIST_DIR" -type f -exec chmod 644 {} \;
    sudo find "$DIST_DIR" -type d -exec chmod 755 {} \;
    
    echo -e "${GREEN}✓ Permissions fixed${NC}"
else
    echo "Dist directory doesn't exist yet. It will be created during build."
fi

echo ""
echo "You can now run: npm run build"
echo ""

