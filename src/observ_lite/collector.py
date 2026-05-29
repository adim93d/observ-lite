"""Collect local hardware and OS observations."""

from __future__ import annotations

import csv
import io
import json
import platform
import shutil
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .commands import CommandResult, command_available, run_command, truncate_text
from .config import Config
from .files import append_jsonl, append_log_block, ensure_log_dir


Snapshot = Dict[str, Any]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_text_file(path: Path, max_chars: int) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "ok": False,
            "path": str(path),
            "output": "",
            "error": str(exc),
        }
    return {
        "ok": True,
        "path": str(path),
        "output": truncate_text(text, max_chars),
    }


def parse_os_release(text: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        parsed[key] = value
    return parsed


def collect_os_info(config: Config) -> Dict[str, Any]:
    os_release = read_text_file(Path("/etc/os-release"), config.max_output_chars)
    parsed_release = parse_os_release(os_release["output"]) if os_release["ok"] else {}
    return {
        "platform": platform.platform(),
        "kernel_version": platform.release(),
        "architecture": platform.machine(),
        "os_release": {
            "raw": os_release,
            "parsed": parsed_release,
        },
    }


def parse_proc_uptime(text: str) -> Dict[str, Any]:
    parts = text.split()
    if len(parts) < 2:
        return {"ok": False, "raw": text, "error": "unexpected /proc/uptime format"}
    try:
        return {
            "ok": True,
            "raw": text.strip(),
            "uptime_seconds": float(parts[0]),
            "idle_seconds": float(parts[1]),
        }
    except ValueError as exc:
        return {"ok": False, "raw": text, "error": str(exc)}


def parse_proc_loadavg(text: str) -> Dict[str, Any]:
    parts = text.split()
    if len(parts) < 3:
        return {"ok": False, "raw": text, "error": "unexpected /proc/loadavg format"}
    try:
        return {
            "ok": True,
            "raw": text.strip(),
            "load_1m": float(parts[0]),
            "load_5m": float(parts[1]),
            "load_15m": float(parts[2]),
        }
    except ValueError as exc:
        return {"ok": False, "raw": text, "error": str(exc)}


def collect_uptime_load(config: Config) -> Dict[str, Any]:
    proc_uptime = read_text_file(Path("/proc/uptime"), config.max_output_chars)
    proc_loadavg = read_text_file(Path("/proc/loadavg"), config.max_output_chars)
    return {
        "proc_uptime": (
            parse_proc_uptime(proc_uptime["output"]) if proc_uptime["ok"] else proc_uptime
        ),
        "proc_loadavg": (
            parse_proc_loadavg(proc_loadavg["output"]) if proc_loadavg["ok"] else proc_loadavg
        ),
        "uptime_command": run_command(
            ["uptime"],
            config.command_timeout,
            config.max_output_chars,
        ),
    }


def parse_meminfo(text: str) -> Dict[str, int]:
    values: Dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        parts = raw_value.strip().split()
        if not parts:
            continue
        try:
            values[key] = int(parts[0])
        except ValueError:
            continue
    return values


def collect_memory(config: Config) -> Dict[str, Any]:
    meminfo_file = read_text_file(Path("/proc/meminfo"), config.max_output_chars)
    if not meminfo_file["ok"]:
        return meminfo_file

    meminfo = parse_meminfo(meminfo_file["output"])
    total_kb = meminfo.get("MemTotal")
    available_kb = meminfo.get("MemAvailable")
    if total_kb is None or available_kb is None:
        return {
            "ok": False,
            "meminfo": meminfo,
            "error": "MemTotal or MemAvailable missing from /proc/meminfo",
        }

    used_kb = max(total_kb - available_kb, 0)
    return {
        "ok": True,
        "meminfo": meminfo,
        "total_mb": round(total_kb / 1024, 2),
        "available_mb": round(available_kb / 1024, 2),
        "used_mb": round(used_kb / 1024, 2),
        "used_percent": round((used_kb / total_kb) * 100, 2) if total_kb else 0,
    }


def collect_disk(config: Config) -> Dict[str, Any]:
    usage = shutil.disk_usage("/")
    findmnt = run_command(
        ["findmnt", "--json", "--real"],
        config.command_timeout,
        config.max_output_chars,
    )
    parsed_findmnt: Dict[str, Any] = {}
    if findmnt["ok"]:
        try:
            parsed_findmnt = json.loads(findmnt["output"])
        except json.JSONDecodeError as exc:
            parsed_findmnt = {"ok": False, "error": str(exc)}

    return {
        "root_filesystem": {
            "path": "/",
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "used_percent": round((usage.used / usage.total) * 100, 2) if usage.total else 0,
        },
        "lsblk": run_command(
            ["lsblk"],
            config.command_timeout,
            config.max_output_chars,
        ),
        "findmnt": {
            "command": findmnt,
            "json": parsed_findmnt,
        },
    }


def parse_proc_net_dev(text: str) -> Dict[str, Any]:
    interfaces: Dict[str, Dict[str, int]] = {}
    for line in text.splitlines()[2:]:
        if ":" not in line:
            continue
        name, raw_values = line.split(":", 1)
        values = raw_values.split()
        if len(values) < 16:
            continue
        try:
            interfaces[name.strip()] = {
                "rx_bytes": int(values[0]),
                "rx_packets": int(values[1]),
                "rx_errors": int(values[2]),
                "rx_drop": int(values[3]),
                "tx_bytes": int(values[8]),
                "tx_packets": int(values[9]),
                "tx_errors": int(values[10]),
                "tx_drop": int(values[11]),
            }
        except ValueError:
            continue
    return {"ok": True, "interfaces": interfaces}


def collect_network(config: Config) -> Dict[str, Any]:
    proc_net_dev = read_text_file(Path("/proc/net/dev"), config.max_output_chars)
    return {
        "proc_net_dev": (
            parse_proc_net_dev(proc_net_dev["output"]) if proc_net_dev["ok"] else proc_net_dev
        ),
        "ip_br_addr": run_command(
            ["ip", "-br", "addr"],
            config.command_timeout,
            config.max_output_chars,
        ),
        "ip_s_link": run_command(
            ["ip", "-s", "link"],
            config.command_timeout,
            config.max_output_chars,
        ),
    }


def collect_hardware(config: Config) -> Dict[str, Any]:
    return {
        "proc_cpuinfo": read_text_file(Path("/proc/cpuinfo"), config.max_output_chars),
        "lspci": run_command(
            ["lspci"],
            config.command_timeout,
            config.max_output_chars,
        ),
        "lsusb": run_command(
            ["lsusb"],
            config.command_timeout,
            config.max_output_chars,
        ),
    }


def collect_sensors(config: Config) -> Dict[str, Any]:
    if not command_available("sensors"):
        return {"ok": False, "error": "command not found: sensors"}

    json_result = run_command(
        ["sensors", "-j"],
        config.command_timeout,
        config.max_output_chars,
    )
    if json_result["ok"]:
        try:
            return {
                "ok": True,
                "format": "json",
                "command": json_result,
                "data": json.loads(json_result["output"]),
            }
        except json.JSONDecodeError as exc:
            plain_result = run_command(
                ["sensors"],
                config.command_timeout,
                config.max_output_chars,
            )
            return {
                "ok": plain_result["ok"],
                "format": "plain_text",
                "json_attempt": json_result,
                "command": plain_result,
                "error": "failed to parse sensors JSON: {0}".format(exc),
            }

    plain_result = run_command(
        ["sensors"],
        config.command_timeout,
        config.max_output_chars,
    )
    return {
        "ok": plain_result["ok"],
        "format": "plain_text",
        "json_attempt": json_result,
        "command": plain_result,
        "error": plain_result.get("error", json_result.get("error", "")),
    }


def _clean_number(value: str) -> Any:
    value = value.strip()
    if value in ("", "N/A", "[Not Supported]"):
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def parse_nvidia_csv(output: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    reader = csv.reader(io.StringIO(output))
    for row in reader:
        if len(row) < 6:
            continue
        rows.append(
            {
                "name": row[0].strip(),
                "temperature_c": _clean_number(row[1]),
                "utilization_percent": _clean_number(row[2]),
                "memory_used_mb": _clean_number(row[3]),
                "memory_total_mb": _clean_number(row[4]),
                "power_draw_w": _clean_number(row[5]),
            }
        )
    return rows


def collect_nvidia_gpu(config: Config) -> Dict[str, Any]:
    if not command_available("nvidia-smi"):
        return {"ok": False, "error": "command not found: nvidia-smi"}

    result = run_command(
        [
            "nvidia-smi",
            "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw",
            "--format=csv,noheader,nounits",
        ],
        config.command_timeout,
        config.max_output_chars,
    )
    if not result["ok"]:
        return {"ok": False, "command": result, "error": result.get("error", "")}

    return {
        "ok": True,
        "command": result,
        "gpus": parse_nvidia_csv(result["output"]),
    }


def detect_storage_devices() -> List[Dict[str, str]]:
    devices: List[Dict[str, str]] = []
    dev_dir = Path("/dev")
    try:
        nvme_devices = sorted(dev_dir.glob("nvme*n1"))
        sd_devices = sorted(dev_dir.glob("sd?"))
    except OSError:
        return devices

    for path in nvme_devices:
        devices.append({"path": str(path), "type": "nvme"})
    for path in sd_devices:
        devices.append({"path": str(path), "type": "sata_scsi"})
    return devices


def collect_storage_health(config: Config) -> Dict[str, Any]:
    devices = detect_storage_devices()
    results: List[Dict[str, Any]] = []
    for device in devices:
        path = device["path"]
        device_type = device["type"]
        if device_type == "nvme":
            command = ["nvme", "smart-log", path]
        else:
            command = ["smartctl", "-H", path]
        results.append(
            {
                "device": path,
                "type": device_type,
                "health": run_command(
                    command,
                    config.command_timeout,
                    config.max_output_chars,
                ),
            }
        )
    return {"ok": True, "devices": devices, "results": results}


def log_command_block(
    path: Path,
    timestamp: str,
    hostname: str,
    label: str,
    result: CommandResult,
) -> None:
    command = " ".join(result.get("command", []))
    title = "{0} host={1} label={2} ok={3} returncode={4} command={5}".format(
        timestamp,
        hostname,
        label,
        result.get("ok"),
        result.get("returncode"),
        command,
    )
    body_parts = []
    if result.get("output"):
        body_parts.append(str(result["output"]))
    if result.get("error"):
        body_parts.append("[error]\n{0}".format(result["error"]))
    append_log_block(path, title, "\n".join(body_parts))


def collect_warning_logs(config: Config, timestamp: str, hostname: str) -> Dict[str, Any]:
    os_warnings = run_command(
        ["journalctl", "-p", "warning..alert", "-n", "200", "--no-pager", "-o", "short-iso"],
        config.command_timeout,
        config.max_output_chars,
    )
    kernel_warnings = run_command(
        ["dmesg", "-T", "--level=err,warn"],
        config.command_timeout,
        config.max_output_chars,
    )

    log_command_block(
        config.log_dir / "os_warnings.log",
        timestamp,
        hostname,
        "journalctl_warning_alert",
        os_warnings,
    )
    log_command_block(
        config.log_dir / "kernel_warnings.log",
        timestamp,
        hostname,
        "dmesg_err_warn",
        kernel_warnings,
    )

    return {
        "os_warnings": os_warnings,
        "kernel_warnings": kernel_warnings,
    }


def collect_snapshot(config: Config) -> Snapshot:
    timestamp = utc_timestamp()
    hostname = socket.gethostname()

    snapshot: Snapshot = {
        "timestamp": timestamp,
        "hostname": hostname,
        "os": collect_os_info(config),
        "uptime_load": collect_uptime_load(config),
        "memory": collect_memory(config),
        "disk": collect_disk(config),
        "network": collect_network(config),
        "hardware": collect_hardware(config),
        "sensors": collect_sensors(config),
        "nvidia_gpu": collect_nvidia_gpu(config),
        "storage_health": collect_storage_health(config),
    }
    snapshot["warnings"] = collect_warning_logs(config, timestamp, hostname)
    return snapshot


def run_once(config: Config) -> Snapshot:
    ensure_log_dir(config.log_dir)
    snapshot = collect_snapshot(config)
    append_jsonl(config.log_dir / "system_snapshot.jsonl", snapshot)
    return snapshot
