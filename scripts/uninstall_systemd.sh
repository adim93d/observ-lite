#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "uninstall_systemd.sh must be run as root. Try: sudo scripts/uninstall_systemd.sh" >&2
  exit 1
fi

systemctl stop observ-lite.timer 2>/dev/null || true
systemctl disable observ-lite.timer 2>/dev/null || true

rm -f /etc/systemd/system/observ-lite.service
rm -f /etc/systemd/system/observ-lite.timer
rm -f /etc/logrotate.d/observ-lite

systemctl daemon-reload
systemctl reset-failed observ-lite.service observ-lite.timer 2>/dev/null || true

cat <<'EOF'
observ-lite systemd timer uninstalled.

Logs were not deleted. To remove them manually:
  sudo rm -rf /var/log/observ-lite

Installed project files were not deleted. To remove them manually:
  sudo rm -rf /opt/observ-lite
EOF

