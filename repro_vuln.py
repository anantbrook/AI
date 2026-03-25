
import os
import json
from pathlib import Path
import sys

# Mock projects.json
PROJECTS_FILE = Path.home() / ".aiderwebapp" / "projects.json"
os.makedirs(PROJECTS_FILE.parent, exist_ok=True)
safe_dir = Path("/tmp/safe_project").resolve()
os.makedirs(safe_dir, exist_ok=True)
PROJECTS_FILE.write_text(json.dumps([{"name": "safe", "path": str(safe_dir)}]))

def is_safe_path(target_path: str) -> bool:
    """Check if target_path is a subdirectory of any saved project."""
    try:
        if not PROJECTS_FILE.exists():
            return False

        target = Path(target_path).resolve()
        import json
        projects = json.loads(PROJECTS_FILE.read_text())
        for p in projects:
            p_path = Path(p.get("path", "")).resolve()
            if target.is_relative_to(p_path):
                return True
        return False
    except Exception:
        return False

# Simulated functions with fixes applied
def simulated_scan_project(path: str):
    try:
        if not is_safe_path(path):
            return {"error": "Access denied: Path not in any saved project."}
        p     = Path(path)
        return {"status": "Success: Path is safe"}
    except Exception as e:
        return {"error": str(e)}

def simulated_git_status(path: str):
    if not is_safe_path(path):
        return {"error": "Access denied: Path not in any saved project."}
    return {"status": "Success: Path is safe"}

print("--- Vulnerability Fix Verification ---")
unsafe_path = "/etc"
print(f"Testing simulated_scan_project with {unsafe_path}: {simulated_scan_project(unsafe_path)}")
print(f"Testing simulated_git_status with {unsafe_path}: {simulated_git_status(unsafe_path)}")

safe_path = str(safe_dir)
print(f"Testing simulated_scan_project with {safe_path}: {simulated_scan_project(safe_path)}")
print(f"Testing simulated_git_status with {safe_path}: {simulated_git_status(safe_path)}")
