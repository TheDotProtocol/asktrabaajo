#!/bin/bash

# AskTrabaajo SSL Certificate Setup Script
# This script sets up SSL certificates using Let's Encrypt

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

echo -e "${BLUE}🔒 Setting up SSL certificates for AskTrabaajo${NC}"

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    print_error "Certbot is not installed. Please install it first:"
    echo "sudo apt-get update && sudo apt-get install certbot"
    exit 1
fi

# Create SSL directory
mkdir -p nginx/ssl

# Get domain from user
read -p "Enter your domain (e.g., asktrabaajo.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    print_error "Domain is required"
    exit 1
fi

print_status "Setting up SSL certificate for $DOMAIN"

# Stop nginx if running
docker-compose stop nginx 2>/dev/null || true

# Create temporary nginx config for certificate validation
cat > nginx/nginx-temp.conf << EOF
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    server {
        listen 80;
        server_name $DOMAIN www.$DOMAIN;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://\$server_name\$request_uri;
        }
    }
}
EOF

# Start temporary nginx container for certificate validation
docker run -d --name nginx-temp \
    -p 80:80 \
    -v $(pwd)/nginx/nginx-temp.conf:/etc/nginx/nginx.conf \
    -v $(pwd)/certbot/www:/var/www/certbot \
    nginx:alpine

# Create certbot directories
mkdir -p certbot/www certbot/conf

# Get SSL certificate
print_status "Obtaining SSL certificate from Let's Encrypt..."
docker run --rm \
    -v $(pwd)/certbot/conf:/etc/letsencrypt \
    -v $(pwd)/certbot/www:/var/www/certbot \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email admin@$DOMAIN \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN \
    -d www.$DOMAIN

# Stop temporary nginx
docker stop nginx-temp
docker rm nginx-temp

# Copy certificates to nginx ssl directory
print_status "Copying certificates to nginx ssl directory..."
cp certbot/conf/live/$DOMAIN/fullchain.pem nginx/ssl/$DOMAIN.crt
cp certbot/conf/live/$DOMAIN/privkey.pem nginx/ssl/$DOMAIN.key

# Set proper permissions
chmod 644 nginx/ssl/$DOMAIN.crt
chmod 600 nginx/ssl/$DOMAIN.key

# Create renewal script
cat > scripts/renew-ssl.sh << EOF
#!/bin/bash
docker run --rm \\
    -v \$(pwd)/certbot/conf:/etc/letsencrypt \\
    -v \$(pwd)/certbot/www:/var/www/certbot \\
    certbot/certbot renew

cp certbot/conf/live/$DOMAIN/fullchain.pem nginx/ssl/$DOMAIN.crt
cp certbot/conf/live/$DOMAIN/privkey.pem nginx/ssl/$DOMAIN.key

chmod 644 nginx/ssl/$DOMAIN.crt
chmod 600 nginx/ssl/$DOMAIN.key

docker-compose restart nginx
EOF

chmod +x scripts/renew-ssl.sh

# Update nginx configuration with domain
sed -i "s/asktrabaajo.com/$DOMAIN/g" nginx/nginx.conf

print_status "SSL certificate setup completed!"
print_status "Certificate files:"
echo "  - nginx/ssl/$DOMAIN.crt"
echo "  - nginx/ssl/$DOMAIN.key"
print_status "Renewal script: scripts/renew-ssl.sh"
print_warning "Add to crontab for auto-renewal: 0 12 * * * /path/to/scripts/renew-ssl.sh" 