#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   REPO_URL="git@github.com:owner/repo.git" DOMAIN="example.com" APP_USER="coeurdurisk" APP_DIR="/opt/coeurdurisk" APP_PORT="18000" ./scripts/vps_bootstrap.sh

REPO_URL="${REPO_URL:-}"
DOMAIN="${DOMAIN:-}"
APP_DIR="${APP_DIR:-/opt/coeurdurisk}"
APP_USER="${APP_USER:-coeurdurisk}"
APP_GROUP="${APP_GROUP:-${APP_USER}}"
APP_PORT="${APP_PORT:-18000}"

if [[ -z "${REPO_URL}" ]]; then
  echo "Erreur: REPO_URL est requis."
  exit 1
fi

sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git certbot python3-certbot-nginx

sudo mkdir -p "${APP_DIR}"
sudo chown -R "$USER:$USER" "${APP_DIR}"

if [[ ! -d "${APP_DIR}/.git" ]]; then
  git clone "${REPO_URL}" "${APP_DIR}"
else
  git -C "${APP_DIR}" pull
fi

cd "${APP_DIR}"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p logs
cp -n deploy/.env.production.example .env || true

if ! getent group "${APP_GROUP}" >/dev/null 2>&1; then
  sudo groupadd --system "${APP_GROUP}"
fi
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  sudo useradd --system --home "${APP_DIR}" --shell /usr/sbin/nologin --gid "${APP_GROUP}" "${APP_USER}"
fi
sudo chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}"

sudo sed \
  -e "s|__APP_USER__|${APP_USER}|g" \
  -e "s|__APP_GROUP__|${APP_GROUP}|g" \
  -e "s|__APP_DIR__|${APP_DIR}|g" \
  -e "s|__APP_PORT__|${APP_PORT}|g" \
  deploy/systemd/coeurdurisk.service | sudo tee /etc/systemd/system/coeurdurisk.service >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now coeurdurisk

SERVER_NAME="_"
if [[ -n "${DOMAIN}" ]]; then
  SERVER_NAME="${DOMAIN} www.${DOMAIN}"
fi
sudo sed \
  -e "s|__SERVER_NAME__|${SERVER_NAME}|g" \
  -e "s|__APP_PORT__|${APP_PORT}|g" \
  deploy/nginx/coeurdurisk.conf | sudo tee /etc/nginx/sites-available/coeurdurisk >/dev/null
sudo ln -sfn /etc/nginx/sites-available/coeurdurisk /etc/nginx/sites-enabled/coeurdurisk
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

if [[ -n "${DOMAIN}" ]]; then
  sudo certbot --nginx -d "${DOMAIN}" -d "www.${DOMAIN}" || true
fi

echo "Deploiement termine."
echo "Healthcheck: curl -I http://127.0.0.1:${APP_PORT}/api/health"

