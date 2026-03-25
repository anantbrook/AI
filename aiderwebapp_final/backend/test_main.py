import sys
from unittest.mock import MagicMock

# Mock out missing dependencies to allow importing main.py
sys.modules["fastapi"] = MagicMock()
sys.modules["fastapi.middleware.cors"] = MagicMock()
sys.modules["fastapi.staticfiles"] = MagicMock()
sys.modules["pydantic"] = MagicMock()
sys.modules["uvicorn"] = MagicMock()

import subprocess
from unittest.mock import patch
from main import run_cmd

def test_run_cmd_success():
    with patch("main.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="  hello world  \n", returncode=0)
        result = run_cmd(["echo", "hello world"])
        assert result == "hello world"
        mock_run.assert_called_once_with(["echo", "hello world"], cwd=None, capture_output=True, text=True, timeout=10)

def test_run_cmd_empty_output():
    with patch("main.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = run_cmd(["true"])
        assert result == ""

def test_run_cmd_exception():
    with patch("main.subprocess.run") as mock_run:
        mock_run.side_effect = Exception("error")
        result = run_cmd(["false"])
        assert result == ""

def test_run_cmd_timeout():
    with patch("main.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["sleep", "20"], timeout=10)
        result = run_cmd(["sleep", "20"], timeout=10)
        assert result == ""
