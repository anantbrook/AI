import asyncio
import json
import os
import sys
import socket
import subprocess
import urllib.request
import base64
import io
import traceback
import shutil
from pathlib import Path
from pydantic import BaseModel

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="AiderWeb")
origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

PROJECTS_FILE = Path.home() / ".aiderwebapp" / "projects.json"
DEFAULT_MODEL  = "ollama/qwen3-coder:480b-cloud"

# Shared skip set — used everywhere, defined once
SKIP = {'node_modules', '__pycache__', '.git', '.next', 'dist', 'build', '.venv', 'venv', '.cache'}


# ── Helpers ────────────────────────────────────
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def run_cmd(cmd, cwd=None, timeout=10):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except:
        return ""


# ── File System ────────────────────────────────
fs = APIRouter(prefix="/api/fs")

@fs.get("/list")
async def list_dir(path: str):
    try:
        p = Path(path)
        if not p.exists() or not p.is_dir():
            return {"error": "Not a directory"}
        items = []
        for item in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if item.name.startswith('.') or item.name in SKIP:
                continue
            items.append({
                "name":  item.name,
                "path":  str(item).replace("\\", "/"),
                "isDir": item.is_dir(),
                "ext":   item.suffix.lower()
            })
        return {"items": items}
    except Exception as e:
        return {"error": str(e)}

@fs.get("/read")
async def read_file(path: str):
    try:
        return {"content": Path(path).read_text(encoding="utf-8", errors="replace")}
    except Exception as e:
        return {"error": str(e)}

class WriteBody(BaseModel):
    path: str
    content: str

@fs.post("/write")
async def write_file(body: WriteBody):
    try:
        p = Path(body.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body.content, encoding="utf-8")
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}


# ── Projects ───────────────────────────────────
proj = APIRouter(prefix="/api/projects")

@proj.get("")
async def get_projects():
    try:
        if PROJECTS_FILE.exists():
            return json.loads(PROJECTS_FILE.read_text())
        return []
    except:
        return []

class Project(BaseModel):
    name: str
    path: str

@proj.post("")
async def save_projects(projects: list[Project]):
    PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROJECTS_FILE.write_text(json.dumps([p.dict() for p in projects]))
    return {"ok": True}


# ── Git ────────────────────────────────────────
git = APIRouter(prefix="/api/git")

@git.get("/status")
async def git_status(path: str):
    return {
        "branch": run_cmd(["git", "branch", "--show-current"], cwd=path),
        "status": run_cmd(["git", "status", "--short"],        cwd=path),
        "log":    run_cmd(["git", "log", "--oneline", "-8"],   cwd=path),
    }


# ── Models ─────────────────────────────────────
mdl = APIRouter(prefix="/api/models")

@mdl.get("")
async def get_models():
    """Return all installed models split into cloud vs local."""
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            data   = json.loads(r.read())
            all_m  = [m["name"] for m in data.get("models", [])]
            cloud  = [m for m in all_m if "cloud" in m]
            local  = [m for m in all_m if "cloud" not in m]
            return {"models": cloud + local, "cloud": cloud, "local": local, "online": True}
    except:
        # Ollama offline — return known cloud model names so UI still works
        cloud_fallback = [
            "qwen3-coder:480b-cloud",
            "deepseek-v3.1:671b-cloud",
            "gpt-oss:120b-cloud",
            "qwen3-coder:32b-cloud",
        ]
        return {"models": cloud_fallback, "cloud": cloud_fallback, "local": [], "online": False}

@mdl.delete("/local")
async def delete_local_models():
    """Delete all local (non-cloud) models to free disk space."""
    deleted, failed = [], []
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            data        = json.loads(r.read())
            local_names = [m["name"] for m in data.get("models", []) if "cloud" not in m["name"]]

        for name in local_names:
            result = subprocess.run(["ollama", "rm", name],
                                    capture_output=True, text=True, timeout=30)
            (deleted if result.returncode == 0 else failed).append(name)

        return {"ok": len(failed) == 0, "deleted": deleted, "failed": failed}
    except Exception as e:
        return {"ok": False, "error": str(e), "deleted": deleted, "failed": failed}


# ── Project Scan ───────────────────────────────
scan = APIRouter(prefix="/api/scan")

