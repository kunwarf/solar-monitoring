#!/bin/bash

# Solar Monitoring System - New Machine Setup Script
# This script helps automate the installation of prerequisites on a new machine

set -e  # Exit on error

echo "=========================================="
echo "Solar Monitoring System - Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Please do not run this script as root"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_VERSION=$VERSION_ID
else
    print_error "Cannot detect OS. This script supports Ubuntu/Debian/CentOS"
    exit 1
fi

print_info "Detected OS: $OS $OS_VERSION"
echo ""

# Update package list
print_info "Updating package list..."
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    sudo apt update
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
    sudo yum update -y
fi

# Install Git
print_info "Installing Git..."
if command -v git &> /dev/null; then
    print_success "Git is already installed: $(git --version)"
else
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        sudo apt install -y git
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        sudo yum install -y git
    fi
    print_success "Git installed: $(git --version)"
fi

# Install Python 3.11+
print_info "Checking Python installation..."
if command -v python3.11 &> /dev/null; then
    PYTHON_VERSION=$(python3.11 --version)
    print_success "Python 3.11+ found: $PYTHON_VERSION"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
        print_success "Python $PYTHON_VERSION found (meets requirement)"
    else
        print_error "Python 3.11+ required. Found: $PYTHON_VERSION"
        print_info "Installing Python 3.11..."
        if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
            sudo apt install -y software-properties-common
            sudo add-apt-repository -y ppa:deadsnakes/ppa
            sudo apt update
            sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
        elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
            print_error "Please install Python 3.11+ manually on CentOS/RHEL"
            print_info "Consider using pyenv: https://github.com/pyenv/pyenv"
        fi
    fi
else
    print_error "Python 3 not found. Installing..."
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
    fi
fi

# Install pip if not present
if ! command -v pip3 &> /dev/null; then
    print_info "Installing pip..."
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        sudo apt install -y python3-pip
    fi
fi

# Install Node.js 20+
print_info "Checking Node.js installation..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)
    if [ "$NODE_MAJOR" -ge 20 ]; then
        print_success "Node.js $NODE_VERSION found (meets requirement)"
    else
        print_error "Node.js 20+ required. Found: $NODE_VERSION"
        print_info "Installing Node.js 20..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
else
    print_info "Node.js not found. Installing Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    print_success "Node.js installed: $(node --version)"
fi

# Install npm if not present
if ! command -v npm &> /dev/null; then
    print_error "npm not found. This should have been installed with Node.js"
else
    print_success "npm found: $(npm --version)"
fi

# Install system dependencies for backend
print_info "Installing system dependencies for backend..."
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    sudo apt install -y \
        build-essential \
        gcc \
        g++ \
        libmodbus-dev \
        setserial \
        curl
    print_success "System dependencies installed"
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
    sudo yum groupinstall -y "Development Tools"
    sudo yum install -y \
        gcc \
        gcc-c++ \
        libmodbus-devel \
        curl
    print_success "System dependencies installed"
fi

# Add user to dialout group (for serial port access)
print_info "Adding user to dialout group for serial port access..."
sudo usermod -a -G dialout $USER
print_success "User added to dialout group (logout/login required for changes)"

# Install Docker (optional)
read -p "Do you want to install Docker and Docker Compose? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Installing Docker..."
    if command -v docker &> /dev/null; then
        print_success "Docker is already installed: $(docker --version)"
    else
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        print_success "Docker installed"
    fi
    
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose is already installed: $(docker-compose --version)"
    else
        print_info "Installing Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        print_success "Docker Compose installed"
    fi
fi

# Summary
echo ""
echo "=========================================="
print_success "Setup completed!"
echo "=========================================="
echo ""
echo "Installed/Verified:"
echo "  - Git: $(git --version)"
echo "  - Python: $(python3 --version 2>/dev/null || echo 'Not found')"
echo "  - Node.js: $(node --version)"
echo "  - npm: $(npm --version)"
echo ""
echo "Next steps:"
echo "  1. Log out and log back in (for group changes to take effect)"
echo "  2. Clone your repository: git clone <repo-url> solar-monitoring"
echo "  3. Follow the MIGRATION_GUIDE.md for detailed migration steps"
echo ""
print_info "For mobile development, you may also need:"
echo "  - Expo CLI: npm install -g expo-cli"
echo "  - Android Studio (for Android development)"
echo "  - Xcode (for iOS development on macOS)"
echo ""

