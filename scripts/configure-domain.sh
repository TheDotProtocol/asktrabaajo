#!/bin/bash

# AskTrabaajo Domain Configuration Script
# This script configures the domain settings for the application

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

echo -e "${BLUE}🌐 Configuring Domain Settings for AskTrabaajo${NC}"

# Get domain from user
read -p "Enter your domain (e.g., asktrabaajo.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    print_error "Domain is required"
    exit 1
fi

print_status "Configuring domain: $DOMAIN"

# Update nginx configuration
print_status "Updating Nginx configuration..."
sed -i "s/asktrabaajo.com/$DOMAIN/g" nginx/nginx.conf
sed -i "s/www.asktrabaajo.com/www.$DOMAIN/g" nginx/nginx.conf

# Update docker-compose.yml
print_status "Updating Docker Compose configuration..."
sed -i "s/asktrabaajo.com/$DOMAIN/g" docker-compose.yml

# Update environment template
print_status "Updating environment configuration..."
sed -i "s/asktrabaajo.com/$DOMAIN/g" backend/env.production.template

# Update frontend environment
print_status "Updating frontend configuration..."
if [ -f "frontend/.env.local" ]; then
    sed -i "s/asktrabaajo.com/$DOMAIN/g" frontend/.env.local
else
    cat > frontend/.env.local << EOF
NEXT_PUBLIC_API_URL=https://api.$DOMAIN
NEXT_PUBLIC_DOMAIN=$DOMAIN
EOF
fi

# Update backend environment
print_status "Updating backend configuration..."
if [ -f "backend/.env.production" ]; then
    sed -i "s/asktrabaajo.com/$DOMAIN/g" backend/.env.production
else
    cp backend/env.production.template backend/.env.production
    sed -i "s/asktrabaajo.com/$DOMAIN/g" backend/.env.production
fi

# Update CORS settings
print_status "Updating CORS settings..."
sed -i "s/asktrabaajo.com/$DOMAIN/g" backend/.env.production

# Create DNS configuration guide
print_status "Creating DNS configuration guide..."
cat > DNS_SETUP.md << EOF
# DNS Configuration for $DOMAIN

## Required DNS Records

### A Records
- \`$DOMAIN\` → Your server IP address
- \`www.$DOMAIN\` → Your server IP address
- \`api.$DOMAIN\` → Your server IP address

### CNAME Records (Optional)
- \`www.$DOMAIN\` → \`$DOMAIN\`

### MX Records (for email)
- \`$DOMAIN\` → \`mail.$DOMAIN\` (Priority: 10)

### TXT Records
- \`$DOMAIN\` → \`v=spf1 include:_spf.google.com ~all\` (SPF)
- \`$DOMAIN\` → \`google-site-verification=your-verification-code\` (if using Google Search Console)

## Example DNS Configuration

\`\`\`
# A Records
$DOMAIN.          IN A    YOUR_SERVER_IP
www.$DOMAIN.      IN A    YOUR_SERVER_IP
api.$DOMAIN.      IN A    YOUR_SERVER_IP

# CNAME Records
mail.$DOMAIN.     IN CNAME $DOMAIN.

# MX Records
$DOMAIN.          IN MX 10 mail.$DOMAIN.

# TXT Records
$DOMAIN.          IN TXT "v=spf1 include:_spf.google.com ~all"
\`\`\`

## SSL Certificate

After setting up DNS, run:
\`\`\`bash
./scripts/setup-ssl.sh
\`\`\`

## Verification

Test your DNS configuration:
\`\`\`bash
nslookup $DOMAIN
nslookup www.$DOMAIN
nslookup api.$DOMAIN
\`\`\`
EOF

print_status "Domain configuration completed!"
print_status "Files updated:"
echo "  - nginx/nginx.conf"
echo "  - docker-compose.yml"
echo "  - backend/.env.production"
echo "  - frontend/.env.local"
print_status "DNS setup guide created: DNS_SETUP.md"
print_warning "Please configure your DNS records as described in DNS_SETUP.md" 