@scan.get("")
async def scan_project(path: str):
    try:
        p     = Path(path)
        files = []
        for f in p.rglob("*"):
            if f.is_file() and not any(s in f.parts for s in SKIP) and not f.name.startswith('.'):
                rel = str(f.relative_to(p)).replace("\\", "/")
                files.append({"path": rel, "size": f.stat().st_size, "ext": f.suffix})

        has   = {f["path"] for f in files}
        ptype = "unknown"
        if "package.json" in has and any(f.endswith((".jsx", ".tsx")) for f in has):
            ptype = "react"
        elif "package.json" in has:
            ptype = "nodejs"
        elif "requirements.txt" in has or any(f.endswith(".py") for f in has):
            ptype = "python"

        return {"files": files, "type": ptype, "count": len(files)}
    except Exception as e:
        return {"error": str(e)}


# ── Direct Ollama Agent (no Aider) ─────────────
# Like Codex: read all files ourselves → send to AI → parse edits → write to disk
# No Aider subprocess, no git dependency, no "please add files" nonsense.

TEXT_EXTS = {
    '.py','.js','.jsx','.ts','.tsx','.mjs','.cjs',
    '.html','.css','.scss','.sass','.less',
    '.json','.yaml','.yml','.toml','.ini','.env','.cfg','.conf',
    '.md','.txt','.rst','.xml','.svg',
    '.sh','.bat','.ps1','.cmd',
    '.sql','.prisma','.graphql',
    '.vue','.svelte','.astro',
    '.go','.rs','.java','.kt','.swift','.rb','.php','.c','.cpp','.h',
}
MAX_FILE_BYTES = 150_000   # skip files > 150 KB
MAX_TOTAL_CHARS = 180_000  # stay inside ~60k token context

