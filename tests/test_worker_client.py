"""Layer 2: IPC protocol tests for WorkerClient — mock subprocess, test behavior."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import json
import subprocess
from tools.worker_client import WorkerClient


@pytest.fixture
def mock_popen():
    """Create a mock Popen process."""
    proc = MagicMock()
    proc.poll.return_value = None  # process alive
    proc.stdin = MagicMock()
    proc.stdout = MagicMock()
    proc.returncode = None
    return proc


def test_start_success(mock_popen):
    """Worker sends ready signal → start() returns True."""
    mock_popen.stdout.readline.return_value = json.dumps({"status": "ready"}) + "\n"
    with patch("subprocess.Popen", return_value=mock_popen):
        client = WorkerClient("model.bin", "config.cfg", timeout=1.0)
        assert client.start() == True


def test_start_timeout(mock_popen):
    """Worker silent → start() returns False."""
    mock_popen.stdout.readline.return_value = ""  # simulate timeout via empty
    # Use a very short timeout to trigger the threading timeout
    with patch("subprocess.Popen", return_value=mock_popen):
        client = WorkerClient("model.bin", "config.cfg", timeout=0.001)
        # The readline will return empty string, which is not valid JSON
        assert client.start() == False


def test_query_success(mock_popen):
    """Normal query → returns ok response."""
    mock_popen.stdout.readline.return_value = json.dumps({"status": "ok", "x": 7, "y": 7, "score": 100}) + "\n"
    mock_popen.stdout.readline.side_effect = [
        json.dumps({"status": "ready"}) + "\n",
        json.dumps({"status": "ok", "x": 7, "y": 7, "score": 100}) + "\n",
    ]
    with patch("subprocess.Popen", return_value=mock_popen):
        client = WorkerClient("model.bin", "config.cfg", timeout=1.0)
        client.start()
        result = client.query([(7, 7, 0)], visits=64)
        assert result["status"] == "ok"
        assert result["x"] == 7
        assert result["y"] == 7


def test_query_worker_error(mock_popen):
    """Worker returns error → passes through."""
    mock_popen.stdout.readline.side_effect = [
        json.dumps({"status": "ready"}) + "\n",
        json.dumps({"status": "error", "error": "No legal moves"}) + "\n",
    ]
    with patch("subprocess.Popen", return_value=mock_popen):
        client = WorkerClient("model.bin", "config.cfg", timeout=1.0)
        client.start()
        result = client.query([(7, 7, 0)])
        assert result["status"] == "error"
        assert "No legal moves" in result["error"]


def test_query_json_parse_error(mock_popen):
    """Worker returns malformed JSON → returns JSON_PARSE_ERROR."""
    mock_popen.stdout.readline.side_effect = [
        json.dumps({"status": "ready"}) + "\n",
        "not valid json\n",
    ]
    mock_popen.poll.return_value = None
    with patch("subprocess.Popen", return_value=mock_popen):
        client = WorkerClient("model.bin", "config.cfg", timeout=1.0)
        client.start()
        result = client.query([(7, 7, 0)])
        assert result["status"] == "error"
        assert "JSON_PARSE_ERROR" in result["error"]


def test_query_worker_crashed(mock_popen):
    """Worker process died → returns WORKER_CRASHED."""
    mock_popen.stdout.readline.side_effect = [
        json.dumps({"status": "ready"}) + "\n",
    ]
    mock_popen.poll.return_value = -11  # SIGSEGV

    with patch("subprocess.Popen", return_value=mock_popen):
        client = WorkerClient("model.bin", "config.cfg", timeout=1.0)
        client.start()
        result = client.query([(7, 7, 0)])
        assert result["status"] == "error"
        assert result["error"] == "WORKER_CRASHED"


def test_is_alive_when_running(mock_popen):
    """Process running → is_alive() returns True."""
    mock_popen.poll.return_value = None
    with patch("subprocess.Popen", return_value=mock_popen):
        client = WorkerClient("model.bin", "config.cfg")
        client._proc = mock_popen
        assert client.is_alive() == True


def test_is_alive_when_exited(mock_popen):
    """Process exited → is_alive() returns False."""
    mock_popen.poll.return_value = 0
    with patch("subprocess.Popen", return_value=mock_popen):
        client = WorkerClient("model.bin", "config.cfg")
        client._proc = mock_popen
        assert client.is_alive() == False


def test_close_sends_quit(mock_popen):
    """close() sends quit and waits."""
    mock_popen.wait.return_value = 0
    mock_popen.stdin.closed = False
    with patch("subprocess.Popen", return_value=mock_popen):
        client = WorkerClient("model.bin", "config.cfg")
        client._proc = mock_popen
        client.close()
        mock_popen.stdin.write.assert_called_with("quit\n")


def test_reset_board_sends_reset(mock_popen):
    """reset_board() sends reset action."""
    mock_popen.stdout.readline.side_effect = [
        json.dumps({"status": "ready"}) + "\n",
        json.dumps({"status": "ok"}) + "\n",
    ]
    with patch("subprocess.Popen", return_value=mock_popen):
        client = WorkerClient("model.bin", "config.cfg", timeout=1.0)
        client.start()
        result = client.reset_board()
        assert result["status"] == "ok"
