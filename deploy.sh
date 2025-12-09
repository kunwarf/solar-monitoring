#!/bin/bash

# Solar Monitoring System Deployment Script
# This script provides easy deployment options for both traditional and Docker setups

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
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

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

# Main menu
show_menu() {
    echo
    print_header "Solar Monitoring System Deployment"
    echo "1. Traditional Deployment (Systemd + Nginx)"
    echo "2. Docker Deployment"
    echo "3. Development Setup"
    echo "4. Health Check"
    echo "5. Backup"
    echo "6. Update"
    echo "7. Exit"
    echo
    read -p "Select an option (1-7): " choice
}

# Traditional deployment
deploy_traditional() {
    print_header "Traditional Deployment Setup"
    
    # Check prerequisites
    check_command "python3"
    check_command "nginx"
    check_command "systemctl"
    
    # Install dependencies
    print_warning "Installing system dependencies..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv nginx git curl
    
    # Create user
    if ! id "solar" &>/dev/null; then
        sudo useradd -r -s /bin/false solar
        print_success "Created solar user"
    fi
    
    # Setup application directory
    sudo mkdir -p /opt/solar-monitoring
    sudo chown solar:solar /opt/solar-monitoring
    
    # Copy application files
    sudo cp -r . /opt/solar-monitoring/
    cd /opt/solar-monitoring
    
    # Setup Python environment
    sudo -u solar python3 -m venv venv
    sudo -u solar venv/bin/pip install -r requirements.txt
    
    # Build React app
    if [ -d "webapp-react" ]; then
        cd webapp-react
        
        # Install missing dependencies first
        print_warning "Installing React dependencies..."
        sudo -u solar npm install @vitejs/plugin-react@^4.2.1 --save-dev
        sudo -u solar npm install
        
        # Build the application
        print_warning "Building React application..."
        sudo -u solar npm run build
        
        cd ..
    fi
    
    # Setup systemd service
    sudo cp /opt/solar-monitoring/solar-monitoring.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable solar-monitoring
    
    # Setup nginx
    sudo cp /opt/solar-monitoring/nginx-site.conf /etc/nginx/sites-available/solar-monitoring
    sudo ln -sf /etc/nginx/sites-available/solar-monitoring /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t
    sudo systemctl restart nginx
    
    print_success "Traditional deployment completed!"
    print_warning "Don't forget to:"
    echo "  1. Edit /opt/solar-monitoring/config.yaml"
    echo "  2. Start the service: sudo systemctl start solar-monitoring"
    echo "  3. Check status: sudo systemctl status solar-monitoring"
}

# Docker deployment
deploy_docker() {
    print_header "Docker Deployment Setup"
    
    # Check prerequisites
    check_command "docker"
    check_command "docker-compose"
    
    # Create necessary directories
    mkdir -p mosquitto-data mosquitto-logs ssl backups
    
    # Copy configuration files
    if [ ! -f "config.yaml" ]; then
        cp config.example.yaml config.yaml
        print_warning "Created config.yaml from example. Please edit it with your settings."
    fi
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        cat > .env << EOF
POSTGRES_PASSWORD=$(openssl rand -base64 32)
MQTT_USERNAME=solar_user
MQTT_PASSWORD=$(openssl rand -base64 16)
TZ=Asia/Karachi
EOF
        print_success "Created .env file with random passwords"
    fi
    
    # Build and start services
    print_warning "Building and starting Docker services..."
    docker-compose up -d --build
    
    # Wait for services to be ready
    print_warning "Waiting for services to start..."
    sleep 30
    
    # Check health
    if curl -s http://localhost/api/now > /dev/null; then
        print_success "Docker deployment completed successfully!"
        echo "Access your application at: http://localhost"
    else
        print_error "Deployment completed but API is not responding"
        echo "Check logs with: docker-compose logs -f"
    fi
}

# Development setup
setup_development() {
    print_header "Development Setup"
    
    # Check prerequisites
    check_command "python3"
    check_command "node"
    check_command "npm"
    
    # Setup Python environment
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Setup React app
    if [ -d "webapp-react" ]; then
        cd webapp-react
        npm install
        cd ..
    fi
    
    # Copy config
    if [ ! -f "config.yaml" ]; then
        cp config.example.yaml config.yaml
        print_warning "Created config.yaml from example. Please edit it."
    fi
    
    print_success "Development environment ready!"
    print_warning "To start development:"
    echo "  1. Activate Python environment: source venv/bin/activate"
    echo "  2. Start backend: python -m solarhub.main"
    echo "  3. Start frontend: cd webapp-react && npm run dev"
}