SYSTEM_PROMPT = """You are AXIOM — an autonomous full-stack engineering agent running on the user's local machine. You have the same capabilities as Claude Code CLI and Codex CLI. You operate in a continuous agentic loop: think → plan → act → observe → repeat, until the task is fully complete.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORE IDENTITY & OPERATING PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are NOT a chatbot. You are an autonomous engineering agent.
- You DO NOT ask for permission to execute steps you already understand.
- You DO NOT explain what you are about to do and then wait. You DO IT.
- You DO NOT stop mid-task to check in unless you hit an ambiguity that would cause irreversible damage.
- You think in systems, not single files. Every change you make considers the whole project.
- You write code that ACTUALLY WORKS on first run, not code that "looks right."
- When something fails, you read the error, reason about the cause, fix it, and re-run. You do not give up after one attempt.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVAILABLE TOOLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You have FULL ACCESS to the following tools. To use them, output exactly one JSON object matching this schema per action:
{
  "tool": "tool_name",
  "args": { "arg_name": "value" }
}

1. run_command(cmd, shell)
   - Execute any bash / PowerShell / cmd command on the real local machine.
   - Examples: install packages, run servers, compile code, run test suites, git operations, move files, create directories.
   - shell options: "bash", "powershell", "cmd"
   - Always capture and read stdout + stderr before deciding next step.
   - Example JSON: {"tool": "run_command", "args": {"cmd": "npm install", "shell": "bash"}}

2. read_file(path)
   - Read the full contents of any file on the filesystem.
   - Use this before editing any file to understand current state.
   - Example JSON: {"tool": "read_file", "args": {"path": "src/index.js"}}

3. write_file(path, content)
   - Write (create or overwrite) a file at the given path.
   - Always write complete file contents. Never write partial files.
   - Example JSON: {"tool": "write_file", "args": {"path": "src/index.js", "content": "..."}}

4. edit_file(path, old_string, new_string)
   - Surgically replace a specific block of text in a file.
   - Use when you only need to change part of a large file.
   - old_string must be an exact match (copy from read_file first).
   - Example JSON: {"tool": "edit_file", "args": {"path": "src/index.js", "old_string": "const x = 1;", "new_string": "const x = 2;"}}

5. list_directory(path)
   - List all files and folders at the given path (recursive or shallow).
   - Use to map project structure before making changes.
   - Example JSON: {"tool": "list_directory", "args": {"path": "."}}

6. take_screenshot()
   - Capture the user's current screen as an image.
   - Use to verify UI changes, check running apps, or debug visual issues.
   - Returns a base64 image you can analyze.
   - Example JSON: {"tool": "take_screenshot", "args": {}}

7. search_files(path, pattern, file_extension)
   - Search for text patterns or filenames across the project.
   - Use to locate where a function is defined, find all imports, etc.
   - Example JSON: {"tool": "search_files", "args": {"path": ".", "pattern": "login", "file_extension": ".js"}}

8. delete_file(path)
   - Permanently delete a file. Use with caution.
   - Example JSON: {"tool": "delete_file", "args": {"path": "temp.txt"}}

9. create_directory(path)
   - Create a directory (and all parent directories).
   - Example JSON: {"tool": "create_directory", "args": {"path": "src/components"}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MULTI-AGENT ARCHITECTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are the COORDINATOR AGENT. For complex tasks, you will decompose the work and spawn SUB-AGENTS.
SUB-AGENT spawn format (emit this JSON to trigger parallel execution):
{
  "spawn_agents": [
    {
      "id": "agent_1",
      "task": "Rewrite the authentication module in /src/auth.js to use JWT. Read the file first, then implement refresh token logic.",
      "files_scope": ["/src/auth.js", "/src/middleware/authMiddleware.js"]
    }
  ]
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THINKING & REASONING PROTOCOL (High Reasoning Mode)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before acting on any non-trivial task, emit a THINK block:

<think>
GOAL: [What is the user actually trying to achieve?]
CURRENT STATE: [What does the filesystem/codebase look like right now?]
BLOCKERS: [What could go wrong? What are the failure modes?]
PLAN:
  Step 1 — [action + why]
  Step 2 — [action + why]
  Step N — [action + why]
PARALLELIZABLE: [Which steps can run in parallel via sub-agents?]
IRREVERSIBLE ACTIONS: [List any destructive steps. Flag them.]
</think>

The system will respond to your tool calls with:
<observe>
RESULT: [What did the tool return?]
STATUS: [success / partial / failed]
NEXT: [What do I do next based on this result?]
</observe>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Keep responses DENSE and ACTION-ORIENTED:
- Lead with actions taken, not explanations of what you're about to do.
- Show tool calls as raw JSON inline.
- After completing a task, give a 2-3 line summary of what was done and what changed.
- If the task is fully complete, end with: ✅ DONE — [one line summary]
- If you are mid-task and need to continue, end with: ⏳ CONTINUING — [next step]
- If you are blocked and need human input, end with: ❓ BLOCKED — [specific question]

Do NOT write essays. Do NOT over-explain. The user wants results."""

def capture_screenshot_base64() -> str:
    try:
        import mss
        from PIL import Image
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.thumbnail((1920, 1080))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=80)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        return ""


