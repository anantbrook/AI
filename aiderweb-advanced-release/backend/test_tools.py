import asyncio
import os
import shutil
import tempfile
import pytest
from pathlib import Path

# Import the tool logic from the backend
# We'll need to patch sys.path so we can import from main.py without changing directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from main import execute_tool

@pytest.fixture
def project_dir():
    """Create a temporary directory for testing filesystem tools."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_write_and_read_file(project_dir):
    """Test creating a file and reading it back."""
    test_file = "hello.txt"
    content = "Hello World!"

    # Test write_file
    args = {"path": test_file, "content": content}
    success, result, event, b64 = await execute_tool("write_file", args, project_dir, "")
    assert success is True
    assert "Successfully wrote" in result

    # Test read_file
    args = {"path": test_file}
    success, result, event, b64 = await execute_tool("read_file", args, project_dir, "")
    assert success is True
    assert result == content

@pytest.mark.asyncio
async def test_path_traversal_prevention(project_dir):
    """Test that path traversal (../) fails and doesn't write outside project_dir."""
    malicious_path = "../escaped_file.txt"
    content = "You've been hacked!"

    args = {"path": malicious_path, "content": content}
    success, result, event, b64 = await execute_tool("write_file", args, project_dir, "")
    assert success is False
    assert "Error: Path traversal" in result

@pytest.mark.asyncio
async def test_edit_file(project_dir):
    """Test targeted surgical string replacement in a file."""
    test_file = "code.js"
    initial_content = "const x = 1;\\nconsole.log(x);"
    p = Path(project_dir) / test_file
    p.write_text(initial_content)

    # Valid replacement
    args = {"path": test_file, "old_string": "const x = 1;", "new_string": "const x = 2;"}
    success, result, event, b64 = await execute_tool("edit_file", args, project_dir, "")
    assert success is True
    assert "Successfully replaced" in result
    assert p.read_text() == "const x = 2;\\nconsole.log(x);"

    # Invalid replacement (string not found)
    args = {"path": test_file, "old_string": "const y = 3;", "new_string": "const y = 4;"}
    success, result, event, b64 = await execute_tool("edit_file", args, project_dir, "")
    assert success is False
    assert "Error: old_string not found" in result

@pytest.mark.asyncio
async def test_create_and_list_directory(project_dir):
    """Test mkdir and listing its contents."""
    dir_name = "src/components"
    args = {"path": dir_name}

    success, result, event, b64 = await execute_tool("create_directory", args, project_dir, "")
    assert success is True
    assert "Successfully created" in result
    assert (Path(project_dir) / dir_name).is_dir()

    # Create a dummy file to list
    (Path(project_dir) / "src" / "index.js").write_text("hello")

    args = {"path": "src"}
    success, result, event, b64 = await execute_tool("list_directory", args, project_dir, "")
    assert success is True
    assert "DIR  components" in result or "DIR components" in result
    assert "FILE index.js" in result

@pytest.mark.asyncio
async def test_search_files(project_dir):
    """Test file search functionality."""
    p = Path(project_dir)
    p.joinpath("file1.txt").write_text("Hello there")
    p.joinpath("file2.js").write_text("const hello = 'world';")
    p.joinpath("secret.txt").write_text("Super secret password")

    args = {"pattern": "hello", "path": "."}
    success, result, event, b64 = await execute_tool("search_files", args, project_dir, "")
    assert success is True
    assert "file2.js" in result

@pytest.mark.asyncio
async def test_run_command_bash(project_dir):
    """Test basic bash command execution."""
    args = {"cmd": "echo 'Testing 123'", "shell": "bash"}
    success, result, event, b64 = await execute_tool("run_command", args, project_dir, "")
    assert success is True
    assert "Testing 123" in result

@pytest.mark.asyncio
async def test_run_command_powershell(project_dir):
    """Test powershell command formatting."""
    # We can't strictly guarantee powershell exists on the docker container running this test,
    # but we can verify it doesn't crash Python and attempts execution.
    args = {"cmd": "Write-Output 'PowerShell Test'", "shell": "powershell"}
    success, result, event, b64 = await execute_tool("run_command", args, project_dir, "")
    # Whether it succeeds depends on the host OS having pwsh/powershell installed,
    # but the execution logic should process it without raising a python exception.
    assert result is not None

@pytest.mark.asyncio
async def test_missing_args(project_dir):
    """Ensure missing args don't crash the loop but return an error string."""
    success, result, event, b64 = await execute_tool("write_file", {}, project_dir, "")
    # Missing args usually result in defaulting to "" or raising an error depending on the tool implementation
    # Currently write_file handles empty paths safely by defaulting to '' and then path traversal check catches it as safe
    # but write fails if it tries to write to a directory vs file.
    # Here, writing to '' evaluates to writing to the project root, which is a directory.
    assert success is False
    assert "Is a directory" in result or "Permission denied" in result or "Invalid" in result or "invalid path" in result.lower()

@pytest.mark.asyncio
async def test_delete_file(project_dir):
    """Test deleting an existing file."""
    test_file = "trash.txt"
    p = Path(project_dir) / test_file
    p.write_text("garbage")

    args = {"path": test_file}
    success, result, event, b64 = await execute_tool("delete_file", args, project_dir, "")
    assert success is True
    assert not p.exists()
