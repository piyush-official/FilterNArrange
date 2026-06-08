#!/usr/bin/env bash
# Plan H §T4 — bootstrap an Oracle Always-Free Ubuntu 22.04 host.
# Run once as root on the freshly-provisioned VM.
#
# Idempotent: re-runs are safe.

set -euo pipefail

DEPLOY_USER="filternarrange"
DATA_ROOT="/var/lib/filternarrange"
ETC_DIR="/etc/filternarrange"

echo "==> apt update + base packages"
apt-get update -y
apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg lsb-release \
    docker.io docker-compose-plugin \
    ufw fail2ban logrotate htop tzdata

echo "==> deploy user + docker group"
id "$DEPLOY_USER" >/dev/null 2>&1 || useradd -m -s /bin/bash "$DEPLOY_USER"
usermod -aG docker "$DEPLOY_USER"

echo "==> data dirs"
mkdir -p "$DATA_ROOT"/{postgres,redis,redpanda,minio,ollama,caddy-data,caddy-config}
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DATA_ROOT"
chmod 700 "$DATA_ROOT"

echo "==> /etc/filternarrange (env files)"
mkdir -p "$ETC_DIR"
chown root:root "$ETC_DIR"
chmod 750 "$ETC_DIR"
if [ ! -f "$ETC_DIR/prod.env" ]; then
    echo "    no prod.env — copy from infra/deploy/prod.env.example, fill in, chmod 0600"
fi

echo "==> ufw"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'ssh'
ufw allow 80/tcp comment 'http (acme + redirect)'
ufw allow 443/tcp comment 'https'
ufw --force enable

echo "==> systemd service"
cat > /etc/systemd/system/filternarrange.service <<'UNIT'
[Unit]
Description=FilterNArrange production stack
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=filternarrange
Group=filternarrange
WorkingDirectory=/home/filternarrange/FilterNArrange
EnvironmentFile=/etc/filternarrange/prod.env
ExecStart=/usr/bin/docker compose \
  -f infra/docker-compose/docker-compose.yml \
  -f infra/docker-compose/docker-compose.prod.yml \
  --env-file /etc/filternarrange/prod.env \
  up -d
ExecStop=/usr/bin/docker compose \
  -f infra/docker-compose/docker-compose.yml \
  -f infra/docker-compose/docker-compose.prod.yml \
  --env-file /etc/filternarrange/prod.env \
  down

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable filternarrange.service

echo "==> logrotate"
cat > /etc/logrotate.d/filternarrange <<'ROT'
/var/lib/docker/containers/*/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
ROT

echo "==> bootstrap complete"
echo "    next: clone repo as $DEPLOY_USER, populate $ETC_DIR/prod.env, run 'systemctl start filternarrange'"
