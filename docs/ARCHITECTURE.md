# Architecture

observ-lite is a local-first log creation MVP for Ubuntu hosts.

## Collector

The Python collector is the only active component in this MVP. It runs once, gathers a snapshot of OS and hardware state, appends structured JSON to `system_snapshot.jsonl`, and appends warning blocks to plain log files.

The collector is split into small modules:

- `main.py`: argparse CLI entrypoint
- `config.py`: environment-based runtime configuration
- `commands.py`: safe subprocess wrapper for all external commands
- `files.py`: append-only JSONL and log helpers
- `collector.py`: collection logic and parsers

External commands are optional. If tools like `nvidia-smi`, `sensors`, `smartctl`, or `nvme` are missing or fail, their failures are recorded in the snapshot instead of crashing the run.

## Log Files

The default log directory is:

```text
/var/log/observ-lite
```

It contains:

- `system_snapshot.jsonl`: one JSON object per collector run
- `os_warnings.log`: timestamped `journalctl` warning/error blocks
- `kernel_warnings.log`: timestamped `dmesg` warning/error blocks

JSONL keeps snapshots easy to parse later with Python, shell tools, SQLite import jobs, or a future analyzer service.

## Systemd Timer

The systemd service is a oneshot unit that runs:

```bash
/usr/bin/python3 -m observ_lite.main run-once
```

The timer starts two minutes after boot, then runs every five minutes with `Persistent=true` so missed runs can be caught after downtime.

## Logrotate

The logrotate config rotates both `.log` and `.jsonl` files under `/var/log/observ-lite`. Rotation is intentionally simple and local.

## Future Layers

This MVP only creates logs. Future layers can build on top of those logs:

- Analyzer: read snapshots and detect thresholds or anomalies
- Alerts: send summarized events to Discord or another channel
- Dashboard: expose recent state and trends
- Service monitor: track trading bot service health
- Watchdog and power controls: integrate Raspberry Pi watchdog and Wake-on-LAN

