#!/usr/bin/env python3
"""Seed script for AutoSysOps Copilot Firestore collection.

Hardcodes the project ID to avoid the Agent Platform project number issue.
"""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-118901d19b7f"
COLLECTION_NAME = "automation_playbooks"

SEED_DATA = [
    {
        "id": "playbook-disk-cleanup",
        "title": "Automated Smart Disk Cleanup & Alerting",
        "category": "Storage & Hygiene",
        "tier": "Quick Win",
        "time_saved": "30 mins / day",
        "tech_stack": "Bash, Systemd Timer, Webhook",
        "summary": "Monitors filesystem usage thresholds, safely trims journalctl/docker logs, and sends a webhook alert if critical capacity persists.",
        "prerequisites": "Bash 4+, root/sudo privilege, systemd",
        "script": """#!/usr/bin/env bash
set -euo pipefail

THRESHOLD=85
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
CURRENT_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')

echo "Current root partition usage: ${CURRENT_USAGE}% (Threshold: ${THRESHOLD}%)"

if [ "${CURRENT_USAGE}" -gt "${THRESHOLD}" ]; then
    echo "Usage exceeds threshold. Running safe cleanup..."
    journalctl --vacuum-time=3d
    if command -v apt-get &> /dev/null; then
        apt-get clean
    fi
    NEW_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    echo "Post-cleanup usage: ${NEW_USAGE}%"
    if [ "${NEW_USAGE}" -gt "${THRESHOLD}" ] && [ -n "${ALERT_WEBHOOK}" ]; then
        curl -s -X POST -H 'Content-type: application/json' \
            --data "{\\"text\\":\\"Disk usage alert on $(hostname): ${NEW_USAGE}% remains above threshold!\\"}" \
            "${ALERT_WEBHOOK}"
    fi
else
    echo "Disk usage within normal parameters."
fi
""",
        "deep_dive_steps": [
            "1. Save script to /usr/local/bin/disk-watchdog.sh and chmod +x.",
            "2. Create a systemd service unit: /etc/systemd/system/disk-watchdog.service.",
            "3. Create a systemd timer unit: /etc/systemd/system/disk-watchdog.timer scheduled every 4 hours.",
            "4. Enable and start: systemctl enable --now disk-watchdog.timer",
            "5. Test dry-run with threshold lowered to trigger notifications safely."
        ]
    },
    {
        "id": "playbook-ssh-audit",
        "title": "SSH Key & Inactive Account Auditor",
        "category": "Security & Access",
        "tier": "Intermediate",
        "time_saved": "2 hours / week",
        "tech_stack": "Python 3, PAM, Linux Shadow",
        "summary": "Audits local users for stale accounts (>60 days inactivity) and verifies authorized_keys permissions against security compliance baselines.",
        "prerequisites": "Python 3.9+, sudo/root access",
        "script": """#!/usr/bin/env python3
import os
import pwd
import spwd
import time
from pathlib import Path

MAX_IDLE_DAYS = 60
now = time.time()
inactive_users = []

print("Auditing user accounts for inactivity and SSH permissions...")

for user in pwd.getpwall():
    if user.pw_uid < 1000 or user.pw_name in ('nobody', 'systemd-coredump'):
        continue
    try:
        shadow_entry = spwd.getspnam(user.pw_name)
        last_change_days = shadow_entry.sp_lstchg
        if last_change_days and (now / 86400 - last_change_days) > MAX_IDLE_DAYS:
            inactive_users.append(user.pw_name)
    except KeyError:
        pass

    auth_keys = Path(user.pw_dir) / ".ssh" / "authorized_keys"
    if auth_keys.exists():
        mode = oct(auth_keys.stat().st_mode)[-3:]
        if mode not in ('600', '400'):
            print(f"[SECURITY ALERT] {user.pw_name}: {auth_keys} has loose permissions: {mode} (expected 600)")

print(f"Audit completed. Found {len(inactive_users)} potentially stale users: {inactive_users}")
""",
        "deep_dive_steps": [
            "1. Place script into /opt/security/ssh_audit.py.",
            "2. Configure an execution schedule via cron or systemd timer (weekly on Sunday at 02:00).",
            "3. Attach logging destination to syslog or send output to security alerting webhook.",
            "4. Verify exception list for service accounts with UID >= 1000."
        ]
    },
    {
        "id": "playbook-service-watchdog",
        "title": "Service Watchdog & Self-Healing Auto-Restart",
        "category": "Reliability & Uptime",
        "tier": "Quick Win",
        "time_saved": "45 mins / incident",
        "tech_stack": "Systemd Drop-ins, Journalctl",
        "summary": "Implements native systemd auto-restart policies with exponential backoff and crash dump notification handlers for critical daemons.",
        "prerequisites": "Systemd 230+",
        "script": """# /etc/systemd/system/myapp.service.d/restart.conf
[Service]
Restart=always
RestartSec=5s
RestartPreventExitStatus=SIGKILL
StartLimitIntervalSec=300
StartLimitBurst=5
ExecStopPost=/usr/local/bin/on-failure-alert.sh %n "%N service exited unexpectedly"
""",
        "deep_dive_steps": [
            "1. Create override directory: mkdir -p /etc/systemd/system/<service-name>.service.d/",
            "2. Create restart.conf with restart policy and backoff parameters.",
            "3. Add on-failure alerting hook script /usr/local/bin/on-failure-alert.sh.",
            "4. Reload systemd daemon: systemctl daemon-reload.",
            "5. Validate syntax: systemd-analyze verify <service-name>.service."
        ]
    },
    {
        "id": "playbook-docker-hygiene",
        "title": "Docker Container & Dangling Volume Hygiene",
        "category": "Container Ops",
        "tier": "Quick Win",
        "time_saved": "20 mins / day",
        "tech_stack": "Bash, Docker CLI, Cron",
        "summary": "Scheduled pruning of stopped containers older than 48h, untagged images, and dangling build caches without affecting running workloads.",
        "prerequisites": "Docker 20.10+",
        "script": """#!/usr/bin/env bash
set -euo pipefail

echo "Executing safe container hygiene sweep..."
# Remove stopped containers older than 48h
docker container prune -f --filter "until=48h"
# Remove dangling images
docker image prune -f --filter "dangling=true"
# Remove unused build cache older than 7 days
docker builder prune -f --filter "until=168h"

echo "Hygiene sweep completed."
docker system df
""",
        "deep_dive_steps": [
            "1. Add hygiene script to /etc/cron.daily/docker-prune or create a systemd timer.",
            "2. Ensure execution permissions: chmod 750 /etc/cron.daily/docker-prune.",
            "3. Review label exclusions for stateful or test containers if required."
        ]
    }
]


def seed():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection(COLLECTION_NAME)

    for item in SEED_DATA:
        doc_id = item["id"]
        collection.document(doc_id).set(item)
        print(f"✓ Seeded playbook: {doc_id} -> '{item['title']}'")

    print(f"\nSuccessfully seeded {len(SEED_DATA)} playbooks into '{COLLECTION_NAME}'!")


if __name__ == "__main__":
    seed()
