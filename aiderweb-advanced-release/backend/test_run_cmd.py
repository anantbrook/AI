import sys
from unittest.mock import MagicMock

# --- Mocking missing dependencies before importing main ---
# This is necessary because main.py imports FastAPI, Pydantic, etc.
# at the module level, which are not installed in this environment.
class MockBaseModel:
    def dict(self):
        return {}

class MockFastAPI:
    def __init__(self, *args, **kwargs): pass
    def add_middleware(self, *args, **kwargs): pass
    def include_router(self, *args, **kwargs): pass
    def mount(self, *args, **kwargs): pass
    def websocket(self, *args, **kwargs):
        def decorator(func): return func
        return decorator

class MockAPIRouter:
    def __init__(self, *args, **kwargs): pass
    def get(self, *args, **kwargs):
        def decorator(func): return func
        return decorator
    def post(self, *args, **kwargs):
        def decorator(func): return func
        return decorator
    def delete(self, *args, **kwargs):
        def decorator(func): return func
        return decorator

# Register mocks in sys.modules to satisfy main.py imports
fastapi_mock = MagicMock()
fastapi_mock.FastAPI = MockFastAPI
fastapi_mock.APIRouter = MockAPIRouter
fastapi_mock.WebSocketDisconnect = type("WebSocketDisconnect", (Exception,), {})
sys.modules["fastapi"] = fastapi_mock
sys.modules["fastapi.middleware.cors"] = MagicMock()
sys.modules["fastapi.staticfiles"] = MagicMock()

pydantic_mock = MagicMock()
pydantic_mock.BaseModel = MockBaseModel
sys.modules["pydantic"] = pydantic_mock

sys.modules["uvicorn"] = MagicMock()
sys.modules["mss"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()

# --- End of Mocks ---

import unittest
from unittest.mock import patch, Mock
import subprocess
import os

# Ensure we can import main
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from main import run_cmd

class TestRunCmd(unittest.TestCase):
    @patch('subprocess.run')
    def test_run_cmd_success(self, mock_run):
        """Test that run_cmd correctly executes a command and strips output."""
        # Mock successful subprocess.run
        mock_run.return_value = Mock(stdout="  hello world  \n", returncode=0)

        result = run_cmd(["echo", "hello world"])

        self.assertEqual(result, "hello world")
        mock_run.assert_called_once_with(["echo", "hello world"], cwd=None, capture_output=True, text=True, timeout=10)

    @patch('subprocess.run')
    def test_run_cmd_with_cwd(self, mock_run):
        """Test that run_cmd respects the cwd (current working directory) argument."""
        mock_run.return_value = Mock(stdout="in dir", returncode=0)

        result = run_cmd(["ls"], cwd="/tmp")

        self.assertEqual(result, "in dir")
        mock_run.assert_called_once_with(["ls"], cwd="/tmp", capture_output=True, text=True, timeout=10)

    @patch('subprocess.run')
    def test_run_cmd_exception(self, mock_run):
        """Test that run_cmd returns an empty string when an exception occurs."""
        # Mock subprocess.run raising an exception
        mock_run.side_effect = Exception("Subprocess failed")

        result = run_cmd(["invalid_command"])

        self.assertEqual(result, "")

    @patch('subprocess.run')
    def test_run_cmd_timeout(self, mock_run):
        """Test that run_cmd handles subprocess.TimeoutExpired correctly."""
        mock_run.side_effect = subprocess.TimeoutExpired(["sleep", "20"], 10)

        result = run_cmd(["sleep", "20"], timeout=10)

        self.assertEqual(result, "")

    def test_run_cmd_real_echo(self):
        """Integration test with a real 'echo' command to verify stripping on the current OS."""
        # On POSIX, echo is an executable; on Windows, it is typically a shell builtin.
        # run_cmd uses subprocess.run(cmd) where cmd is a list, so shell=False (default).
        # This will work on Linux/macOS and should work on Windows if echo.exe exists or via shell.
        try:
            result = run_cmd(["echo", "test"])
            self.assertEqual(result, "test")
        except FileNotFoundError:
            # Skip if 'echo' is not found (e.g., bare Windows environment without echo.exe)
            self.skipTest("'echo' command not found on this system")

if __name__ == "__main__":
    # Prevent .pyc files from being created during test execution
    sys.dont_write_bytecode = True
    unittest.main()
