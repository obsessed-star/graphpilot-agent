import pytest

from graphpilot.config import Settings
from graphpilot.graph import build_graph, initial_state
from graphpilot.tools import Registry, Tool, obj


@pytest.mark.parametrize("reason", ["length", "max_tokens"])
def test_truncated_output_is_not_success_and_does_not_execute_tools(reason):
    executed = []
    registry = Registry()
    registry.add(Tool("probe", "probe", obj({}), lambda: executed.append(True) or {}))

    class Truncated:
        def complete(self, *_args):
            return {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "partial", "type": "function", "function": {"name": "probe", "arguments": "{"}}
                    ],
                },
                "finish_reason": reason,
                "usage": {"completion_tokens": 256},
            }

    result = build_graph(Truncated(), registry, Settings()).invoke(initial_state("test"))
    assert result["status"] == "output_limit"
    assert result["model_calls"] == 1 and result["tool_calls"] == 0
    assert not executed
    assert not result["messages"][-1].get("tool_calls")
    assert result["usage"] == [{"completion_tokens": 256}]


@pytest.mark.parametrize("content", [None, "", []])
def test_empty_visible_response_is_not_completed(content):
    class Empty:
        def complete(self, *_args):
            return {"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}

    result = build_graph(Empty(), Registry(), Settings()).invoke(initial_state("test"))
    assert result["status"] == "empty_response"
