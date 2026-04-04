"""
value_claw CLI — entry point.

Subcommands
-----------
  onboard   Interactive first-time setup wizard
  start     Start the agent daemon (web dashboard + optional channels)
  stop      Stop the running daemon
  status    Show daemon status
  chat      Interactive CLI chat (foreground)
  skill     ClawHub marketplace (search / browse / install / info)
"""

import argparse
import asyncio
import logging

from . import config
from .core.persistent_agent import PersistentAgent
from .core.session_store import SessionStore

# ── Provider builder ─────────────────────────────────────────────────────────

_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "deepseek":  {"env": "DEEPSEEK_API_KEY",  "base": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "grok":      {"env": "GROK_API_KEY",      "base": "https://api.x.ai/v1",         "model": "grok-3"},
    "claude":    {"env": "ANTHROPIC_API_KEY",  "model": "claude-sonnet-4-6"},
    "anthropic": {"env": "ANTHROPIC_API_KEY",  "model": "claude-sonnet-4-6"},
    "gemini":    {"env": "GEMINI_API_KEY",     "model": "gemini-2.0-flash"},
    "kimi":      {"env": "KIMI_API_KEY",       "base": "https://api.moonshot.cn/v1",  "model": "moonshot-v1-128k"},
    "moonshot":  {"env": "KIMI_API_KEY",       "base": "https://api.moonshot.cn/v1",  "model": "moonshot-v1-128k"},
    "glm":       {"env": "GLM_API_KEY",        "base": "https://open.bigmodel.cn/api/paas/v4/", "model": "glm-4-flash"},
    "zhipu":     {"env": "GLM_API_KEY",        "base": "https://open.bigmodel.cn/api/paas/v4/", "model": "glm-4-flash"},
    "chatglm":   {"env": "GLM_API_KEY",        "base": "https://open.bigmodel.cn/api/paas/v4/", "model": "glm-4-flash"},
}

_CONFIG_KEY_MAP: dict[str, str] = {
    "anthropic": "claude", "moonshot": "kimi", "zhipu": "glm", "chatglm": "glm",
}


def _build_single_provider(name: str):
    """Build a single LLM provider by canonical name."""
    name = name.lower().strip()
    defaults = _PROVIDER_DEFAULTS.get(name)
    if not defaults:
        raise ValueError(f"Unknown LLM provider: '{name}'")

    cfg_key = _CONFIG_KEY_MAP.get(name, name)
    api_key = config.get_str("llm", cfg_key, "apiKey", env=defaults["env"])
    if not api_key:
        raise ValueError(f"{defaults['env']} not set (env or value_claw.json llm.{cfg_key}.apiKey)")

    if name in ("claude", "anthropic"):
        from .core.llm.anthropic_client import AnthropicProvider
        return AnthropicProvider(
            api_key=api_key,
            model_name=config.get_str("llm", cfg_key, "model", default=defaults["model"]),
        )

    if name == "gemini":
        from .core.llm.gemini_client import GeminiProvider
        return GeminiProvider(api_key=api_key)

    from .core.llm.openai_compatible import OpenAICompatibleProvider
    return OpenAICompatibleProvider(
        api_key=api_key,
        base_url=config.get_str("llm", cfg_key, "baseUrl", default=defaults.get("base", "")),
        model_name=config.get_str("llm", cfg_key, "model", default=defaults["model"]),
    )


def _build_provider():
    """Build the LLM provider, with optional fallback from config.

    Config example::

        "llm": {
            "provider": "claude",
            "fallback": "deepseek",
            "claude":   { "apiKey": "...", "model": "claude-sonnet-4-6" },
            "deepseek": { "apiKey": "...", "model": "deepseek-chat" }
        }
    """
    primary_name = config.get_str(
        "llm", "provider", env="LLM_PROVIDER", default="deepseek"
    ).lower()

    primary = _build_single_provider(primary_name)

    fallback_name = config.get_str("llm", "fallback", default="")
    if fallback_name:
        from .core.llm.fallback import FallbackProvider
        fallback = _build_single_provider(fallback_name)
        p_model = getattr(primary, "model_name", primary_name)
        f_model = getattr(fallback, "model_name", fallback_name)
        logging.getLogger(__name__).info("[LLM] %s → %s fallback enabled", p_model, f_model)
        return FallbackProvider(primary, fallback)

    return primary


