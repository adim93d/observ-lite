#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "install_systemd.sh must be run as root. Try: sudo scripts/install_systemd.sh" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL_DIR="/opt/observ-lite"
LOG_DIR="/var/log/observ-lite"

install -d -m 755 "${INSTALL_DIR}"

cp -a "${REPO_ROOT}/README.md" "${INSTALL_DIR}/"
cp -a "${REPO_ROOT}/src" "${INSTALL_DIR}/"
cp -a "${REPO_ROOT}/config" "${INSTALL_DIR}/"
cp -a "${REPO_ROOT}/systemd" "${INSTALL_DIR}/"
cp -a "${REPO_ROOT}/logrotate" "${INSTALL_DIR}/"

install -d -m 750 -o root -g adm "${LOG_DIR}"
chown root:adm "${LOG_DIR}"
chmod 750 "${LOG_DIR}"

install -m 644 "${REPO_ROOT}/systemd/observ-lite.service" /etc/systemd/system/observ-lite.service
install -m 644 "${REPO_ROOT}/systemd/observ-lite.timer" /etc/systemd/system/observ-lite.timer
install -m 644 "${REPO_ROOT}/logrotate/observ-lite" /etc/logrotate.d/observ-lite

systemctl daemon-reload
systemctl enable --now observ-lite.timer

cat <<'EOF'
observ-lite systemd timer installed.

Useful status commands:
  systemctl status observ-lite.timer
  systemctl list-timers observ-lite.timer
  journalctl -u observ-lite.service -n 50 --no-pager
  sudo tail -n 5 /var/log/observ-lite/system_snapshot.jsonl
  sudo tail -n 80 /var/log/observ-lite/os_warnings.log
  sudo tail -n 80 /var/log/observ-lite/kernel_warnings.log
EOF

