#!/usr/bin/env bash
# First-time setup on a fresh Ubuntu 24.04/25.04 OVH VPS.
# Run as root (or with sudo) from the repository root.
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/rag-platform}"
SECRETS_DIR="/etc/rag-platform"
SECRETS_FILE="$SECRETS_DIR/secrets.env"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo bash infra/prod/scripts/first-setup.sh)" >&2
  exit 1
fi

echo "==> apt update & upgrade"
apt-get update
apt-get upgrade -y

echo "==> installing base packages"
apt-get install -y --no-install-recommends \
  ca-certificates curl git ufw fail2ban unattended-upgrades \
  tzdata jq

echo "==> installing docker engine + compose plugin"
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

echo "==> configuring ufw (22/80/443 only)"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> enabling unattended security upgrades"
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "==> cloning / updating repository into ${REPO_DIR}"
if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "   REPO_DIR=${REPO_DIR} is not a git checkout."
  echo "   Clone it manually, then re-run this script. Example:"
  echo "     sudo git clone https://github.com/Guillaume7625/rag-platform.git ${REPO_DIR}"
  exit 1
fi
git -C "$REPO_DIR" pull --ff-only

echo "==> creating secrets dir at ${SECRETS_DIR}"
mkdir -p "$SECRETS_DIR"
chmod 750 "$SECRETS_DIR"
if [[ ! -f "$SECRETS_FILE" ]]; then
  cp "$REPO_DIR/infra/prod/secrets.env.example" "$SECRETS_FILE"
  chmod 600 "$SECRETS_FILE"
  chown root:root "$SECRETS_FILE"
  echo
  echo "   A template has been placed at ${SECRETS_FILE}."
  echo "   Edit it now and fill in every REPLACE_ME before continuing:"
  echo "     sudo nano ${SECRETS_FILE}"
  echo
  echo "   Useful generators:"
  echo "     openssl rand -base64 32   # postgres / minio passwords"
  echo "     openssl rand -hex 64      # JWT_SECRET"
  echo
  echo "   Once the file is ready, run:"
  echo "     sudo bash ${REPO_DIR}/infra/prod/scripts/deploy.sh"
  exit 0
fi

echo "==> installing systemd unit"
install -m 644 "$REPO_DIR/infra/prod/systemd/rag-platform.service" /etc/systemd/system/rag-platform.service
systemctl daemon-reload
systemctl enable rag-platform.service

echo
echo "All set. Run: sudo bash ${REPO_DIR}/infra/prod/scripts/deploy.sh"
