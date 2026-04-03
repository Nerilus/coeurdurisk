# Mise en production sur VPS (Ubuntu + Nginx + systemd)

Ce guide deploie l'application FastAPI derriere Nginx, avec un service `systemd`.

## 1) Prerequis VPS

- Ubuntu 22.04/24.04
- Un nom de domaine pointe vers le VPS (optionnel mais recommande)
- Un utilisateur non-root avec sudo (ex: `deploy`)

## 2) Installation systeme

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git
```

## 3) Recuperer le projet

```bash
sudo mkdir -p /opt/coeurdurisk
sudo chown -R $USER:$USER /opt/coeurdurisk
git clone <URL_DU_REPO> /opt/coeurdurisk
cd /opt/coeurdurisk
```

## 4) Environnement Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 5) Variables d'environnement

Copier et remplir le fichier d'exemple:

```bash
cp deploy/.env.production.example .env
nano .env
```

## 6) Service systemd

Copier le template:

```bash
APP_DIR=/opt/coeurdurisk
APP_USER=coeurdurisk
APP_GROUP=coeurdurisk
APP_PORT=18000

sudo groupadd --system ${APP_GROUP} || true
sudo useradd --system --home ${APP_DIR} --shell /usr/sbin/nologin --gid ${APP_GROUP} ${APP_USER} || true
sudo chown -R ${APP_USER}:${APP_GROUP} ${APP_DIR}

sudo sed \
  -e "s|__APP_USER__|${APP_USER}|g" \
  -e "s|__APP_GROUP__|${APP_GROUP}|g" \
  -e "s|__APP_DIR__|${APP_DIR}|g" \
  -e "s|__APP_PORT__|${APP_PORT}|g" \
  deploy/systemd/coeurdurisk.service | sudo tee /etc/systemd/system/coeurdurisk.service >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now coeurdurisk
sudo systemctl status coeurdurisk
```

Verifier l'API localement:

```bash
curl -I http://127.0.0.1:${APP_PORT}/api/health
```

## 7) Reverse proxy Nginx

```bash
SERVER_NAME="ton-domaine.tld www.ton-domaine.tld"
sudo sed \
  -e "s|__SERVER_NAME__|${SERVER_NAME}|g" \
  -e "s|__APP_PORT__|${APP_PORT}|g" \
  deploy/nginx/coeurdurisk.conf | sudo tee /etc/nginx/sites-available/coeurdurisk >/dev/null
sudo ln -s /etc/nginx/sites-available/coeurdurisk /etc/nginx/sites-enabled/coeurdurisk
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

## 8) HTTPS (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d ton-domaine.tld -d www.ton-domaine.tld
```

## 9) Mises a jour

```bash
cd /opt/coeurdurisk
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo chown -R coeurdurisk:coeurdurisk /opt/coeurdurisk
sudo systemctl restart coeurdurisk
```

## Commandes utiles

```bash
sudo journalctl -u coeurdurisk -n 200 --no-pager
sudo systemctl restart coeurdurisk
sudo systemctl restart nginx
```

