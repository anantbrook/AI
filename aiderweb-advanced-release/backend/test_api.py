import pytest
from fastapi.testclient import TestClient
from main import app
import os
import json
import tempfile
from pathlib import Path
import main

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def setup_mock_project():
    """Mock the PROJECTS_FILE to point to a temporary test directory."""
    temp_dir = tempfile.mkdtemp()

    # Store old file path
    old_proj_file = main.PROJECTS_FILE

    # Create mock projects.json pointing to our temp dir
    mock_proj_file = Path(tempfile.mkdtemp()) / "projects.json"
    mock_proj_file.write_text(json.dumps([{"name": "TestProject", "path": temp_dir}]))

    main.PROJECTS_FILE = mock_proj_file

    yield temp_dir

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
    shutil.rmtree(mock_proj_file.parent)
    main.PROJECTS_FILE = old_proj_file

def test_api_fs_list_valid_project(client, setup_mock_project):
    """Test listing files inside a registered project directory."""
    # create a file
    (Path(setup_mock_project) / "test.txt").write_text("hello")
    response = client.get(f"/api/fs/list?path={setup_mock_project}")
    assert response.status_code == 200
    assert "items" in response.json()

def test_api_fs_list_invalid_project(client, setup_mock_project):
    """Test attempting to read a path outside of registered projects."""
    invalid_path = "/etc" # An arbitrary path out of scope
    response = client.get(f"/api/fs/list?path={invalid_path}")
    assert response.status_code == 200
    assert "error" in response.json()
    assert "Access denied" in response.json()["error"]

def test_api_fs_read_write_invalid_project(client, setup_mock_project):
    """Test read/write API endpoints for path traversal/security."""
    # Write
    response = client.post("/api/fs/write", json={"path": "/tmp/hack.txt", "content": "bad"})
    assert response.status_code == 200
    assert "error" in response.json()
    assert "Access denied" in response.json()["error"]

    # Read
    response = client.get("/api/fs/read?path=/etc/passwd")
    assert response.status_code == 200
    assert "error" in response.json()
    assert "Access denied" in response.json()["error"]

def test_websocket_origin_rejection(client):
    """Ensure websocket blocks connection if Origin header is missing or incorrect."""
    with pytest.raises(Exception) as excinfo:
        with client.websocket_connect("/ws/terminal", headers={"Origin": "http://evil.com"}):
            pass
    # Starlette's TestClient raises a generic exception or WebSocketDisconnect when the server closes the connection during handshake
        # WebSocketDisconnect itself means it was rejected during handshake in TestClient
        assert excinfo.type.__name__ == "WebSocketDisconnect" or "403" in str(excinfo.value) or "1008" in str(excinfo.value)
