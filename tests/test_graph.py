import json

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from graphpilot.config import Settings
from graphpilot.graph import build_graph, initial_state, request_messages, text_size
from graphpilot.provider import LiteLLMProvider
from graphpilot.tools import Registry, Tool, add_phone_tools, obj, workspace_tools


def call(name, args, identifier="call-1"):
    return {
        "id": identifier,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(args),
        },
    }


def answer(text):
    return {"role": "assistant", "content": text}


def request(*calls):
    return {"role": "assistant", "content": None, "tool_calls": list(calls)}


class Script:
    def __init__(self, *messages):
        self.messages = list(messages)
        self.requests = []

    def complete(self, messages, tools):
        self.requests.append((messages, tools))
        return {"message": self.messages.pop(0), "usage": {"total_tokens": 10}}


def execute(provider, registry=None, settings=None):
    graph = build_graph(provider, registry or Registry(), settings or Settings(), InMemorySaver())
    config = {"configurable": {"thread_id": "test"}}
    return graph, config, graph.invoke(initial_state("test"), config)


def test_real_langgraph_runs_registered_tool_then_model(tmp_path):
    (tmp_path / "input.txt").write_text("fixture", encoding="utf-8")
    model = Script(request(call("read_file", {"path": "input.txt"})), answer("Read verified."))
    _, _, result = execute(model, workspace_tools(tmp_path))
    assert result["status"] == "completed"
    assert result["model_calls"] == 2 and result["tool_calls"] == 1
    tool_result = json.loads(model.requests[1][0][-1]["content"])
    assert tool_result["content"] == "fixture"


def test_approval_blocks_side_effect_until_resumed(tmp_path):
    model = Script(request(call("write_file", {"path": "out.txt", "content": "approved"})), answer("done"))
    graph, config, paused = execute(model, workspace_tools(tmp_path))
    assert paused["__interrupt__"][0].value["tool"] == "write_file"
    assert not (tmp_path / "out.txt").exists()
    result = graph.invoke(Command(resume=True), config)
    assert result["status"] == "completed"
    assert (tmp_path / "out.txt").read_text() == "approved"
    assert len(model.requests) == 2  # Approval does not invoke a critic or regenerate the tool call.


def test_denial_never_executes(tmp_path):
    model = Script(request(call("write_file", {"path": "out.txt", "content": "no"})), answer("denied"))
    graph, config, _ = execute(model, workspace_tools(tmp_path))
    result = graph.invoke(Command(resume=False), config)
    assert not (tmp_path / "out.txt").exists()
    assert result["tool_calls"] == 0
    assert json.loads(model.requests[1][0][-1]["content"])["denied"]


def test_sqlite_approval_survives_rebuilding_graph(tmp_path):
    database = str(tmp_path / "sessions.sqlite")
    workspace = tmp_path / "workspace"
    model = Script(request(call("write_file", {"path": "resume.txt", "content": "durable"})))
    config = {"configurable": {"thread_id": "durable"}}
    with SqliteSaver.from_conn_string(database) as saver:
        graph = build_graph(model, workspace_tools(workspace), Settings(), saver)
        assert graph.invoke(initial_state("write"), config)["__interrupt__"]
    with SqliteSaver.from_conn_string(database) as saver:
        graph = build_graph(Script(answer("resumed")), workspace_tools(workspace), Settings(), saver)
        result = graph.invoke(Command(resume=True), config)
        assert result["status"] == "completed"
    assert (workspace / "resume.txt").read_text() == "durable"


@pytest.mark.parametrize("args", [{"path": "../escape.txt"}, {"path": ".env"}, {"path": "x", "extra": 1}])
def test_invalid_or_escaped_read_is_tool_error(tmp_path, args):
    model = Script(request(call("read_file", args)), answer("stopped"))
    execute(model, workspace_tools(tmp_path))
    assert "error" in json.loads(model.requests[1][0][-1]["content"])


def test_multiple_tool_calls_are_not_executed(tmp_path):
    model = Script(request(call("list_files", {}, "a"), call("list_files", {}, "b")), answer("stopped"))
    _, _, result = execute(model, workspace_tools(tmp_path))
    assert result["tool_calls"] == 0
    assert all("error" in json.loads(m["content"]) for m in model.requests[1][0][-2:])