# Health check
health_check() {
    print_header "System Health Check"
    
    # Check if running in Docker
    if [ -f "docker-compose.yml" ] && docker-compose ps | grep -q "Up"; then
        echo "Docker deployment detected"
        
        # Check Docker services
        echo "Docker Services:"
        docker-compose ps
        
        # Check API
        if curl -s http://localhost/api/now > /dev/null; then
            print_success "API is responding"
        else
            print_error "API is not responding"
        fi
        
        # Check web app
        if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
            print_success "Web application is accessible"
        else
            print_error "Web application is not accessible"
        fi
        
    else
        echo "Traditional deployment detected"
        
        # Check systemd service
        if systemctl is-active --quiet solar-monitoring; then
            print_success "Solar monitoring service is running"
        else
            print_error "Solar monitoring service is not running"
        fi
        
        # Check nginx
        if systemctl is-active --quiet nginx; then
            print_success "Nginx is running"
        else
            print_error "Nginx is not running"
        fi
        
        # Check API
        if curl -s http://localhost/api/now > /dev/null; then
            print_success "API is responding"
        else
            print_error "API is not responding"
        fi
    fi
    
    echo
    echo "System resources:"
    if command -v docker &> /dev/null && docker ps &> /dev/null; then
        docker stats --no-stream
    else
        top -bn1 | head -20
    fi
}

# Backup
backup_system() {
    print_header "System Backup"
    
    DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="./backups"
    
    mkdir -p $BACKUP_DIR
    
    if [ -f "docker-compose.yml" ] && docker-compose ps | grep -q "Up"; then
        echo "Backing up Docker deployment..."
        
        # Backup volumes
        docker run --rm -v solar-monitoring_postgres-data:/data -v $(pwd)/$BACKUP_DIR:/backup alpine tar czf /backup/postgres_$DATE.tar.gz -C /data .
        docker run --rm -v solar-monitoring_redis-data:/data -v $(pwd)/$BACKUP_DIR:/backup alpine tar czf /backup/redis_$DATE.tar.gz -C /data .
        
        # Backup application files
        tar czf $BACKUP_DIR/app_$DATE.tar.gz config.yaml solarhub.db
        
        print_success "Docker backup completed: $BACKUP_DIR"
    else
        echo "Backing up traditional deployment..."
        
        # Backup application directory
        sudo tar czf $BACKUP_DIR/solar-monitoring_$DATE.tar.gz -C /opt solar-monitoring
        
        # Backup database
        sudo cp /opt/solar-monitoring/solarhub.db $BACKUP_DIR/solarhub_$DATE.db
        
        print_success "Traditional backup completed: $BACKUP_DIR"
    fi
    
    # Cleanup old backups (keep last 7 days)
    find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
    find $BACKUP_DIR -name "*.db" -mtime +7 -delete
}

# Update system
update_system() {
    print_header "System Update"
    
    if [ -f "docker-compose.yml" ] && docker-compose ps | grep -q "Up"; then
        echo "Updating Docker deployment..."
        
        # Pull latest changes
        git pull origin main
        
        # Rebuild and restart
        docker-compose down
        docker-compose up -d --build
        
        print_success "Docker deployment updated!"
    else
        echo "Updating traditional deployment..."
        
        # Stop service
        sudo systemctl stop solar-monitoring
        
        # Pull latest changes
        git pull origin main
        
        # Update Python dependencies
        cd /opt/solar-monitoring
        sudo -u solar venv/bin/pip install -r requirements.txt
        
        # Rebuild React app
        if [ -d "webapp-react" ]; then
            cd webapp-react
            sudo -u solar npm install
            sudo -u solar npm run build
            cd ..
        fi
        
        # Restart service
        sudo systemctl start solar-monitoring
        
        print_success "Traditional deployment updated!"
    fi
}

# Main loop
while true; do
    show_menu
    
    case $choice in
        1)
            deploy_traditional
            ;;
        2)
            deploy_docker
            ;;
        3)
            setup_development
            ;;
        4)
            health_check
            ;;
        5)
            backup_system
            ;;
        6)
            update_system
            ;;
        7)
            print_success "Goodbye!"
            exit 0
            ;;
        *)
            print_error "Invalid option. Please select 1-7."
            ;;
    esac
    
    echo
    read -p "Press Enter to continue..."
done
