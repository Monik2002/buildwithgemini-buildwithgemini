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

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
