#!/bin/bash

# AskTrabaajo Production Deployment Script
# Usage: ./scripts/deploy.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Environment variables
ENVIRONMENT=${1:-production}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/asktrabaajo_${TIMESTAMP}"

echo -e "${BLUE}🚀 Starting AskTrabaajo deployment for ${ENVIRONMENT} environment${NC}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed"
    exit 1
fi

print_status "Prerequisites check passed"

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs uploads nginx/logs nginx/ssl monitoring backups

# Backup existing data if exists
if [ -d "data" ]; then
    print_warning "Creating backup of existing data..."
    cp -r data "$BACKUP_DIR"
    print_status "Backup created at $BACKUP_DIR"
fi

# Load environment variables
if [ -f ".env.${ENVIRONMENT}" ]; then
    print_status "Loading environment variables from .env.${ENVIRONMENT}"
    export $(cat .env.${ENVIRONMENT} | xargs)
else
    print_warning "No .env.${ENVIRONMENT} file found, using defaults"
fi

# Run security checks
print_status "Running security checks..."
if command -v bandit &> /dev/null; then
    bandit -r backend/ -f json -o security_report.json || print_warning "Security scan completed with warnings"
else
    print_warning "Bandit not installed, skipping security scan"
fi

# Run tests
print_status "Running tests..."
cd backend
if command -v pytest &> /dev/null; then
    pytest tests/ -v --cov=api --cov-report=html --cov-report=term-missing || {
        print_error "Tests failed"
        exit 1
    }
else
    print_warning "pytest not installed, skipping tests"
fi
cd ..

# Build and deploy with Docker Compose
print_status "Building and deploying with Docker Compose..."

# Stop existing containers
docker-compose down || print_warning "No existing containers to stop"

# Pull latest images
docker-compose pull

# Build images
docker-compose build --no-cache

# Start services
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 30

# Health checks
print_status "Running health checks..."

# Check backend
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "Backend is healthy"
else
    print_error "Backend health check failed"
    docker-compose logs backend
    exit 1
fi

# Check frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    print_status "Frontend is healthy"
else
    print_error "Frontend health check failed"
    docker-compose logs frontend
    exit 1
fi

# Check database
if docker-compose exec -T postgres pg_isready -U asktrabaajo_prod > /dev/null 2>&1; then
    print_status "Database is healthy"
else
    print_error "Database health check failed"
    docker-compose logs postgres
    exit 1
fi

# Run database migrations
print_status "Running database migrations..."
docker-compose exec -T backend python -c "from api.models.database import create_tables; create_tables()" || {
    print_error "Database migration failed"
    exit 1
}

# Performance test
print_status "Running performance tests..."
if command -v locust &> /dev/null; then
    timeout 60 locust --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=30s --headless || print_warning "Performance test completed"
else
    print_warning "Locust not installed, skipping performance test"
fi

# SSL certificate check (if using Let's Encrypt)
if [ -f "nginx/ssl/asktrabaajo.com.crt" ]; then
    print_status "SSL certificate found"
else
    print_warning "SSL certificate not found, please configure SSL certificates"
fi

# Final status check
print_status "Final status check..."
docker-compose ps

# Print access information
echo -e "${BLUE}🎉 Deployment completed successfully!${NC}"
echo -e "${BLUE}📊 Access Information:${NC}"
echo -e "   Frontend: https://asktrabaajo.com"
echo -e "   Backend API: https://api.asktrabaajo.com"
echo -e "   Monitoring: http://localhost:9090 (Prometheus)"
echo -e "   Dashboard: http://localhost:3001 (Grafana)"
echo -e "   Nginx Status: http://localhost:8080/nginx_status"

# Cleanup old backups (keep last 5)
print_status "Cleaning up old backups..."
ls -t /backups/asktrabaajo_* | tail -n +6 | xargs -r rm -rf

print_status "Deployment script completed successfully!" 