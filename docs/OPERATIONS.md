# Operations

## Run Manually

From the repo:

```bash
PYTHONPATH=src python3 -m observ_lite.main run-once
```

Use a local log directory when running without permission to write under `/var/log`:

```bash
OBSERV_LITE_LOG_DIR=./logs PYTHONPATH=src python3 -m observ_lite.main run-once
```

The helper script runs the same command from the repo root:

```bash
scripts/run_once.sh
```

## Check Systemd Status

```bash
systemctl status observ-lite.timer
systemctl list-timers observ-lite.timer
systemctl status observ-lite.service
```

Run the service immediately:

```bash
sudo systemctl start observ-lite.service
```

## Inspect Generated Logs

```bash
sudo tail -n 5 /var/log/observ-lite/system_snapshot.jsonl
sudo tail -n 80 /var/log/observ-lite/os_warnings.log
sudo tail -n 80 /var/log/observ-lite/kernel_warnings.log
```

Pretty-print the latest snapshot:

```bash
sudo tail -n 1 /var/log/observ-lite/system_snapshot.jsonl | python3 -m json.tool
```

For local test logs:

```bash
tail -n 1 ./logs/system_snapshot.jsonl | python3 -m json.tool
tail -n 80 ./logs/os_warnings.log
tail -n 80 ./logs/kernel_warnings.log
```

## Troubleshoot Permissions

The default log directory is `/var/log/observ-lite`, normally owned by `root:adm` with mode `750`.

Check permissions:

```bash
sudo ls -ld /var/log/observ-lite
sudo ls -l /var/log/observ-lite
```

Repair expected permissions:

```bash
sudo chown root:adm /var/log/observ-lite
sudo chmod 750 /var/log/observ-lite
```

When running manually as a normal user, set `OBSERV_LITE_LOG_DIR=./logs`.

## Check Systemd Logs

```bash
journalctl -u observ-lite.service -n 100 --no-pager
journalctl -u observ-lite.timer -n 100 --no-pager
```

Some commands need root or kernel permissions. For example, `dmesg`, `smartctl`, and `nvme smart-log` can fail for an unprivileged manual run. Those failures should appear as error fields rather than crashing the collector.

