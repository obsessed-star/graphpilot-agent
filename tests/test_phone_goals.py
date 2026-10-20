"""Outcome-oriented graph/transport fixtures. No live website, model, or phone is implied."""

import hashlib
import json
import struct
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from graphpilot.config import Settings
from graphpilot.graph import build_graph, initial_state
from graphpilot.tools import add_phone_tools, workspace_tools

pytest.importorskip("usbphone")
from usbphone.adb import Device  # noqa: E402
from usbphone.controller import Phone  # noqa: E402


class WebsitePhone:
    """A tiny Android transport fixture whose UI changes in response to actual commands."""

    def __init__(self, goal):
        self.goal = goal
        self.page = "Home"
        self.files = {}
        self.actions = []

    def select(self, serial=None):
        assert serial in (None, "fixture")
        return Device("fixture", "device", True, "Fixture")

    def run(self, *args):
        return b"\x89PNG\r\n\x1a\n\0\0\0\rIHDR" + struct.pack(">II", 1080, 1920)

    def shell(self, serial, *args):
        if args[0] == "am":
            self.actions.append(args)
            self.page = "Download document" if self.goal == "document" else "Applicant name"
        elif args[:2] == ("input", "text"):
            self.actions.append(args)
            assert args[2] == "Fixture%sCandidate"
            self.page = "Submit application"
        elif args[:2] == ("input", "tap"):
            self.actions.append(args)
            if self.goal == "document":
                self.files["certificate.pdf"] = b"%PDF-1.7\nsynthetic test document"
                self.page = "Download complete"
            else:
                self.page = "Application received: FIXTURE-001"
        elif args[0] == "cat":
            return (
                '<hierarchy><node text="' + self.page + '" clickable="true" enabled="true" '
                'bounds="[0,0][400,100]"/></hierarchy>'
            ).encode()
        elif args[0] == "find":
            return b"".join(("/sdcard/Download/" + n).encode() + b"\0" for n in self.files)
        elif args[0] in {"stat", "sha256sum", "head"}:
            data = self.files[args[-1].rsplit("/", 1)[1]]
            if args[0] == "stat":
                return f"regular file:{len(data)}".encode()
            if args[0] == "sha256sum":
                return hashlib.sha256(data).hexdigest().encode()
            return data
        return b""


class GoalFixtureProvider:
    """Rules replace model inference; graph, approval, tool registry and controller stay real."""

    def __init__(self, goal):
        self.goal = goal
        self.calls = 0
        self.before = None
        self.evidence = None

    def complete(self, messages, tools):
        self.calls += 1
        results = [m for m in messages if m["role"] == "tool"]
        previous = results[-1] if results else None
        result = json.loads(previous["content"]) if previous else {}
        assert "error" not in result
        if result.get("denied"):
            return {"message": {"role": "assistant", "content": "Submission was denied; not submitted."}}
        name = previous["name"] if previous else None
        if name is None:
            tool, args = ("phone_list_downloads", {}) if self.goal == "document" else ("phone_observe", {})
        elif name == "phone_list_downloads":
            if self.before is None:
                self.before = result["files"]
                tool, args = "phone_observe", {}
            else:
                new = set(result["files"]) - set(self.before)
                assert new == {"certificate.pdf"}
                tool, args = "phone_export_download", {"name": new.pop()}
        elif name == "phone_export_download":
            self.evidence = result
            return {"message": {"role": "assistant", "content": "Saved: " + result["path"]}}
        else:
            obs = result.get("observation", result)
            label = obs["elements"][0]["text"]
            args = {"observation_id": obs["observation_id"]}
            if label == "Home":
                tool = "phone_open_url"
                args.update(url="https://example.org/fixture", package="")
            elif label == "Applicant name":
                tool = "phone_type_text"
                args["text"] = "Fixture Candidate"
            elif label in {"Download document", "Submit application"}:
                tool = "phone_tap_element"
                args["index"] = 0
            elif label == "Download complete":
                tool, args = "phone_list_downloads", {}
            else:
                assert label == "Application received: FIXTURE-001"
                self.evidence = label
                return {"message": {"role": "assistant", "content": label}}
        return {
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": f"step-{self.calls}",
                        "type": "function",
                        "function": {"name": tool, "arguments": json.dumps(args)},
                    }
                ],
            }
        }


@pytest.mark.parametrize(
    "goal,deny_submit", [("document", False), ("application", False), ("application", True)]
)
def test_goal_to_evidence_over_real_graph_and_phone_controller(tmp_path, monkeypatch, goal, deny_submit):
    monkeypatch.setattr("usbphone.controller.time.sleep", lambda _: None)
    transport = WebsitePhone(goal)
    phone = Phone(transport, output=tmp_path / "captures")
    registry = workspace_tools(tmp_path / "workspace")
    add_phone_tools(registry, phone)
    provider = GoalFixtureProvider(goal)
    graph = build_graph(provider, registry, Settings(max_model_calls=12), InMemorySaver())
    config = {"configurable": {"thread_id": "goal"}, "recursion_limit": 50}
    prompt = (
        "Bu siteden belgeyi indir: https://example.org/fixture"
        if goal == "document"
        else "Bu iş yerine benim için başvur. Doğrulanmış adım: Fixture Candidate."
    )
    result = graph.invoke(initial_state(prompt), config)
    while result.get("__interrupt__"):
        request = result["__interrupt__"][0].value
        approve = not (deny_submit and request["tool"] == "phone_tap_element")
        # Resumption restores the controller observation, as it must after a process restart.
        phone._last = None
        result = graph.invoke(Command(resume=approve), config)
    assert result["status"] == "completed"
    if deny_submit:
        assert transport.page == "Submit application" and provider.evidence is None
        assert "not submitted" in result["messages"][-1]["content"]
    elif goal == "document":
        assert Path(provider.evidence["path"]).read_bytes() == transport.files["certificate.pdf"]
        assert provider.evidence["transfer_verified"]
        assert not provider.evidence["content_verified"]
    else:
        assert provider.evidence == "Application received: FIXTURE-001"
