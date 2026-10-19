from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., dict]
    mutating: bool = False

    def schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def validate(self, args: dict):
        errors = list(Draft202012Validator(self.parameters).iter_errors(args))
        if errors:
            raise ValueError("Tool arguments do not match the declared JSON schema.")


class Registry:
    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def add(self, tool: Tool):
        if tool.name in self.tools:
            raise ValueError(f"Duplicate tool: {tool.name}")
        Draft202012Validator.check_schema(tool.parameters)
        self.tools[tool.name] = tool

    def schemas(self):
        return [t.schema() for t in self.tools.values()]

    def prepare(self, call: dict) -> tuple[Tool, dict]:
        function = call.get("function", {})
        tool = self.tools.get(function.get("name"))
        if not tool:
            raise ValueError("Unknown tool requested.")
        args = json.loads(function.get("arguments", "{}"))
        tool.validate(args)
        return tool, args


def obj(properties: dict, required: list[str] | None = None):
    return {
        "type": "object",
        "properties": properties,
        "required": required if required is not None else list(properties),
        "additionalProperties": False,
    }


def workspace_tools(root: Path) -> Registry:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    registry = Registry()

    def resolve(path: str) -> Path:
        if ":" in path or "\x00" in path:
            raise ValueError("Invalid workspace path.")
        candidate = (root / path).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError("Path escapes the workspace.")
        if any(part.startswith(".") for part in candidate.relative_to(root).parts):
            raise ValueError("Hidden paths are excluded from agent file access.")
        return candidate

    def list_files():
        paths = []
        # Bound traversal as well as output; never recursively scan the host filesystem.
        for path in root.iterdir():
            if not path.name.startswith(".") and not path.is_symlink():
                paths.append({"name": path.name, "directory": path.is_dir()})
            if len(paths) >= 100:
                break
        return {"entries": paths}

    def read_file(path: str):
        target = resolve(path)
        if target.stat().st_size > 16000:
            raise ValueError("File exceeds 16 KB; narrow the input.")
        return {"path": path, "content": target.read_text("utf-8")}

    def write_file(path: str, content: str):
        target = resolve(path)
        if len(content.encode("utf-8")) > 16000:
            raise ValueError("File exceeds 16 KB.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": path, "bytes": target.stat().st_size, "written": True}

    registry.add(Tool("list_files", "List top-level entries in the task workspace.", obj({}), list_files))
    path_schema = {"type": "string", "minLength": 1, "maxLength": 200}
    registry.add(
        Tool("read_file", "Read a UTF-8 workspace file (up to 16 KB).", obj({"path": path_schema}), read_file)
    )
    registry.add(
        Tool(
            "write_file",
            "Write a UTF-8 workspace file. Requires human approval.",
            obj({"path": path_schema, "content": {"type": "string", "maxLength": 16000}}),
            write_file,
            mutating=True,
        )
    )
    return registry


def add_phone_tools(registry: Registry, phone):
    registry.add(
        Tool(
            "phone_observe",
            "Read USB phone screenshot and UI. Observe before every action.",
            obj({}),
            phone.observe,
        )
    )
    observation = {"type": "string", "pattern": "^[a-f0-9]{32}$"}
    integer = {"type": "integer", "minimum": 0}
    specs = {
        "tap": {"x": integer, "y": integer},
        "tap_element": {"index": integer},
        "swipe": {
            **{k: integer for k in ("x1", "y1", "x2", "y2")},
            "duration_ms": {"type": "integer", "minimum": 50, "maximum": 3000},
        },
        "type_text": {"text": {"type": "string", "minLength": 1, "maxLength": 1000}},
        "key": {"key": {"type": "string", "enum": ["HOME", "BACK", "ENTER", "BACKSPACE", "RECENTS"]}},
        "launch": {"package": {"type": "string", "minLength": 3, "maxLength": 200}},
    }
    for action, properties in specs.items():

        def handler(observation_id, _action=action, **kwargs):
            # After a durable agent restart the Phone instance has no in-memory observation.
            phone.restore(observation_id)
            return phone.act(_action, observation_id, **kwargs)

        registry.add(
            Tool(
                f"phone_{action}",
                f"Android {action}; use the latest observation ID. Requires human approval.",
                obj({"observation_id": observation, **properties}),
                handler,
                mutating=True,
            )
        )
