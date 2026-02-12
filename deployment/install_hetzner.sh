#!/usr/bin/env bash
set -euo pipefail

APP_USER="${APP_USER:-mtpnews}"
APP_DIR="${APP_DIR:-/opt/mtp-newsletter}"
REPO_DIR="${REPO_DIR:-$APP_DIR/repo}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root"
  exit 1
fi

apt update
apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  git \
  curl \
  ca-certificates \
  libpango-1.0-0 \
  libcairo2 \
  libgdk-pixbuf-2.0-0 \
  libffi-dev \
  fonts-dejavu-core

if ! id "${APP_USER}" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "${APP_USER}"
fi

mkdir -p "${APP_DIR}"/{data,templates,output,logs,backups}
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

if [[ ! -d "${REPO_DIR}" ]]; then
  echo "Expected repository at ${REPO_DIR}. Clone your repo there first."
  echo "Example: sudo -u ${APP_USER} git clone <repo-url> ${REPO_DIR}"
  exit 1
fi

sudo -u "${APP_USER}" python3 -m venv "${APP_DIR}/venv"
sudo -u "${APP_USER}" "${APP_DIR}/venv/bin/pip" install --upgrade pip
sudo -u "${APP_USER}" "${APP_DIR}/venv/bin/pip" install -r "${REPO_DIR}/services/newsletter_cli/requirements.txt"
sudo -u "${APP_USER}" "${APP_DIR}/venv/bin/pip" install "${REPO_DIR}/services/newsletter_cli"

if [[ ! -f "${APP_DIR}/.env" ]]; then
  cp "${REPO_DIR}/services/newsletter_cli/.env.example" "${APP_DIR}/.env"
  chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"
  chmod 600 "${APP_DIR}/.env"
  echo "Created ${APP_DIR}/.env. Fill in MTP credentials before cache refresh."
fi

install -m 0755 "${REPO_DIR}/services/newsletter_cli/deployment/backup.sh" "${APP_DIR}/backup.sh"
chown "${APP_USER}:${APP_USER}" "${APP_DIR}/backup.sh"

cp "${REPO_DIR}/services/newsletter_cli/deployment/systemd/newsletter-cache-refresh.service" /etc/systemd/system/
cp "${REPO_DIR}/services/newsletter_cli/deployment/systemd/newsletter-cache-refresh.timer" /etc/systemd/system/
cp "${REPO_DIR}/services/newsletter_cli/deployment/systemd/newsletter-backup.service" /etc/systemd/system/
cp "${REPO_DIR}/services/newsletter_cli/deployment/systemd/newsletter-backup.timer" /etc/systemd/system/

systemctl daemon-reload
systemctl enable newsletter-cache-refresh.timer
systemctl enable newsletter-backup.timer

sudo -u "${APP_USER}" bash -lc "set -a && source ${APP_DIR}/.env && set +a && ${APP_DIR}/venv/bin/newsletter init"

echo "Installation complete"
echo "Next steps:"
echo "1) Edit ${APP_DIR}/.env"
echo "2) Run initial warmup: sudo -u ${APP_USER} bash -lc 'set -a && source ${APP_DIR}/.env && set +a && ${APP_DIR}/venv/bin/newsletter cache refresh'"
echo "3) Start timers: systemctl start newsletter-cache-refresh.timer newsletter-backup.timer"
