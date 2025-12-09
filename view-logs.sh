#!/bin/bash

# Log Viewer Script

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

show_menu() {
    echo
    print_header "Log Viewer"
    echo "1. Backend logs (systemd)"
    echo "2. Backend logs (Docker)"
    echo "3. Nginx access logs"
    echo "4. Nginx error logs"
    echo "5. All logs (real-time)"
    echo "6. Recent errors only"
    echo "7. Exit"
    echo
    read -p "Select an option (1-7): " choice
}

view_backend_systemd() {
    print_header "Backend Logs (Systemd)"
    echo "Press Ctrl+C to exit"
    echo
    sudo journalctl -u solar-monitoring -f
}

view_backend_docker() {
    print_header "Backend Logs (Docker)"
    echo "Press Ctrl+C to exit"
    echo
    docker-compose logs -f solar-backend
}

view_nginx_access() {
    print_header "Nginx Access Logs"
    echo "Press Ctrl+C to exit"
    echo
    sudo tail -f /var/log/nginx/access.log
}

view_nginx_error() {
    print_header "Nginx Error Logs"
    echo "Press Ctrl+C to exit"
    echo
    sudo tail -f /var/log/nginx/error.log
}

view_all_logs() {
    print_header "All Logs (Real-time)"
    echo "Press Ctrl+C to exit"
    echo
    
    # Check which backend is running
    if systemctl is-active --quiet solar-monitoring 2>/dev/null; then
        echo "=== Backend Logs (Systemd) ==="
        sudo journalctl -u solar-monitoring -f &
        BACKEND_PID=$!
    elif docker-compose ps | grep -q "solar-backend.*Up" 2>/dev/null; then
        echo "=== Backend Logs (Docker) ==="
        docker-compose logs -f solar-backend &
        BACKEND_PID=$!
    else
        echo "No backend service running"
        BACKEND_PID=""
    fi
    
    echo "=== Nginx Access Logs ==="
    sudo tail -f /var/log/nginx/access.log &
    ACCESS_PID=$!
    
    echo "=== Nginx Error Logs ==="
    sudo tail -f /var/log/nginx/error.log &
    ERROR_PID=$!
    
    # Wait for user to press Ctrl+C
    trap "kill $BACKEND_PID $ACCESS_PID $ERROR_PID 2>/dev/null; exit" INT
    wait
}

view_recent_errors() {
    print_header "Recent Errors"
    
    echo "=== Recent Backend Errors ==="
    if systemctl is-active --quiet solar-monitoring 2>/dev/null; then
        sudo journalctl -u solar-monitoring --no-pager -n 50 | grep -i error || echo "No recent backend errors"
    elif docker-compose ps | grep -q "solar-backend.*Up" 2>/dev/null; then
        docker-compose logs --tail=50 solar-backend | grep -i error || echo "No recent backend errors"
    else
        echo "Backend not running"
    fi
    
    echo
    echo "=== Recent Nginx Errors ==="
    if [ -f "/var/log/nginx/error.log" ]; then
        sudo tail -50 /var/log/nginx/error.log | grep -i error || echo "No recent nginx errors"
    else
        echo "Nginx error log not found"
    fi
    
    echo
    echo "=== Recent System Errors ==="
    sudo journalctl --no-pager -n 50 | grep -i error | tail -10 || echo "No recent system errors"
}

# Main loop
while true; do
    show_menu
    
    case $choice in
        1)
            view_backend_systemd
            ;;
        2)
            view_backend_docker
            ;;
        3)
            view_nginx_access
            ;;
        4)
            view_nginx_error
            ;;
        5)
            view_all_logs
            ;;
        6)
            view_recent_errors
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
