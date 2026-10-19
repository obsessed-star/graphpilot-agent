from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv, set_key
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from graphpilot.config import Settings
from graphpilot.graph import build_graph, initial_state
from graphpilot.provider import LiteLLMProvider
from graphpilot.tools import add_phone_tools, workspace_tools


def make_registry(workspace: Path, phone_enabled: bool, state_dir: Path):
    registry = workspace_tools(workspace)
    if phone_enabled:
        try:
            from usbphone.controller import Phone
        except ImportError as exc:
            raise ValueError("Install the separate usbphone-control project to use --phone.") from exc
        add_phone_tools(registry, Phone(output=state_dir / "phone"))
    return registry


def print_result(result):
    if result.get("__interrupt__"):
        print(json.dumps({"status": "awaiting_approval", "request": result["__interrupt__"][0].value},
                         ensure_ascii=False, indent=2))
    else:
        last = result["messages"][-1]
        print(last.get("content") or "[No text response]")
        print(json.dumps({k: result[k] for k in ("status", "model_calls", "tool_calls")}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Provider-neutral LangGraph agent with durable tool approval.")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--state-dir", default=".graphpilot")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="Run an offline graph/approval exercise. No model or phone required.")
    sub.add_parser("doctor", help="Check configuration without calling a model.")
    configure = sub.add_parser("configure", help="Read a key privately into a local ignored env file.")
    configure.add_argument("--key-env", default="GROQ_API_KEY")
    for name in ("run", "resume"):
        command = sub.add_parser(name)
        if name == "run":
            command.add_argument("prompt")
        else:
            command.add_argument("decision", choices=["approve", "deny"])
        command.add_argument("--session", default="default")
        command.add_argument("--workspace", default="workspace")
        command.add_argument("--phone", action="store_true")
        command.add_argument("--non-interactive", action="store_true")
    args = parser.parse_args()
    load_dotenv(args.env_file, override=False)
    try:
        if args.command == "configure":
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", args.key_env):
                raise ValueError("Use an uppercase environment variable name.")
            target = Path(args.env_file)
            if target.is_symlink():
                raise ValueError("Refusing to write a key through a symlink.")
            if not sys.stdin.isatty():
                raise ValueError("Run configure in your own terminal; do not send keys as CLI arguments.")
            key = getpass.getpass(f"{args.key_env} (hidden): ").strip()
            if not key:
                raise ValueError("Empty key was not saved.")
            target.touch(mode=0o600, exist_ok=True)
            set_key(str(target), args.key_env, key)
            print(f"Saved {args.key_env} to {target.resolve()}. Value is hidden.")
            return
        if args.command == "demo":
            from graphpilot.demo import run_demo
            print(json.dumps(run_demo(), indent=2))
            return
        settings = Settings.from_env()
        if args.command == "doctor":
            variable = settings.api_key_env or {
                "groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
                "gemini": "GEMINI_API_KEY", "azure": "AZURE_API_KEY",
            }.get(settings.model.split("/")[0])
            print(json.dumps({"model": settings.model, "key_variable": variable,
                              "key_present": bool(os.getenv(variable)) if variable else None,
                              "vision_enabled": settings.vision, "live_model_calls": 0}, indent=2))
            return
        state_dir = Path(args.state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)
        registry = make_registry(Path(args.workspace), args.phone, state_dir)
        config = {"configurable": {"thread_id": args.session},
                  "recursion_limit": settings.max_model_calls * 3 + 10}
        with SqliteSaver.from_conn_string(str(state_dir / "sessions.sqlite")) as saver:
            graph = build_graph(LiteLLMProvider(settings), registry, settings, saver)
            previous = graph.get_state(config)
            pending = bool(previous.next)
            if args.command == "run" and pending:
                raise ValueError("This session awaits approval. Use resume approve/deny before a new task.")
            if args.command == "resume" and not pending:
                raise ValueError("This session has no pending action.")
            value = (initial_state(args.prompt) if args.command == "run"
                     else Command(resume=args.decision == "approve"))
            result = graph.invoke(value, config)
            while result.get("__interrupt__") and not args.non_interactive:
                print_result(result)
                decision = input("Bu işlemi onaylıyor musun? [e/H]: ").strip().lower() in {"e", "evet", "y", "yes"}
                result = graph.invoke(Command(resume=decision), config)
            print_result(result)
    except (ValueError, OSError, EOFError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    except KeyboardInterrupt:
        print("Stopped. Any pending approval remains in the session.", file=sys.stderr)
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
