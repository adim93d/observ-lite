# observ-lite

observ-lite is a small Ubuntu observability MVP. It collects local hardware and OS information into append-only log files, using JSONL for structured snapshots and plain log files for journal and kernel warnings.

This is the first layer of a larger observability system. It intentionally avoids Docker, dashboards, external APIs, and alerting integrations.

## What It Collects

- Timestamp and hostname
- OS, kernel, architecture, and `/etc/os-release`
- Uptime, load average, and memory usage
- Root filesystem usage, block devices, and mount data
- Network interfaces and counters
- CPU, PCI, and USB hardware details
- Sensor output when `sensors` is installed
- NVIDIA GPU metrics when `nvidia-smi` is available
- NVMe and SATA/SCSI storage health when tools and permissions allow it
- Recent OS and kernel warnings

Missing optional commands are recorded as clean errors in the snapshot. A failed command should not crash the collector.

## Install Optional Ubuntu Packages

The collector uses only Python standard library code. These packages improve what it can observe:

```bash
sudo apt update
sudo apt install -y python3 lm-sensors smartmontools nvme-cli pciutils usbutils iproute2 procps logrotate
```

Optional sensor setup:

```bash
sudo sensors-detect --auto
```

## Run Once From This Repo

```bash
PYTHONPATH=src python3 -m observ_lite.main run-once
```

If `/var/log/observ-lite` is not writable by your current user, use a local log directory:

```bash
OBSERV_LITE_LOG_DIR=./logs PYTHONPATH=src python3 -m observ_lite.main run-once
```

The helper script does the same repo-local run:

```bash
scripts/run_once.sh
```

## Install Systemd Timer

```bash
sudo scripts/install_systemd.sh
```

The installer copies the project to `/opt/observ-lite`, creates `/var/log/observ-lite`, installs the systemd unit and timer, installs logrotate config, then enables and starts the timer.

Verify the timer:

```bash
systemctl status observ-lite.timer
systemctl list-timers observ-lite.timer
journalctl -u observ-lite.service -n 50 --no-pager
```

## View Logs

```bash
sudo tail -n 5 /var/log/observ-lite/system_snapshot.jsonl
sudo tail -n 80 /var/log/observ-lite/os_warnings.log
sudo tail -n 80 /var/log/observ-lite/kernel_warnings.log
```

Pretty-print the latest JSONL snapshot:

```bash
sudo tail -n 1 /var/log/observ-lite/system_snapshot.jsonl | python3 -m json.tool
```

## Uninstall Systemd Timer

```bash
sudo scripts/uninstall_systemd.sh
```

The uninstall script does not delete `/var/log/observ-lite` by default.