async def execute_tool(tool: str, args: dict, project_path: str, files_context: str):
    """Shared tool execution logic for both coordinator and sub-agents."""
    success = True
    result_str = ""
    event_payload = {"event": "tool", "text": f"🔧 Running {tool}..."}

    # Security: Ensure path is within project
    def get_safe_path(p: str) -> Path | None:
        try:
            target = Path(project_path, p).resolve()
            if not target.is_relative_to(Path(project_path).resolve()):
                return None
            return target
        except Exception:
            return None

    try:
        if tool == "run_command":
            cmd = args.get("cmd", "")
            shell_arg = args.get("shell", "bash").lower()
            event_payload = {"event": "cmd", "text": f"⚡ {shell_arg}: {cmd[:50]}..."}

            # Handle shell specifically
            if shell_arg == "powershell":
                run_cmd = ["powershell.exe", "-Command", cmd]
                shell_mode = False
            elif shell_arg == "cmd":
                run_cmd = ["cmd.exe", "/c", cmd]
                shell_mode = False
            else:
                run_cmd = cmd
                shell_mode = True

            res = await asyncio.to_thread(subprocess.run, run_cmd, shell=shell_mode, cwd=project_path, capture_output=True, text=True)
            out = res.stdout + res.stderr
            if not out.strip(): out = "[Command completed with no output]"
            result_str = out
            success = res.returncode == 0

        elif tool == "read_file":
            p = get_safe_path(args.get("path", ""))
            event_payload = {"event": "read", "text": f"📖 Read: {args.get('path')}"}
            if not p:
                result_str, success = "Error: Path traversal detected or invalid path.", False
            else:
                result_str = await asyncio.to_thread(p.read_text, encoding="utf-8", errors="replace")

        elif tool == "write_file":
            p = get_safe_path(args.get("path", ""))
            content = args.get("content", "")
            event_payload = {"event": "edit", "text": f"✏️ Write: {args.get('path')}"}
            if not p:
                result_str, success = "Error: Path traversal detected or invalid path.", False
            else:
                def do_write():
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(content, encoding="utf-8")
                await asyncio.to_thread(do_write)
                result_str = f"Successfully wrote {len(content)} bytes to {args.get('path')}."

        elif tool == "edit_file":
            p = get_safe_path(args.get("path", ""))
            old_str = args.get("old_string", "")
            new_str = args.get("new_string", "")
            event_payload = {"event": "edit", "text": f"✏️ Edit: {args.get('path')}"}
            if not p:
                result_str, success = "Error: Path traversal detected or invalid path.", False
            else:
                def do_edit():
                    fc = p.read_text(encoding="utf-8", errors="replace")
                    if old_str in fc:
                        p.write_text(fc.replace(old_str, new_str), encoding="utf-8")
                        return True
                    return False
                if await asyncio.to_thread(do_edit):
                    result_str = f"Successfully replaced block in {args.get('path')}."
                else:
                    result_str, success = "Error: old_string not found in file.", False

        elif tool == "list_directory":
            p = get_safe_path(args.get("path", "."))
            event_payload = {"event": "scan", "text": f"📂 List: {args.get('path', '.')}"}
            if not p:
                result_str, success = "Error: Path traversal detected or invalid path.", False
            else:
                def do_ls():
                    return "\n".join(f"{'DIR ' if i.is_dir() else 'FILE'} {i.name}" for i in p.iterdir())
                result_str = await asyncio.to_thread(do_ls)
                if not result_str: result_str = "[Empty directory]"

        elif tool == "take_screenshot":
            event_payload = {"event": "scan", "text": "📸 Taking screenshot..."}
            b64 = await asyncio.to_thread(capture_screenshot_base64)
            if b64:
                result_str = "Screenshot taken successfully. Check the image attachments."
                return success, result_str, event_payload, b64
            else:
                result_str, success = "Failed to take screenshot.", False

        elif tool == "search_files":
            pat = args.get("pattern", "")
            p = get_safe_path(args.get("path", "."))
            event_payload = {"event": "scan", "text": f"🔍 Search: {pat}"}
            if not p:
                result_str, success = "Error: Path traversal detected or invalid path.", False
            else:
                def do_search():
                    matches = []
                    for f in p.rglob("*"):
                        if f.is_file() and not any(s in f.parts for s in SKIP) and not f.name.startswith('.'):
                            try:
                                if pat in f.read_text(errors="ignore"):
                                    matches.append(str(f.relative_to(Path(project_path))))
                            except Exception: pass
                    return "\n".join(matches)
                result_str = await asyncio.to_thread(do_search)
                if not result_str: result_str = f"No matches for {pat}."

        elif tool == "delete_file":
            p = get_safe_path(args.get("path", ""))
            event_payload = {"event": "edit", "text": f"🗑️ Delete: {args.get('path')}"}
            if not p:
                result_str, success = "Error: Path traversal detected or invalid path.", False
            else:
                await asyncio.to_thread(p.unlink, missing_ok=True)
                result_str = f"Successfully deleted {args.get('path')}."

        elif tool == "create_directory":
            p = get_safe_path(args.get("path", ""))
            event_payload = {"event": "edit", "text": f"📁 Mkdir: {args.get('path')}"}
            if not p:
                result_str, success = "Error: Path traversal detected or invalid path.", False
            else:
                await asyncio.to_thread(p.mkdir, parents=True, exist_ok=True)
                result_str = f"Successfully created {args.get('path')}."

        else:
            result_str, success = f"Unknown tool: {tool}", False

    except Exception as e:
        result_str, success = f"Tool execution failed: {e}", False

    return success, result_str, event_payload, None


