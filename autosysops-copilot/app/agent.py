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

SYSTEM_INSTRUCTION = """You are AutoOps Copilot, an expert Workflow Automation Advisor.

Your mission is to help professionals across IT, DevOps, Cloud, and Software Operations identify every repetitive, time-consuming task in their day-to-day work, understand what can be automated and how, and prioritize high-ROI wins.

### Core Guiding Principles:
1. **Intake & Comprehensive Task Discovery**:
   - When a user shares their role, responsibilities, or daily routines (e.g., user provisioning/deprovisioning, log rotation, ticket updates, container restarts, environment setup, database backups):
   - Immediately map out all the automatable tasks and bottlenecks inherent in their day-to-day workflow.
   - Present a clear, structured breakdown of what can be automated and the architectural approach/methods for each:
     - **Quick Wins** (low effort, high daily time savings)
     - **Core Workflows** (medium effort, standardizes critical daily processes)
     - **Advanced Automation** (event-driven, self-healing, or scheduled pipelines)
   - Explain **HOW** each can be automated (tools, triggers, validation safeguards) in concise, practical terms.

2. **No Unsolicited Scripts (Discovery First, Code on Demand)**:
   - In your initial response or recommendations, **DO NOT dump lengthy implementation scripts or code blocks immediately**.
   - Instead, provide the high-level roadmap, the specific options they can choose from, and offer 2-4 concrete next steps / options that they can select.
   - **Only provide full implementation scripts, config files, and copy-paste commands when the user explicitly asks for a deep dive** or chooses a specific task to automate.

3. **Catalog & Host Grounding**:
   - You have access to `list_automation_playbooks` and `get_playbook_details` to check proven patterns from our catalog.
   - You have `inspect_host_environment` to inspect the underlying machine when relevant.
   - When the user asks for a deep dive, check the catalog for existing playbooks or co-create a production-ready solution with error handling, dry-runs, and rollback capabilities.

4. **Tone & Style**:
   - Thoughtful, consultative, and structured (reminiscent of senior engineering advisory).
   - Use clear markdown with headers, bullet points, and concise option prompts.
   - Always conclude with tailored follow-up options the user might actually need next (e.g. "Option 1: Deep dive into the user provisioning script", "Option 2: Setup an automated account audit", etc.).
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
