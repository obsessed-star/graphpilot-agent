import json
import os
import subprocess
import sys


def test_offline_demo_cli_exercises_real_graph():
    result = subprocess.run(
        [sys.executable, "-m", "graphpilot.cli", "demo"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    report = json.loads(result.stdout)
    assert report["live_model_calls"] == 0
    assert report["approval_pause_verified"] and report["file_write_verified"]


def test_doctor_never_displays_key(tmp_path):
    env = {**os.environ, "GROQ_API_KEY": "PRIVATE_TEST_SENTINEL", "AGENT_MODEL": "groq/test"}
    result = subprocess.run(
        [sys.executable, "-m", "graphpilot.cli", "doctor"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
        env=env,
        cwd=tmp_path,
    )
    assert json.loads(result.stdout)["key_present"]
    assert "PRIVATE_TEST_SENTINEL" not in result.stdout + result.stderr
