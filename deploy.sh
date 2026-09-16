#!/bin/bash

# Deployment script for VPS/Linux VM

echo "🚀 A4 PDF Generator Deployment Script"
echo "====================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
   echo "Please run as root (use sudo)"
   exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt-get update
apt-get upgrade -y

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "🐳 Installing Docker Compose..."
    apt-get install -y docker-compose
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p saved_configs generated_pdfs

# Set permissions
chmod 755 saved_configs generated_pdfs

# Build and start the container
echo "🏗️ Building Docker image..."
docker-compose build

echo "🚀 Starting application..."
docker-compose up -d

# Get IP address
IP=$(hostname -I | awk '{print $1}')

echo ""
echo "✅ Deployment complete!"
echo "====================================="
echo "Access your PDF generator at:"
echo "  http://$IP:8501"
echo ""
echo "To stop the service: docker-compose down"
echo "To view logs: docker-compose logs -f"
echo "To restart: docker-compose restart"
