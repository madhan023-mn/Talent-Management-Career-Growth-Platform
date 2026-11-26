#!/usr/bin/env bash
# ==============================================================================
# Talent Growth - 24/7 VPS Setup Script (Ubuntu/Debian)
# Provisions Python 3.11, Nginx, Certbot SSL, systemd, and cron backup job.
# ==============================================================================
set -e

echo "Starting automated VPS provisioning for Talent Growth Platform..."

APP_DIR="/var/www/talent-growth"
DOMAIN_NAME="${1:-}"

if [ -z "$DOMAIN_NAME" ]; then
    echo "Usage: sudo bash deploy/setup_vps.sh <your-domain-or-ip>"
    echo "Example: sudo bash deploy/setup_vps.sh app.talentgrowth.com"
    exit 1
fi

# 1. Update OS packages and install dependencies
echo "[1/6] Installing system packages..."
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx sqlite3 curl ufw

# 2. Configure Firewall (UFW)
echo "[2/6] Configuring firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# 3. Setup Application Directory and Virtualenv
echo "[3/6] Setting up application directory..."
mkdir -p "$APP_DIR/data/backups"
cp -r . "$APP_DIR/"
chown -R www-data:www-data "$APP_DIR"

cd "$APP_DIR"
python3 -m venv .venv
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r requirements.txt

# 4. Configure systemd Service
echo "[4/6] Installing systemd service..."
cp "$APP_DIR/deploy/systemd/talent-growth.service" /etc/systemd/system/talent-growth.service
systemctl daemon-reload
systemctl enable talent-growth
systemctl restart talent-growth

# 5. Configure Nginx
echo "[5/6] Configuring Nginx reverse proxy..."
sed -i "s/server_name .*/server_name $DOMAIN_NAME;/" "$APP_DIR/deploy/nginx/talent-growth.conf"
cp "$APP_DIR/deploy/nginx/talent-growth.conf" "/etc/nginx/sites-available/$DOMAIN_NAME"
ln -sf "/etc/nginx/sites-available/$DOMAIN_NAME" "/etc/nginx/sites-enabled/"
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

# 6. Setup Automated Daily Database Backup Cron Job
echo "[6/6] Installing automated daily backup cron job..."
CRON_JOB="0 2 * * * www-data $APP_DIR/.venv/bin/python $APP_DIR/scripts/db_backup.py --backup >> /var/log/talent_growth_backup.log 2>&1"
echo "$CRON_JOB" > /etc/cron.d/talent_growth_backup
chmod 644 /etc/cron.d/talent_growth_backup

echo "========================================================"
echo "Deployment Complete!"
echo "Status: Running on http://$DOMAIN_NAME"
echo "To enable Free Let's Encrypt SSL, run:"
echo "  sudo certbot --nginx -d $DOMAIN_NAME"
echo "========================================================"
