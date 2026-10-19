"""Deterministic OFFLINE integration exercise; this is not a live AI result."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from graphpilot.config import Settings
from graphpilot.graph import build_graph, initial_state
from graphpilot.tools import workspace_tools


class DemoProvider:
    def complete(self, messages, tools):
        if not any(m["role"] == "tool" for m in messages):
            return {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "demo-write",
                            "type": "function",
                            "function": {
                                "name": "write_file",
                                "arguments": json.dumps(
                                    {
                                        "path": "demo.txt",
                                        "content": "An approved tool wrote this file.\n",
                                    }
                                ),
                            },
                        }
                    ],
                },
                "usage": {"demo": True},
            }
        return {
            "message": {"role": "assistant", "content": "Offline demo: approved file write verified."},
            "usage": {"demo": True},
        }


def run_demo():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        graph = build_graph(DemoProvider(), workspace_tools(root), Settings(), InMemorySaver())
        config = {"configurable": {"thread_id": "offline-demo"}}
        paused = graph.invoke(initial_state("Write a short file."), config)
        assert paused.get("__interrupt__") and not (root / "demo.txt").exists()
        result = graph.invoke(Command(resume=True), config)
        assert (root / "demo.txt").read_text() == "An approved tool wrote this file.\n"
        return {
            "mode": "offline-scripted-provider",
            "live_model_calls": 0,
            "approval_pause_verified": True,
            "file_write_verified": True,
            "model_calls": result["model_calls"],
            "tool_calls": result["tool_calls"],
            "status": result["status"],
        }
