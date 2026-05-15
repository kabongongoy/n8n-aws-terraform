#!/bin/bash
set -euo pipefail

# ── Variables injected by Terraform ──────────────────────────────────────────
DOMAIN="${domain_name}"
N8N_USER="${n8n_basic_auth_user}"
N8N_PASS="${n8n_basic_auth_password}"

# ── System update ─────────────────────────────────────────────────────────────
apt-get update -y
apt-get upgrade -y
apt-get install -y \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  unzip \
  htop \
  ufw

# ── Docker ────────────────────────────────────────────────────────────────────
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl enable docker
systemctl start docker

# ── Caddy (reverse proxy + automatic HTTPS) ───────────────────────────────────
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  > /etc/apt/sources.list.d/caddy-stable.list
apt-get update -y
apt-get install -y caddy

# ── n8n data directory ────────────────────────────────────────────────────────
mkdir -p /opt/n8n/data
chown -R 1000:1000 /opt/n8n/data

# ── Docker Compose for n8n ────────────────────────────────────────────────────
cat > /opt/n8n/docker-compose.yml <<EOF
version: "3.8"

services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=$N8N_USER
      - N8N_BASIC_AUTH_PASSWORD=$N8N_PASS
      - N8N_HOST=$DOMAIN
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://$DOMAIN/
      - GENERIC_TIMEZONE=Australia/Brisbane
      - N8N_LOG_LEVEL=info
      - N8N_METRICS=true
    volumes:
      - /opt/n8n/data:/home/node/.n8n
    ports:
      - "5678:5678"
EOF

cd /opt/n8n && docker compose up -d

# ── Caddyfile ─────────────────────────────────────────────────────────────────
cat > /etc/caddy/Caddyfile <<EOF
$DOMAIN {
    reverse_proxy localhost:5678

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options nosniff
        X-Frame-Options SAMEORIGIN
        Referrer-Policy no-referrer-when-downgrade
    }

    encode gzip

    log {
        output file /var/log/caddy/n8n-access.log
        format json
    }
}
EOF

mkdir -p /var/log/caddy
systemctl enable caddy
systemctl restart caddy

# ── UFW firewall ──────────────────────────────────────────────────────────────
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# ── Automatic security updates ────────────────────────────────────────────────
apt-get install -y unattended-upgrades
dpkg-reconfigure --priority=low unattended-upgrades

echo "Bootstrap complete — n8n is starting at https://$DOMAIN"
