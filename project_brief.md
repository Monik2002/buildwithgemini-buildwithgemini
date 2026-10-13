# My agent: AutoSysOps Copilot
One-liner: A conversational agent that helps IT professionals and sysadmins identify repetitive daily workflows, browse a catalog of tailored automation playbooks, and deep-dive into tested implementation scripts.

Tool coverage:
- Memory: User profile (role, Linux distros, cloud providers, scripting preferences, toolchain like Ansible/Bash/Python) and history of reviewed/adopted automations.
- Tools: Playbook search/retrieval tool, script generator, and syntax/dry-run validator.
- Catalog/UI: Catalog of automation opportunities (cards showing estimated time saved, complexity, prerequisite tools, and a deep-dive action).
- Image gen: Pipeline/workflow architecture diagrams for the automated process.
- Sandbox: Python/Bash code execution sandbox to test-run and verify automation scripts.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): code sandbox for script execution and verification, Cloud Trace for latency/monitoring

---

## Detailed Project Specification

### 1. Overview & User Journey
1. **Intake & Profiling**:
   - The user describes their daily routine (e.g., *"I manually check disk space, clean docker volumes, manage SSH keys, and tail logs across Ubuntu and RHEL instances"*).
   - The agent remembers environment details (distros, cloud providers, tools) in long-term memory.
2. **Opportunity Analysis & Catalog Rendering**:
   - The agent analyzes tasks and returns an interactive catalog of automation opportunities via **A2UI cards**.
   - Each card displays:
     - **Title** (e.g., *Automated Disk Space Alert & Cleanup*)
     - **Impact & ROI** (e.g., *Saves ~30 mins/day, Low Risk*)
     - **Tech Stack** (e.g., *Bash, Systemd Timer, Webhook*)
     - **Complexity Tier** (Quick Win / Intermediate / Advanced)
     - **Action**: "Deep Dive" trigger.
3. **Deep Dive & Implementation**:
   - Selecting a card generates a complete implementation guide:
     - Step-by-step setup instructions.
     - Production-ready scripts (Bash/Python/Ansible).
     - Security best practices & rollback plan.
4. **Validation & Visuals**:
   - **Code Sandbox**: Validates script syntax, executes safe dry-runs, and simulates edge cases.
   - **Image Generation**: Produces architecture diagrams depicting the trigger-to-alert flow.

---

### 2. Architecture & Workshop Tool Alignment

| Workshop Component | Implementation in AutoSysOps Copilot |
| :--- | :--- |
| **Sessions & Memory** | Tracks user role, Linux environment (distro, cloud, privileges), past automations explored, and preferred toolchains (e.g., Bash vs Python vs Ansible). |
| **Function Tools** | `search_playbooks(query, category)`: Fetches automation blueprints from the catalog.<br>`validate_script_syntax(code, shell)`: Checks script safety/syntax before execution.<br>`generate_playbook_deep_dive(playbook_id)`: Retrieves deep-dive specifications. |
| **Catalog & A2UI** | Renders structured cards for each discovered automation candidate with metadata chips, badges, and deep-dive action triggers. |
| **Code Sandbox** | Executes Bash/Python scripts in an isolated environment to test logic (e.g., log parsing regex, threshold calculation) and verify error handling. |
| **Image Generation** | Generates system workflow and architecture diagrams (e.g., Cron/Systemd -> Script -> Slack Webhook). |
| **Storage / RAG** | Pre-loaded catalog of common Linux/DevOps automation patterns (storage management, log hygiene, user provisioning, backup verification). |

---

### 3. Example Playbooks in Catalog
- **Playbook 1: Smart Disk Cleanup & Alerting**
  - *Tier*: Quick Win (Bash + Cron / Systemd Timer)
  - *Details*: Monitors partition thresholds, clears `/var/log` rotated files, and posts a webhook alert if usage remains critical.
- **Playbook 2: Automated SSH Key & User Offboarding**
  - *Tier*: Intermediate (Python + PAM / Authorized_Keys)
  - *Details*: Audits inactive accounts, rotates authorized keys, and archives user home folders.
- **Playbook 3: Service Health Watchdog & Auto-Remediation**
  - *Tier*: Intermediate (Systemd + Journalctl)
  - *Details*: Auto-restarts failing services with exponential backoff and emails crash dumps.
- **Playbook 4: Docker & Container Resource Garbage Collection**
  - *Tier*: Quick Win (Bash / Docker CLI)
  - *Details*: Periodically cleans dangling volumes, stopped containers, and untagged images with safety exclusions.
