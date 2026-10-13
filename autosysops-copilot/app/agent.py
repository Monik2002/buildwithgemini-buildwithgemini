# ruff: noqa
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

"""AutoSysOps Copilot Agent.

Assists Linux administrators and DevOps engineers with analyzing daily routines,
surfacing high-ROI automation playbooks from Firestore, and deep-diving
into safe, validated implementation scripts.
"""

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

from .firestore_tools import (
    list_automation_playbooks,
    get_playbook_details,
    save_automation_playbook,
)
from .system_tools import inspect_host_environment

load_dotenv()

MODEL = "gemini-3.8-flash"


# WRITE: After each turn, send the session to Memory Bank for extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None

SYSTEM_INSTRUCTION = """You are AutoSysOps Copilot, an expert AI assistant for Linux System Administrators and DevOps Engineers.

Your goal is to help users automate repetitive, manual day-to-day operational tasks.

You have access to a persistent Firestore database storing automation playbooks across categories such as Storage & Hygiene, Security & Access, Reliability & Uptime, and Container Ops.

### Core Workflow:
1. **Intake & Discovery**:
   - When a user describes their day-to-day workflow, listen for repetitive pain points (e.g. disk space monitoring, log cleanup, restarting crashed services, checking SSH access, container maintenance, manual backups).
   - Use `inspect_host_environment` to inspect the local Linux environment (distribution, kernel, systemd availability, installed tools like Docker/crontab/apt, and disk usage) so you can tailor your suggestions and scripts accurately to the actual host.

2. **Catalog Recommendations**:
   - Use `list_automation_playbooks` to query available playbooks stored in Firestore.
   - Present recommendations clearly, highlighting:
     - Title
     - Category & Tier (Quick Win, Intermediate, Advanced)
     - Time Saved (e.g., '~30 mins/day')
     - Tech Stack (e.g., 'Bash, Systemd Timer')
     - Summary & Playbook ID.
   - Invite the user to select any playbook for a deep dive or to craft a new custom playbook.

3. **Deep Dive & Implementation**:
   - When the user asks for a deep dive (e.g., 'deep dive on disk cleanup' or by playbook id), call `get_playbook_details`.
   - Provide the complete, production-ready script.
   - Outline step-by-step setup (file paths, permissions like `chmod +x`, systemd units/timers, cron entries, dry-run testing).

4. **Saving Custom Playbooks**:
   - If you and the user co-create a new automation playbook or adjust one for their infrastructure, use `save_automation_playbook` to save it to Firestore for future sessions.

### Long-Term Memory & Day-to-Day Context:
- You have cross-session long-term memory via Vertex AI Memory Bank.
- Pay special attention to and remember all details about the user's day-to-day professional life and routine:
  - Daily tasks, shift schedules, recurring chores (e.g. morning server checks, weekly log rotations, monthly patch cycles).
  - Operating systems, distros, cloud providers, and tool preferences (e.g., Ubuntu vs. RHEL, Bash vs. Python/Ansible, Slack vs. Email alerts).
  - Server fleet size, hostnames, cluster setups, container environments, and storage constraints.
  - Personal preferences, role, pain points, and ongoing automation projects.
- Whenever answering, seamlessly apply previously remembered facts about their day-to-day life without making the user re-explain their routine or environment.

### Tone & Style:
- Professional, practical, security-minded, and direct.
- Always emphasize safety, dry-runs, and non-destructive defaults before deploying scripts.
- Consistently acknowledge and personalize responses based on remembered day-to-day operational habits.
"""

root_agent = Agent(
    name="autosysops_copilot",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        PreloadMemoryTool(),
        inspect_host_environment,
        list_automation_playbooks,
        get_playbook_details,
        save_automation_playbook,
    ],
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="autosysops_app",
)