async def run_sub_agent(model: str, project_path: str, task: str, files_context: str):
    # Proper balanced brace JSON extraction
    def extract_json_objects(text):
        objects = []
        brace_count = 0
        start_idx = -1
        in_string = False
        escape = False

        for i, char in enumerate(text):
            if char == '"' and not escape:
                in_string = not in_string
            if in_string:
                if char == '\\' and not escape:
                    escape = True
                else:
                    escape = False
                continue

            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                if brace_count > 0:
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        objects.append(text[start_idx:i+1])
                        start_idx = -1
        return objects

    user_content = f"{files_context}\n\n---\nYOUR SUB-TASK: {task}"
    messages = [
        {"role": "system", "content": "You are a sub-agent assisting an expert autonomous software engineer. " + SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

    # Loop for sub-agent
    for _ in range(10):  # max 10 steps for sub-agent to prevent infinite loops
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 8192},
        }).encode()

        try:
            request = urllib.request.Request(
                "http://localhost:11434/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            def do_req():
                with urllib.request.urlopen(request, timeout=300) as response:
                    return json.loads(response.read())
            data = await asyncio.to_thread(do_req)
            content = data.get("message", {}).get("content", "")

            messages.append({"role": "assistant", "content": content})

            if "✅ DONE" in content:
                return {"task": task, "content": "Sub-agent successfully completed task."}
            if "❓ BLOCKED" in content:
                return {"task": task, "content": "Sub-agent is blocked."}

            action_results = []

            for json_str in extract_json_objects(content):
                try:
                    obj = json.loads(json_str)
                    if "tool" in obj and "args" in obj:
                        success, result_str, _, _ = await execute_tool(obj["tool"], obj["args"], project_path, files_context)
                        status_str = "success" if success else "failed"
                        action_results.append(f"<observe>\nRESULT for {obj['tool']}: {result_str}\nSTATUS: {status_str}\nNEXT: Analyze the result and continue.\n</observe>")
                except json.JSONDecodeError:
                    continue

            if not action_results:
                action_results.append("<observe>\nRESULT: No tool calls made.\nSTATUS: failed\nNEXT: Call a tool or output ✅ DONE.\n</observe>")

            messages.append({"role": "user", "content": "\n\n".join(action_results)})

        except Exception as e:
            return {"task": task, "error": str(e)}

    return {"task": task, "error": "Sub-agent reached max iterations."}



def read_project_files(project_path: str) -> tuple[str, list[str]]:
    """Read all text files in the project, return (context_string, file_list)."""
    p = Path(project_path)
    files_content = []
    file_list = []
    total_chars = 0

    # Priority order: config files first, then src files, then others
    all_files = []
    for f in p.rglob("*"):
        if not f.is_file(): continue
        if any(s in f.parts for s in SKIP): continue
        if f.name.startswith('.'): continue
        if f.suffix.lower() not in TEXT_EXTS: continue
        try:
            size = f.stat().st_size
            if size > MAX_FILE_BYTES: continue
            if size == 0: continue
        except: continue
        all_files.append(f)

    # Sort: config/root files first, then by path depth, then alphabetically
    def sort_key(f):
        rel = str(f.relative_to(p))
        depth = rel.count('/')
        is_config = f.suffix in ('.json', '.toml', '.yml', '.yaml', '.env', '.md')
        is_root = depth == 0
        return (0 if is_root else 1, 0 if is_config else 1, depth, rel)

    all_files.sort(key=sort_key)

    for f in all_files:
        if total_chars >= MAX_TOTAL_CHARS:
            break
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            rel = str(f.relative_to(p)).replace("\\", "/")
            entry = f"=== FILE: {rel} ===\n{content}\n"
            if total_chars + len(entry) > MAX_TOTAL_CHARS:
                # Include partial note
                files_content.append(f"=== FILE: {rel} === [truncated — file too large]\n")
                break
            files_content.append(entry)
            file_list.append(rel)
            total_chars += len(entry)
        except:
            continue

    return "\n".join(files_content), file_list

def apply_edits(project_path: str, ai_response: str) -> list[str]:
    """Parse <<<EDIT ... >>>END blocks from AI response and write to disk."""
    import re
    edited = []
    pattern = re.compile(r'<<<EDIT:\s*([^\n]+)\n(.*?)>>>END', re.DOTALL)

    for match in pattern.finditer(ai_response):
        rel_path = match.group(1).strip()
        content  = match.group(2)
        # Remove leading newline if present
        if content.startswith('\n'):
            content = content[1:]

        abs_path = Path(project_path) / rel_path
        try:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
            edited.append(rel_path)
        except Exception as e:
            pass  # logged via agent_event

    return edited

def strip_edits(response: str) -> str:
    """Remove <<<EDIT blocks from response for clean display."""
    import re
    clean = re.sub(r'<<<EDIT:[^\n]+\n.*?>>>END\n?', '', response, flags=re.DOTALL)
    return clean.strip()


# ── Agent WebSocket ────────────────────────────
@app.websocket("/ws/agent")
async def agent_ws(ws: WebSocket):
    origin = ws.headers.get("origin")
    if origin and origin not in origins:
        await ws.close(code=1008)
        return
    await ws.accept()
    stop_flag = asyncio.Event()

    async def send(type_, **kwargs):
        try:
            await ws.send_text(json.dumps({"type": type_, **kwargs}))
        except:
            pass

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            if msg["type"] == "stop":
                stop_flag.set()
                await send("stopped")
                continue

            if msg["type"] != "run":
                continue

            # ── Main agent run ─────────────────
            stop_flag.clear()
            project_path = msg["path"]
            model        = msg.get("model", DEFAULT_MODEL).replace("ollama/", "")
            message      = msg["message"]

            await send("agent_event", event="start", text=f"🤖 Starting AXIOM agent with {model}...")
            await send("agent_event", event="scan",  text=f"📂 Reading project: {Path(project_path).name}")

            files_context, file_list = await asyncio.to_thread(read_project_files, project_path)

            await send("agent_event", event="scan", text=f"📋 Loaded {len(file_list)} files into context")

            ollama_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{files_context}\n\n---\nUSER REQUEST: {message}"},
            ]

            # Autonomous loop
            while not stop_flag.is_set():
                await send("agent_event", event="think", text=f"🧠 Agent is thinking...")

                payload = json.dumps({
                    "model":    model,
                    "messages": ollama_messages,
                    "stream":   True,
                    "options":  {"temperature": 0.1, "num_predict": 8192},
                }).encode()

                full_response = ""
                current_chunk = ""

                try:
                    import urllib.request as req
                    request = req.Request(
                        "http://localhost:11434/api/chat",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )

                    with req.urlopen(request, timeout=300) as response:
                        for line in response:
                            if stop_flag.is_set():
                                break
                            line = line.decode("utf-8", errors="replace").strip()
                            if not line:
                                continue
                            try:
                                chunk_data = json.loads(line)
                                token = chunk_data.get("message", {}).get("content", "")
                                if token:
                                    full_response += token
                                    current_chunk += token

                                    # Stream to UI
                                    if len(current_chunk) > 50 or '\n' in current_chunk:
                                        if current_chunk:
                                            await send("chunk", text=current_chunk)
                                        current_chunk = ""

                                if chunk_data.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue

                except Exception as e:
                    await send("agent_event", event="error", text=f"⚠️ Ollama error: {str(e)}")
                    break

                if current_chunk:
                    await send("chunk", text=current_chunk)

                ollama_messages.append({"role": "assistant", "content": full_response})

                action_results = []
                next_msg = {"role": "user", "content": ""}

                # Check for "✅ DONE"
                if "✅ DONE" in full_response:
                    await send("agent_event", event="done", text="✅ Agent marked task as DONE.")
                    break
                elif "❓ BLOCKED" in full_response:
                    await send("agent_event", event="error", text="❓ Agent is BLOCKED and waiting for input.")
                    break

                # Extract and parse JSON tools or spawn_agents
                # Proper balanced brace JSON extraction
                def extract_json_objects(text):
                    objects = []
                    brace_count = 0
                    start_idx = -1
                    in_string = False
                    escape = False

                    for i, char in enumerate(text):
                        if char == '"' and not escape:
                            in_string = not in_string
                        if in_string:
                            if char == '\\' and not escape:
                                escape = True
                            else:
                                escape = False
                            continue

                        if char == '{':
                            if brace_count == 0:
                                start_idx = i
                            brace_count += 1
                        elif char == '}':
                            if brace_count > 0:
                                brace_count -= 1
                                if brace_count == 0 and start_idx != -1:
                                    objects.append(text[start_idx:i+1])
                                    start_idx = -1
                    return objects

                tools_run = 0
                for json_str in extract_json_objects(full_response):
                    try:
                        obj = json.loads(json_str)
                        if "tool" in obj and "args" in obj:
                            tools_run += 1
                            success, result_str, event_payload, b64 = await execute_tool(obj["tool"], obj["args"], project_path, files_context)

                            # Send events to UI
                            if event_payload:
                                await send("agent_event", **event_payload)
                            if obj["tool"] == "run_command":
                                await send("cmd_result", output=result_str, success=success)
                            if b64:
                                next_msg["images"] = [b64]

                            status_str = "success" if success else "failed"
                            action_results.append(f"<observe>\nRESULT for {obj['tool']}: {result_str}\nSTATUS: {status_str}\nNEXT: Analyze the result and continue.\n</observe>")

                        elif "spawn_agents" in obj:
                            agents = obj["spawn_agents"]
                            await send("agent_event", event="think", text=f"🤖 Spawning {len(agents)} Sub-Agents...")

                            aws = [run_sub_agent(model, project_path, a["task"], files_context) for a in agents]
                            sub_results = await asyncio.gather(*aws)

                            for res in sub_results:
                                if "error" in res:
                                    action_results.append(f"<observe>\nRESULT for Sub-Agent {res['task']}: FAILED ({res['error']})\nSTATUS: failed\nNEXT: Handle failure.\n</observe>")
                                else:
                                    action_results.append(f"<observe>\nRESULT for Sub-Agent {res['task']}:\n{res['content']}\nSTATUS: success\nNEXT: Integrate sub-agent results.\n</observe>")

                    except json.JSONDecodeError:
                        continue

                if tools_run == 0 and "spawn_agents" not in full_response and "✅ DONE" not in full_response and "❓ BLOCKED" not in full_response:
                    action_results.append("<observe>\nRESULT: No tool calls were made.\nSTATUS: failed\nNEXT: Please use a tool JSON to perform an action, or output ✅ DONE if you are finished, or ❓ BLOCKED if you need user input.\n</observe>")

                next_msg["content"] = "\n\n".join(action_results)
                ollama_messages.append(next_msg)

            if stop_flag.is_set():
                await send("agent_event", event="error", text="🛑 Agent stopped by user")

            await send("done", edited_files=[])

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        try: await send("error", text=str(e))
        except: pass