def test_model_call_budget_stops_before_another_provider_request(tmp_path):
    model = Script(request(call("list_files", {})))
    _, _, result = execute(model, workspace_tools(tmp_path), Settings(max_model_calls=1))
    assert result["status"] == "model_call_limit"
    assert len(model.requests) == 1


def test_tool_call_budget_stops_effects(tmp_path):
    model = Script(request(call("list_files", {})), request(call("list_files", {})), answer("stopped"))
    _, _, result = execute(model, workspace_tools(tmp_path), Settings(max_tool_calls=1))
    assert result["tool_calls"] == 1
    assert "limit" in json.loads(model.requests[2][0][-1]["content"])["error"]


def test_context_cap_makes_no_remote_call():
    model = Script()
    _, _, result = execute(model, settings=Settings(max_input_chars=10))
    assert result["status"] == "input_limit" and not model.requests


def test_provider_error_is_not_persisted_verbatim():
    class Failing:
        def complete(self, *args):
            raise RuntimeError("SECRET-sentinel")

    _, _, result = execute(Failing())
    assert result["status"] == "provider_error"
    assert "SECRET-sentinel" not in json.dumps(result)


def test_litellm_adapter_forwards_config_and_disables_retries(monkeypatch):
    import litellm

    captured = {}

    class Message:
        def model_dump(self, **kwargs):
            return {"role": "assistant", "content": "ok", "provider_specific_fields": {"ignored": True}}

    class Response:
        choices = [type("Choice", (), {"message": Message()})()]
        usage = None

    def completion(**kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(litellm, "completion", completion)
    monkeypatch.setenv("CUSTOM_TEST_KEY", "not-a-real-key")
    provider = LiteLLMProvider(
        Settings(model="groq/test", api_base="https://example.invalid/v1", api_key_env="CUSTOM_TEST_KEY")
    )
    result = provider.complete([{"role": "user", "content": "x"}], [{"type": "function"}])
    assert captured["num_retries"] == 0 and captured["api_key"] == "not-a-real-key"
    assert captured["model"] == "openai/test" and captured["api_base"] == "https://example.invalid/v1"
    assert result["message"] == answer("ok")


def test_screenshots_do_not_count_as_text_and_only_latest_is_sent():
    image = {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "x" * 50000}}]}
    messages = request_messages([image, answer("step"), image])
    assert isinstance(messages[0]["content"], str)
    assert isinstance(messages[2]["content"], list)
    assert text_size(messages) < 1000


def test_registry_rejects_duplicate_names():
    registry = Registry()
    tool = Tool("x", "x", obj({}), lambda: {})
    registry.add(tool)
    with pytest.raises(ValueError, match="Duplicate"):
        registry.add(tool)


def test_agent_and_phone_integration_restores_action_observation(tmp_path, monkeypatch):
    # This runs the real graph and phone controller together over a deterministic fake USB transport.
    import struct

    pytest.importorskip("usbphone")
    from usbphone.adb import Device
    from usbphone.controller import Phone

    class Transport:
        def __init__(self):
            self.actions = []

        def select(self, serial=None):
            return Device("fixture", "device", True, "Fixture")

        def run(self, *args):
            return b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + struct.pack(">II", 1080, 1920)

        def shell(self, serial, *args):
            if args[0] == "input":
                self.actions.append(args)
            return b"<hierarchy/>" if args[0] == "cat" else b""

    transport = Transport()
    phone = Phone(transport, output=tmp_path / "captures")
    observation = phone.observe()
    registry = workspace_tools(tmp_path / "workspace")
    add_phone_tools(registry, phone)
    model = Script(
        request(call("phone_key", {"observation_id": observation["observation_id"], "key": "HOME"})),
        answer("Screen observed after action."),
    )
    graph, config, paused = execute(model, registry)
    assert paused["__interrupt__"] and not transport.actions
    monkeypatch.setattr("usbphone.controller.time.sleep", lambda _: None)
    phone._last = None  # Recreate the condition after an agent process restart.
    result = graph.invoke(Command(resume=True), config)
    assert transport.actions == [("input", "keyevent", "3")]
    assert result["tool_calls"] == 1


def test_config_rejects_zero_budgets():
    with pytest.raises(ValueError):
        Settings(max_model_calls=0)
