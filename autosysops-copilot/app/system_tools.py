# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Live system inspection tool for AutoSysOps Copilot."""

import os
import platform
import shutil
import subprocess
from typing import Any, Dict


def inspect_host_environment() -> Dict[str, Any]:
    """Inspects the local Linux host environment to gather real system facts.

    Detects the Linux distribution, kernel version, init system (systemd),
    available package managers and CLI tools, and root disk usage.

    Returns:
        Dict with OS distribution, tools available, and disk usage.
    """
    # 1. Distro info
    distro = "Linux (generic)"
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        distro = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass

    # 2. Available admin CLI tools
    tools = [
        t for t in [
            "apt", "dnf", "yum", "pacman", "systemctl",
            "journalctl", "crontab", "docker", "python3", "bash"
        ] if shutil.which(t)
    ]

    # 3. Root disk usage
    disk = "unknown"
    try:
        res = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            disk = res.stdout.strip().splitlines()[-1].split()[4]  # e.g. "22%"
    except Exception:
        pass

    return {
        "os": distro,
        "kernel": platform.release(),
        "arch": platform.machine(),
        "init_system": "systemd" if shutil.which("systemctl") else "other",
        "available_tools": tools,
        "root_disk_usage": disk,
    }
