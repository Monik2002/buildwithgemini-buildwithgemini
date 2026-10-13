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

"""Firestore backend tools for AutoSysOps Copilot.

Uses a hardcoded project ID string to ensure compatibility with Agent Platform
(avoiding google.auth.default() which returns the project number and breaks Firestore).
"""

from typing import Any, Dict, List, Optional
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-118901d19b7f"
COLLECTION_NAME = "automation_playbooks"


def _get_firestore_client() -> firestore.Client:
    """Return a Firestore client explicitly pinned to the string project ID."""
    return firestore.Client(project=PROJECT_ID)


def list_automation_playbooks(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List or filter automation playbooks from the Firestore catalog.

    Args:
        category: Optional category to filter playbooks by (e.g. 'Storage & Hygiene', 'Security & Access', 'Reliability & Uptime', 'Container Ops').

    Returns:
        A list of playbook summaries stored in Firestore.
    """
    try:
        db = _get_firestore_client()
        coll_ref = db.collection(COLLECTION_NAME)
        if category:
            query = coll_ref.where("category", "==", category)
            docs = query.stream()
        else:
            docs = coll_ref.stream()

        results = []
        for doc in docs:
            data = doc.to_dict()
            results.append({
                "id": doc.id,
                "title": data.get("title", ""),
                "category": data.get("category", ""),
                "tier": data.get("tier", ""),
                "time_saved": data.get("time_saved", ""),
                "tech_stack": data.get("tech_stack", ""),
                "summary": data.get("summary", ""),
                "prerequisites": data.get("prerequisites", ""),
            })
        return results if results else [{"message": "No playbooks found in this category."}]
    except Exception as e:
        return [{"error": f"Failed to query playbooks from Firestore: {str(e)}"}]


def get_playbook_details(playbook_id: str) -> Dict[str, Any]:
    """Retrieve full details, setup steps, and implementation script for a specific playbook.

    Args:
        playbook_id: The unique ID of the playbook (e.g. 'playbook-disk-cleanup').

    Returns:
        The full playbook document from Firestore including script and deep_dive_steps.
    """
    try:
        db = _get_firestore_client()
        doc_ref = db.collection(COLLECTION_NAME).document(playbook_id)
        doc = doc_ref.get()
        if not doc.exists:
            return {"error": f"Playbook '{playbook_id}' does not exist in Firestore."}
        return doc.to_dict()
    except Exception as e:
        return {"error": f"Failed to retrieve playbook '{playbook_id}': {str(e)}"}


def save_automation_playbook(
    playbook_id: str,
    title: str,
    category: str,
    tier: str,
    time_saved: str,
    tech_stack: str,
    summary: str,
    script: str,
    deep_dive_steps: List[str],
    prerequisites: str = "Bash, sudo",
) -> Dict[str, Any]:
    """Create or update a tailored automation playbook in Firestore.

    Args:
        playbook_id: Unique slug for the playbook (e.g. 'playbook-nginx-cache-purge').
        title: Title of the automation playbook.
        category: Operational category (e.g. 'Web Server Ops', 'Database Backup', 'Networking').
        tier: Complexity tier ('Quick Win', 'Intermediate', or 'Advanced').
        time_saved: Estimated operational time saved (e.g. '15 mins / day').
        tech_stack: Technologies used (e.g. 'Bash, Nginx CLI, Systemd').
        summary: Brief description of what the automation accomplishes.
        script: Full bash or python automation script.
        deep_dive_steps: Step-by-step instructions for installation and configuration.
        prerequisites: Required packages, tools, or permissions.

    Returns:
        Status confirmation of the saved playbook.
    """
    try:
        db = _get_firestore_client()
        doc_data = {
            "id": playbook_id,
            "title": title,
            "category": category,
            "tier": tier,
            "time_saved": time_saved,
            "tech_stack": tech_stack,
            "summary": summary,
            "script": script,
            "deep_dive_steps": deep_dive_steps,
            "prerequisites": prerequisites,
        }
        db.collection(COLLECTION_NAME).document(playbook_id).set(doc_data)
        return {"status": "success", "message": f"Playbook '{playbook_id}' saved successfully to Firestore."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to save playbook: {str(e)}"}