# ── Ensure config is ready (auto-onboard if needed) ─────────────────────────

def _ensure_configured(config_path: str | None = None) -> None:
    """If no API key is configured, run the onboard wizard first."""
    from .onboard import needs_onboard, run_onboard

    if needs_onboard(config_path):
        print("[value_claw] No LLM provider configured. Starting setup wizard...\n")
        run_onboard(config_path)


# ── Subcommand handlers ─────────────────────────────────────────────────────

def _cmd_onboard(args) -> None:
    from .onboard import run_onboard
    run_onboard(args.config)


def _cmd_start(args) -> None:
    _ensure_configured(args.config)

    if args.foreground:
        _run_foreground(args)
    else:
        from .daemon import start_daemon
        start_daemon(channels=args.channels, config_path=args.config)


def _run_foreground(args) -> None:
    """Run the web server (+ optional channels) in the foreground."""
    provider = None
    try:
        provider = _build_provider()
    except Exception as exc:
        print(f"[value_claw] Warning: LLM provider not configured ({exc})")

    channels = args.channels or []

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        import uvicorn
    except ImportError:
        print("Error: Web mode requires 'fastapi' and 'uvicorn'.")
        print("Install with: pip install value_claw[web]")
        return

    from .web.app import create_app

    host = config.get_str("web", "host", default="0.0.0.0")
    port = config.get_int("web", "port", default=7788)

    app = create_app(provider, build_provider_fn=_build_provider)

    ch_to_start = channels or _detect_configured_channels()
    if ch_to_start:
        from .server import start_channels
        from .web import app as web_app_module
        label = "explicit" if channels else "auto-detected"
        print(f"[value_claw] Channels ({label}): {', '.join(ch_to_start)}")

        @app.on_event("startup")
        async def _start_channels():
            bots = await start_channels(provider, ch_to_start, fastapi_app=app)
            web_app_module._active_bots.extend(bots)

    print(f"[value_claw] Web dashboard: http://localhost:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


def _detect_configured_channels() -> list[str]:
    """Return channel names that have a token configured."""
    found = []
    tg_token = config.get_str("channels", "telegram", "token", default="")
    if tg_token:
        found.append("telegram")
    dc_token = config.get_str("channels", "discord", "token", default="")
    if dc_token:
        found.append("discord")
    return found


def _cmd_stop(args) -> None:
    from .daemon import stop_daemon
    stop_daemon()


def _cmd_status(args) -> None:
    from .daemon import print_status
    print_status()


def _cmd_chat(args) -> None:
    _ensure_configured(args.config)

    try:
        provider = _build_provider()
    except Exception as exc:
        print(f"Error: {exc}")
        return

    provider_name = config.get_str("llm", "provider", env="LLM_PROVIDER", default="deepseek")
    verbose = config.get("agent", "verbose", default=True)

    store = SessionStore()
    session_id = "cli"

    print(f"Initializing Agent with Provider: {provider_name.upper()}...")
    agent = PersistentAgent(
        provider=provider,
        verbose=bool(verbose),
        store=store,
        session_id=session_id,
    )
    print(f"Loaded {len(agent.loaded_skill_names)} active skills.")

    restored = len(agent.messages) - 1
    if restored > 0:
        print(f"Restored {restored} messages from previous session.")

    cfg_path = config.config_path()
    cfg_source = f" (config: {cfg_path})" if cfg_path else ""
    print("\n--- value_claw Agent ---")
    print(f"Provider: {provider_name}{cfg_source}")
    print(f"Session: {store._path(session_id)}")
    print("Commands: 'exit' to quit | '/compact [hint]' | '/status' | '/clear'")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break

            if user_input.startswith("/compact"):
                hint = user_input[len("/compact"):].strip() or None
                result = agent.compact(instruction=hint)
                print(f"Bot: {result}")
                continue

            if user_input == "/status":
                memory_count = len(agent.memory.list_all())
                print(
                    f"Bot: Session Status\n"
                    f"  Provider     : {type(agent.provider).__name__}\n"
                    f"  Skills       : {len(agent.loaded_skill_names)} loaded\n"
                    f"  Memories     : {memory_count} entries\n"
                    f"  History      : {len(agent.messages)} messages\n"
                    f"  Compactions  : {agent.compaction_count}\n"
                    f"  Session File : {store._path(session_id)}"
                )
                continue

            if user_input == "/clear":
                store.delete(session_id)
                agent.clear_history()
                print("Bot: Chat history cleared. Agent is still active with all skills and memory intact.")
                continue

            response = agent.chat(user_input)
            print(f"Bot: {response}")
        except KeyboardInterrupt:
            print("\nExiting...")
            break




# ── Argument parser ──────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="value_claw",
        description="value_claw — Autonomous AI Agent Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Quick start:\n"
            "  value_claw onboard       Set up your LLM provider\n"
            "  value_claw start         Start the agent daemon\n"
            "  value_claw chat          Interactive CLI chat\n"
            "\n"
            "Docs: https://github.com/ericwang915/value_claw"
        ),
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="Path to value_claw.json config file.",
    )
    # Hidden --mode for backward compat
    parser.add_argument("--mode", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--channels", nargs="+", default=None, help=argparse.SUPPRESS)

    sub = parser.add_subparsers(dest="command")

    # onboard
    sub.add_parser("onboard", help="Interactive first-time setup wizard")

    # start
    sp_start = sub.add_parser("start", help="Start the agent daemon")
    sp_start.add_argument(
        "--foreground", "-f", action="store_true",
        help="Run in foreground (don't daemonize)",
    )
    sp_start.add_argument(
        "--channels", nargs="+",
        choices=["telegram", "discord"],
        help="Also start messaging channels",
    )

    # stop
    sub.add_parser("stop", help="Stop the running daemon")

    # status
    sub.add_parser("status", help="Show daemon status")

    # chat
    sub.add_parser("chat", help="Interactive CLI chat (foreground)")

    return parser


# ── Backward-compat --mode handler ───────────────────────────────────────────

def _handle_legacy_mode(args) -> None:
    """Support the old ``--mode cli|web|telegram|discord`` flags."""
    mode = args.mode
    channels_arg = getattr(args, "channels", None)

    if channels_arg:
        try:
            provider = _build_provider()
        except Exception as exc:
            print(f"Error: {exc}")
            return
        from .server import run_server
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        asyncio.run(run_server(provider, channels=channels_arg))
        return

    if mode == "web":
        provider = None
        try:
            provider = _build_provider()
        except Exception as exc:
            print(f"[value_claw] Warning: LLM provider not configured ({exc})")
        try:
            import uvicorn
        except ImportError:
            print("Error: pip install value_claw[web]")
            return
        from .web.app import create_app
        host = config.get_str("web", "host", default="0.0.0.0")
        port = config.get_int("web", "port", default=7788)
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        app = create_app(provider, build_provider_fn=_build_provider)
        uvicorn.run(app, host=host, port=port, log_level="info")
        return

    if mode in ("telegram", "discord"):
        try:
            provider = _build_provider()
        except Exception as exc:
            print(f"Error: {exc}")
            return
        from .server import run_server
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        asyncio.run(run_server(provider, channels=[mode]))
        return

    # Default: cli
    try:
        provider = _build_provider()
    except Exception as exc:
        print(f"Error: {exc}")
        return
    _cmd_chat(args)


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    config.load()

    parser = _build_parser()
    args = parser.parse_args()

    if args.config:
        config.load(args.config, force=True)

    # Handle legacy --mode flag
    if args.mode and not args.command:
        _handle_legacy_mode(args)
        return

    dispatch = {
        "onboard": _cmd_onboard,
        "start": _cmd_start,
        "stop": _cmd_stop,
        "status": _cmd_status,
        "chat": _cmd_chat,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
