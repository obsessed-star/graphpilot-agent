import json

import pytest

from graphpilot.config import Settings
from graphpilot.graph import build_graph, initial_state
from graphpilot.tools import Registry, workspace_tools


@pytest.mark.parametrize(
    "bad",
    [
        [{"type": "function", "function": {"name": "x", "arguments": "{}"}}],
        [{"id": "x", "function": {"name": "x", "arguments": {}}}],
        {"id": "x"},
    ],
)
def test_malformed_provider_tool_calls_fail_before_dispatch(bad):
    class BadProvider:
        def complete(self, *args):
            return {"message": {"role": "assistant", "content": None, "tool_calls": bad}}

    graph = build_graph(BadProvider(), Registry(), Settings())
    assert graph.invoke(initial_state("test"))["status"] == "provider_error"


def test_windows_alternate_stream_path_is_rejected(tmp_path):
    registry = workspace_tools(tmp_path)
    tool, args = registry.prepare(
        {
            "function": {
                "name": "write_file",
                "arguments": json.dumps({"path": "note.txt:stream", "content": "x"}),
            }
        }
    )
    with pytest.raises(ValueError, match="Invalid workspace"):
        tool.handler(**args)