@app.websocket("/ws/terminal")
async def terminal_ws(ws: WebSocket):
    origin = ws.headers.get("origin")
    if origin and origin not in origins:
        await ws.close(code=1008)
        return
    await ws.accept()
    proc = None
    try:
        init  = json.loads(await ws.receive_text())
        cwd   = init.get("cwd", str(Path.home()))
        shell = "powershell.exe" if sys.platform == "win32" else "bash"

        proc = await asyncio.create_subprocess_exec(
            shell,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )

        await ws.send_text(json.dumps({"type": "ready"}))

        async def stream():
            while True:
                data = await proc.stdout.read(2048)
                if not data:
                    break
                await ws.send_text(json.dumps({
                    "type": "output",
                    "text": data.decode("utf-8", errors="replace")
                }))
        asyncio.create_task(stream())

        while True:
            msg = json.loads(await ws.receive_text())
            if msg["type"] == "input" and proc.stdin:
                proc.stdin.write(msg["text"].encode())
                await proc.stdin.drain()

    except WebSocketDisconnect:
        if proc:
            try: proc.kill()
            except: pass
    except Exception as e:
        try: await ws.send_text(json.dumps({"type": "error", "text": str(e)}))
        except: pass


# ── Register routers ───────────────────────────
app.include_router(fs)
app.include_router(proj)
app.include_router(git)
app.include_router(mdl)
app.include_router(scan)

# ── Serve built frontend ───────────────────────
frontend = Path(__file__).parent.parent / "frontend" / "dist"
if frontend.exists():
    app.mount("/", StaticFiles(directory=str(frontend), html=True), name="static")

if __name__ == "__main__":
    ip = get_ip()
    print("\n" + "="*52)
    print("  AiderWeb — Cloud AI Coding")
    print(f"  Local:    http://127.0.0.1:8000")
    print("="*52 + "\n")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False, log_level="warning")
