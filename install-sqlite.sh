#!/bin/bash

# Install SQLite command-line tools
# This script helps install sqlite3 on Linux systems

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Installing SQLite command-line tools...${NC}"

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS. Trying default installation..."
    OS="unknown"
fi

echo "Detected OS: $OS"

# Install based on OS
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    echo "Installing sqlite3 for Ubuntu/Debian..."
    sudo apt update
    sudo apt install -y sqlite3 libsqlite3-dev
    echo -e "${GREEN}✓ SQLite installed successfully${NC}"
    
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ] || [ "$OS" = "fedora" ]; then
    echo "Installing sqlite3 for CentOS/RHEL/Fedora..."
    if command -v dnf &> /dev/null; then
        sudo dnf install -y sqlite sqlite-devel
    else
        sudo yum install -y sqlite sqlite-devel
    fi
    echo -e "${GREEN}✓ SQLite installed successfully${NC}"
    
elif [ "$OS" = "arch" ] || [ "$OS" = "manjaro" ]; then
    echo "Installing sqlite3 for Arch/Manjaro..."
    sudo pacman -S --noconfirm sqlite
    echo -e "${GREEN}✓ SQLite installed successfully${NC}"
    
else
    echo -e "${YELLOW}Unknown OS. Please install sqlite3 manually:${NC}"
    echo "  Ubuntu/Debian: sudo apt install sqlite3"
    echo "  CentOS/RHEL:   sudo yum install sqlite"
    echo "  Fedora:        sudo dnf install sqlite"
    echo "  Arch:          sudo pacman -S sqlite"
    exit 1
fi

# Verify installation
if command -v sqlite3 &> /dev/null; then
    echo ""
    echo -e "${GREEN}Verification:${NC}"
    sqlite3 --version
    echo ""
    echo -e "${GREEN}SQLite is ready to use!${NC}"
    echo ""
    echo "You can now access your database with:"
    echo "  sqlite3 /home/faisal/.solarhub/solarhub.db"
else
    echo -e "${YELLOW}Warning: sqlite3 command not found after installation${NC}"
    echo "You may need to log out and back in, or run: source ~/.bashrc"
fi

