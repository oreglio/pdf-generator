# A4 PDF Generator - Deployment Guide

## 🚀 Hosting Options

### Option 1: VPS/Linux VM (Recommended)
**Works with: Freebox Delta VM, any VPS (DigitalOcean, Linode, OVH), AWS EC2**

#### Quick Deploy with Docker
```bash
# SSH into your server
ssh user@your-server-ip

# Clone or upload the files
git clone <your-repo> pdf-generator
cd pdf-generator

# Run the deployment script
sudo ./deploy.sh
```

The app will be available at `http://your-server-ip:8501`

#### Manual Installation (without Docker)
```bash
# Install Python 3.9+
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run pdf_generator_ui.py --server.port=8501 --server.address=0.0.0.0

# For background running, use screen or systemd
screen -S pdf-generator
streamlit run pdf_generator_ui.py --server.port=8501 --server.address=0.0.0.0
# Detach with Ctrl+A, D
```

### Option 2: Free Cloud Providers

#### Streamlit Cloud (EASIEST & FREE)
1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Deploy directly from your repository
5. **URL**: `https://yourapp.streamlit.app`

#### Render.com (FREE)
1. Create account at [render.com](https://render.com)
2. New > Web Service
3. Connect GitHub repo
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `streamlit run pdf_generator_ui.py --server.port=$PORT --server.address=0.0.0.0`

#### Railway.app (FREE trial)
1. Go to [railway.app](https://railway.app)
2. Deploy from GitHub
3. Add environment variable: `PORT=8501`
4. Deploy automatically

### Option 3: Local Network (Freebox/Home Server)

#### On Freebox Delta
```bash
# Create a VM with Ubuntu
# SSH into the VM
ssh vm@192.168.1.x

# Follow VPS deployment steps above
sudo ./deploy.sh

# Access from local network: http://192.168.1.x:8501
```

#### Port Forwarding for External Access
1. Freebox settings > Port forwarding
2. Forward port 8501 to your VM IP
3. Access: `http://your-public-ip:8501`

## 🔒 Security Recommendations

### Basic Security
```bash
# Use reverse proxy with nginx
sudo apt install nginx

# Create nginx config
sudo nano /etc/nginx/sites-available/pdf-generator

# Add:
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Enable and restart
sudo ln -s /etc/nginx/sites-available/pdf-generator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Add HTTPS with Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Add Basic Authentication
```bash
# Install apache2-utils
sudo apt install apache2-utils

# Create password file
sudo htpasswd -c /etc/nginx/.htpasswd username

# Add to nginx config:
auth_basic "Restricted Content";
auth_basic_user_file /etc/nginx/.htpasswd;
```

## 🐳 Docker Commands

```bash
# Start service
docker-compose up -d

# Stop service
docker-compose down

# View logs
docker-compose logs -f

# Restart service
docker-compose restart

# Update after code changes
docker-compose build
docker-compose up -d
```

## 🔧 Environment Variables

Create `.env` file for configuration:
```env
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_THEME_BASE=light
```

## 📊 System Requirements

- **Minimum**: 1 CPU, 512MB RAM
- **Recommended**: 2 CPU, 1GB RAM
- **Storage**: 500MB for app + space for PDFs
- **OS**: Linux (Ubuntu 20.04+ recommended)

## 🆓 Best Free Options

1. **Streamlit Cloud** - Easiest, no setup needed
2. **Render.com** - Good free tier, auto-deploy
3. **Your own PC** - Use ngrok for temporary public access:
   ```bash
   # Install ngrok
   brew install ngrok  # macOS
   # or download from ngrok.com

   # Run locally
   streamlit run pdf_generator_ui.py

   # In another terminal
   ngrok http 8501
   # Get public URL like: https://abc123.ngrok.io
   ```

## 📱 Mobile Access

The app is mobile-responsive. Access from any device with a browser at your deployment URL.

## 🔄 Backup Configurations

Saved configurations are stored in `saved_configs/` directory. Back them up regularly:
```bash
# Backup
tar -czf configs-backup-$(date +%Y%m%d).tar.gz saved_configs/

# Restore
tar -xzf configs-backup-20240101.tar.gz
```

## ❓ Troubleshooting

### Port already in use
```bash
# Find process using port 8501
lsof -i :8501
# Kill it
kill -9 <PID>
```

### Permission denied
```bash
# Fix permissions
sudo chown -R $USER:$USER .
chmod 755 saved_configs generated_pdfs
```

### Memory issues
Add swap if low on RAM:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```
