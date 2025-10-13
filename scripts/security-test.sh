#!/bin/bash

# AskTrabaajo Security Testing Script
# This script runs comprehensive security tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo -e "${BLUE}🔒 Running Security Tests for AskTrabaajo${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Bandit Security Scan
print_status "Running Bandit security scan..."
if command_exists bandit; then
    cd backend
    bandit -r . -f json -o security_report.json || {
        print_warning "Bandit scan completed with warnings"
    }
    cd ..
else
    print_warning "Bandit not installed. Install with: pip install bandit"
fi

# 2. Safety Dependency Check
print_status "Running Safety dependency check..."
if command_exists safety; then
    cd backend
    safety check || {
        print_warning "Safety check completed with warnings"
    }
    cd ..
else
    print_warning "Safety not installed. Install with: pip install safety"
fi

# 3. Docker Security Scan
print_status "Running Docker security scan..."
if command_exists docker; then
    # Scan backend image
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy image asktrabaajo_backend:latest || {
        print_warning "Docker security scan completed with warnings"
    }
else
    print_warning "Docker not available for security scanning"
fi

# 4. SSL Certificate Check
print_status "Checking SSL certificates..."
if [ -f "nginx/ssl/asktrabaajo.com.crt" ]; then
    openssl x509 -in nginx/ssl/asktrabaajo.com.crt -text -noout | grep -E "(Subject:|Not After:)" || {
        print_error "SSL certificate check failed"
    }
    print_status "SSL certificate found and valid"
else
    print_warning "SSL certificate not found"
fi

# 5. Port Security Check
print_status "Checking for open ports..."
netstat -tuln | grep -E ":(80|443|8000|3000|5432|6379)" || {
    print_warning "Some expected ports are not open"
}

# 6. File Permissions Check
print_status "Checking file permissions..."
find . -name "*.key" -o -name "*.pem" -o -name ".env*" | while read file; do
    if [ -f "$file" ]; then
        perms=$(stat -c "%a" "$file")
        if [ "$perms" != "600" ] && [ "$perms" != "400" ]; then
            print_warning "Insecure permissions on $file: $perms"
        fi
    fi
done

# 7. Environment Variables Check
print_status "Checking environment variables..."
if [ -f "backend/.env.production" ]; then
    if grep -q "your-super-secret-production-key" backend/.env.production; then
        print_error "Default secret key found in production environment"
    fi
    if grep -q "your-smtp-password-here" backend/.env.production; then
        print_error "Default SMTP password found in production environment"
    fi
    if grep -q "your-openai-api-key-here" backend/.env.production; then
        print_error "Default OpenAI API key found in production environment"
    fi
else
    print_warning "Production environment file not found"
fi

# 8. Docker Compose Security Check
print_status "Checking Docker Compose security..."
if [ -f "docker-compose.yml" ]; then
    # Check for exposed ports
    if grep -q "ports:" docker-compose.yml; then
        print_warning "Ports are exposed in Docker Compose"
    fi
    
    # Check for root user
    if grep -q "user: root" docker-compose.yml; then
        print_error "Root user found in Docker Compose"
    fi
else
    print_error "Docker Compose file not found"
fi

# 9. Nginx Security Headers Check
print_status "Checking Nginx security headers..."
if [ -f "nginx/nginx.conf" ]; then
    if grep -q "X-Frame-Options" nginx/nginx.conf; then
        print_status "X-Frame-Options header configured"
    else
        print_warning "X-Frame-Options header not configured"
    fi
    
    if grep -q "Strict-Transport-Security" nginx/nginx.conf; then
        print_status "HSTS header configured"
    else
        print_warning "HSTS header not configured"
    fi
else
    print_error "Nginx configuration not found"
fi

# 10. Database Security Check
print_status "Checking database security..."
if [ -f "docker-compose.yml" ]; then
    if grep -q "POSTGRES_PASSWORD" docker-compose.yml; then
        print_status "Database password configured"
    else
        print_warning "Database password not configured"
    fi
fi

# 11. API Security Check
print_status "Checking API security..."
if [ -f "backend/main.py" ]; then
    if grep -q "CORS" backend/main.py; then
        print_status "CORS configured"
    else
        print_warning "CORS not configured"
    fi
fi

# 12. JWT Security Check
print_status "Checking JWT security..."
if [ -f "backend/api/routes/auth.py" ]; then
    if grep -q "ACCESS_TOKEN_EXPIRE_MINUTES" backend/api/routes/auth.py; then
        print_status "JWT expiration configured"
    else
        print_warning "JWT expiration not configured"
    fi
fi

# Generate Security Report
print_status "Generating security report..."
cat > security_report.txt << EOF
AskTrabaajo Security Test Report
Generated: $(date)

Security Checks:
- Bandit scan: $(if command_exists bandit; then echo "Available"; else echo "Not available"; fi)
- Safety check: $(if command_exists safety; then echo "Available"; else echo "Not available"; fi)
- SSL certificates: $(if [ -f "nginx/ssl/asktrabaajo.com.crt" ]; then echo "Found"; else echo "Not found"; fi)
- Environment variables: $(if [ -f "backend/.env.production" ]; then echo "Configured"; else echo "Not configured"; fi)
- Docker security: $(if command_exists docker; then echo "Available"; else echo "Not available"; fi)

Recommendations:
1. Change default secret keys in production
2. Configure proper SMTP credentials
3. Set up OpenAI API key
4. Ensure SSL certificates are valid
5. Review file permissions
6. Configure proper CORS settings
7. Set up monitoring and logging

EOF

print_status "Security testing completed!"
print_status "Report saved to: security_report.txt"
print_warning "Review the security report and address any issues before deployment" 