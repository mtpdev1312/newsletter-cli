# Hetzner Runbook: Newsletter CLI

## 1. Provision
- Create Ubuntu VM (22.04+)
- Create operator user with SSH key login
- Disable password auth in SSH config

## 2. Install
```bash
sudo APP_USER=mtpnews APP_DIR=/opt/mtp-newsletter REPO_DIR=/opt/mtp-newsletter/repo \
  bash /opt/mtp-newsletter/repo/services/newsletter_cli/deployment/install_hetzner.sh
```

## 3. Configure secrets
```bash
sudo nano /opt/mtp-newsletter/.env
sudo chmod 600 /opt/mtp-newsletter/.env
```
Required values:
- `MTP_API_USERNAME`
- `MTP_API_PASSWORD`
- `MTP_API_SERVICE_URL`

## 4. Initialize and warm up
```bash
sudo -u mtpnews bash -lc 'set -a && source /opt/mtp-newsletter/.env && set +a && /opt/mtp-newsletter/venv/bin/newsletter init'
sudo -u mtpnews bash -lc 'set -a && source /opt/mtp-newsletter/.env && set +a && /opt/mtp-newsletter/venv/bin/newsletter cache refresh'
```

## 5. Copy templates
Template naming convention:
- `<name>_de.html`
- `<name>_en.html`

Copy templates into `/opt/mtp-newsletter/templates`.

## 6. Enable timers
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now newsletter-cache-refresh.timer
sudo systemctl enable --now newsletter-backup.timer
sudo systemctl list-timers | grep newsletter
```

## 7. Generate from SSH
```bash
cat > /tmp/products.json << 'JSON'
[
  {"article_number": "MTP102004", "discount": 0, "quantity": 1}
]
JSON

sudo -u mtpnews bash -lc 'set -a && source /opt/mtp-newsletter/.env && set +a && \
  /opt/mtp-newsletter/venv/bin/newsletter generate --template basic --language de --products-file /tmp/products.json --pdf'
```

## 8. Retrieve files via SCP
```bash
scp user@server:/opt/mtp-newsletter/output/newsletter_de_YYYYMMDD_HHMMSS.html .
scp user@server:/opt/mtp-newsletter/output/newsletter_de_YYYYMMDD_HHMMSS.pdf .
```

## 9. Operations
Check recent runs:
```bash
sudo -u mtpnews bash -lc 'set -a && source /opt/mtp-newsletter/.env && set +a && /opt/mtp-newsletter/venv/bin/newsletter runs list --limit 20'
```

Show run details:
```bash
sudo -u mtpnews bash -lc 'set -a && source /opt/mtp-newsletter/.env && set +a && /opt/mtp-newsletter/venv/bin/newsletter runs show --id 1'
```

Manual backup:
```bash
sudo APP_DIR=/opt/mtp-newsletter /opt/mtp-newsletter/backup.sh
```
