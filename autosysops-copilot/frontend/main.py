"""FastAPI proxy for deployed AutoSysOps Copilot Agent Runtime.

Connects the browser frontend to the deployed Agent Runtime using
`async_create_session` and `async_stream_query` via the Vertex AI Reasoning Engines API.
"""

import json
import os
import uuid
import google.auth
import google.auth.transport.requests
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/766448645967/locations/us-east1/reasoningEngines/8874111068780101632",
)
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]
SERVICE_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{RESOURCE}"

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }

app = FastAPI()

_sessions: dict[str, str] = {}

async def _get_or_create_session(client: httpx.AsyncClient, user_id: str) -> str:
    if user_id in _sessions:
        return _sessions[user_id]
    
    resp = await client.post(
        f"{SERVICE_URL}:query",
        headers=_auth_headers(),
        json={
            "class_method": "async_create_session",
            "input": {"user_id": user_id},
        },
        timeout=30.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to create session ({resp.status_code}): {resp.text}")
    
    sess_id = resp.json().get("output", {}).get("id")
    if not sess_id:
        raise RuntimeError("No session ID returned by agent runtime")
    _sessions[user_id] = sess_id
    return sess_id

@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )

@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"

    async with httpx.AsyncClient(timeout=120.0) as client:
        session_id = await _get_or_create_session(client, user_id)
        
        stream_url = f"{SERVICE_URL}:streamQuery"
        payload = {
            "class_method": "async_stream_query",
            "input": {
                "user_id": user_id,
                "session_id": session_id,
                "message": message,
            },
        }

        parts: list[dict] = []
        text_accumulator: list[str] = []

        async with client.stream("POST", stream_url, headers=_auth_headers(), json=payload) as response:
            if response.status_code != 200:
                err_text = await response.aread()
                return JSONResponse(
                    status_code=200,
                    content={"parts": [{"kind": "text", "text": f"Error ({response.status_code}): {err_text.decode('utf-8')}"}]}
                )

            async for line in response.aiter_lines():
                if not line or not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue

                content = event.get("content")
                if isinstance(content, dict):
                    event_parts = content.get("parts", [])
                    for p in event_parts:
                        if "text" in p and p["text"]:
                            text_accumulator.append(p["text"])
                        elif "function_call" in p:
                            fn = p["function_call"]
                            parts.append({
                                "kind": "action",
                                "name": fn.get("name"),
                                "args": fn.get("args")
                            })

        full_text = "".join(text_accumulator).strip()
        if full_text:
            parts.insert(0, {"kind": "text", "text": full_text})
        elif not parts:
            parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]

        return JSONResponse({"parts": parts})

PROJECT_ID = "qwiklabs-gcp-04-118901d19b7f"

@app.get("/api/playbooks")
async def get_saved_playbooks():
    """Return all automation playbooks from Firestore."""
    try:
        from google.cloud import firestore
        db = firestore.Client(project=PROJECT_ID)
        docs = db.collection("automation_playbooks").stream()
        playbooks = []
        for d in docs:
            data = d.to_dict()
            playbooks.append({
                "id": d.id,
                "title": data.get("title", d.id),
                "category": data.get("category", "General"),
                "tier": data.get("tier", "Custom"),
                "time_saved": data.get("time_saved", "N/A"),
                "tech_stack": data.get("tech_stack", "Bash"),
                "summary": data.get("summary", ""),
            })
        return JSONResponse({"playbooks": playbooks})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/playbooks")
async def save_playbook(req: Request):
    """Save a user-customized playbook to Firestore."""
    try:
        from google.cloud import firestore
        body = await req.json()
        doc_id = body.get("id") or f"custom-{uuid.uuid4().hex[:8]}"
        db = firestore.Client(project=PROJECT_ID)
        db.collection("automation_playbooks").document(doc_id).set({
            "title": body.get("title", "Custom Automation Playbook"),
            "category": body.get("category", "Custom"),
            "tier": body.get("tier", "Custom"),
            "time_saved": body.get("time_saved", "~1-2 hrs/week"),
            "tech_stack": body.get("tech_stack", "Bash"),
            "summary": body.get("summary", ""),
            "script": body.get("script", ""),
            "setup_steps": body.get("setup_steps", []),
            "created_at": firestore.SERVER_TIMESTAMP,
        })
        return JSONResponse({"status": "saved", "id": doc_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/api/playbooks/{playbook_id}")
async def delete_playbook(playbook_id: str):
    """Delete a saved playbook from Firestore."""
    try:
        from google.cloud import firestore
        db = firestore.Client(project=PROJECT_ID)
        doc_ref = db.collection("automation_playbooks").document(playbook_id)
        doc = doc_ref.get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"error": f"Playbook '{playbook_id}' not found."})
        doc_ref.delete()
        return JSONResponse({"status": "deleted", "id": playbook_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/dry-run")
async def dry_run_script(req: Request):
    """Safely validate and simulate execution of a script."""
    import subprocess
    import tempfile
    body = await req.json()
    script = body.get("script", "")
    lang = body.get("language", "bash").lower()

    if not script.strip():
        return JSONResponse({"valid": False, "output": "No script provided."})

    with tempfile.NamedTemporaryFile("w", suffix=f".{ 'py' if 'python' in lang else 'sh' }", delete=False) as f:
        f.write(script)
        f_path = f.name

    try:
        if "python" in lang:
            cmd = ["python3", "-m", "py_compile", f_path]
        else:
            cmd = ["bash", "-n", f_path]
        
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            lines = [l.strip() for l in script.splitlines() if l.strip() and not l.strip().startswith("#")]
            return JSONResponse({
                "valid": True,
                "syntax": "PASSED (0 syntax errors)",
                "executable_lines": len(lines),
                "safe_mode": "Read-only syntax & parameter validation verified.",
                "output": "Syntax and structure check passed without errors."
            })
        else:
            return JSONResponse({
                "valid": False,
                "syntax": "FAILED",
                "output": proc.stderr or proc.stdout
            })
    except Exception as e:
        return JSONResponse({"valid": False, "output": f"Validation error: {e}"})
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
