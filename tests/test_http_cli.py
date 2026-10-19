"""Real CLI + LiteLLM + HTTP integration, using a local scripted Groq-compatible server."""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class PrivateEnvironment(dict):
    def __repr__(self):
        return "<local API test environment; values hidden>"


@pytest.fixture
def local_api():
    requests = []
    settings = {"status": 200}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(body)
            if settings["status"] != 200:
                self.send_response(settings["status"])
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"Local test rejected the request"}}')
                return
            tool_results = [m for m in body["messages"] if m["role"] == "tool"]
            if tool_results:
                result = json.loads(tool_results[-1]["content"])
                message = {"role": "assistant", "content": "denied" if result.get("denied") else "written"}
                reason = "stop"
            else:
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "http-write",
                            "type": "function",
                            "function": {
                                "name": "write_file",
                                "arguments": json.dumps(
                                    {"path": "result.txt", "content": "HTTP tool execution\n"}
                                ),
                            },
                        }
                    ],
                }
                reason = "tool_calls"
            response = {
                "id": "local-test",
                "object": "chat.completion",
                "created": 1,
                "model": body["model"],
                "choices": [
                    {"index": 0, "message": message, "finish_reason": reason},
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = PrivateEnvironment(
        {
            **os.environ,
            "AGENT_MODEL": "groq/llama-3.3-70b-versatile",
            "AGENT_API_BASE": f"http://127.0.0.1:{server.server_port}/openai/v1",
            "AGENT_API_KEY_ENV": "LOCAL_TEST_KEY",
            "LOCAL_TEST_KEY": "local-fixture-only",
            "AGENT_VISION": "false",
            "AGENT_MAX_MODEL_CALLS": "8",
            "AGENT_MAX_TOOL_CALLS": "12",
            "AGENT_MAX_INPUT_CHARS": "24000",
            "LITELLM_LOCAL_MODEL_COST_MAP": "True",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    try:
        yield env, requests, settings
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def invoke(tmp_path, env, *arguments):
    return subprocess.run(
        [sys.executable, "-m", "graphpilot.cli", *arguments],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize("decision", ["approve", "deny"])
def test_real_cli_http_round_trip_and_sqlite_resume(tmp_path, local_api, decision):
    env, requests, _ = local_api
    paused = invoke(tmp_path, env, "run", "Write a file", "--session", "http", "--non-interactive")
    assert paused.returncode == 0, paused.stderr + paused.stdout
    assert json.loads(paused.stdout)["status"] == "awaiting_approval"
    target = tmp_path / "workspace" / "result.txt"
    assert not target.exists()
    resumed = invoke(tmp_path, env, "resume", decision, "--session", "http", "--non-interactive")
    assert resumed.returncode == 0, resumed.stderr + resumed.stdout
    assert len(requests) == 2
    if decision == "approve":
        assert target.read_text() == "HTTP tool execution\n"
        assert "written" in resumed.stdout
    else:
        assert not target.exists()
        assert "denied" in resumed.stdout


@pytest.mark.parametrize("status", [401, 429])
def test_http_failure_has_nonzero_cli_exit_without_retries(tmp_path, local_api, status):
    env, requests, settings = local_api
    settings["status"] = status
    result = invoke(tmp_path, env, "run", "test", "--non-interactive")
    assert '"status": "provider_error"' in result.stdout
    assert len(requests) == 1  # No hidden retries or external provider requests.
    assert result.returncode == 2
