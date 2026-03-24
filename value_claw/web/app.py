"""
FastAPI application for the value_claw Web Dashboard.

Provides REST endpoints for config/skills/status inspection, a config
save endpoint for editing settings from the browser, and a WebSocket
endpoint for real-time chat with the agent.
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import config
from ..core.agent import Agent
from ..core.llm.base import LLMProvider
from ..core.persistent_agent import PersistentAgent
from ..core.session_store import SessionStore
from ..core.skill_loader import SkillRegistry

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

_agent: Agent | None = None
_provider: LLMProvider | None = None
_store: SessionStore | None = None
_start_time: float = 0.0
_build_provider_fn = None
_active_bots: list = []
_chat_lock: asyncio.Lock | None = None
_fastapi_app: FastAPI | None = None

WEB_SESSION_ID = "web:dashboard"


def _get_chat_lock() -> asyncio.Lock:
    """Lazily create the web chat lock (must be done inside the event loop)."""
    global _chat_lock
    if _chat_lock is None:
        _chat_lock = asyncio.Lock()
    return _chat_lock


def create_app(provider: LLMProvider | None, *, build_provider_fn=None) -> FastAPI:
    """Build and return the FastAPI app.

    Parameters
    ----------
    provider          : LLM provider (may be None if not yet configured)
    build_provider_fn : callable that rebuilds the provider from config
                        (used after config save to hot-reload the provider)
    """
    global _provider, _store, _start_time, _build_provider_fn, _fastapi_app
    _provider = provider
    _store = SessionStore()
    _start_time = time.time()
    _build_provider_fn = build_provider_fn

    app = FastAPI(title="value_claw Dashboard", docs_url=None, redoc_url=None)
    _fastapi_app = app

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.add_api_route("/", _serve_index, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/api/config", _api_config_get, methods=["GET"])
    app.add_api_route("/api/config", _api_config_save, methods=["POST"])
    app.add_api_route("/api/skills", _api_skills, methods=["GET"])
    app.add_api_route("/api/status", _api_status, methods=["GET"])
    app.add_api_route("/api/memories", _api_memories, methods=["GET"])
    app.add_api_route("/api/identity", _api_identity, methods=["GET"])
    app.add_api_route("/api/identity/soul", _api_save_soul, methods=["POST"])
    app.add_api_route("/api/identity/persona", _api_save_persona, methods=["POST"])
    app.add_api_route("/api/identity/tools", _api_get_tools_notes, methods=["GET"])
    app.add_api_route("/api/identity/tools", _api_save_tools_notes, methods=["POST"])
    app.add_api_route("/api/memory/index", _api_get_index, methods=["GET"])
    app.add_api_route("/api/memory/index", _api_save_index, methods=["POST"])
    app.add_api_route("/api/transcribe", _api_transcribe, methods=["POST"])
    app.add_api_route("/api/channels", _api_channels_status, methods=["GET"])
    app.add_api_route("/api/channels/restart", _api_channels_restart, methods=["POST"])
    app.add_api_route("/api/files/clear", _api_clear_files, methods=["POST"])
    app.add_api_route("/api/files", _api_list_files, methods=["GET"])
    # Cron / Prefect management
    app.add_api_route("/api/cron/jobs", _api_cron_list_jobs, methods=["GET"])
    app.add_api_route("/api/cron/jobs", _api_cron_add_job, methods=["POST"])
    app.add_api_route("/api/cron/jobs/{job_id}", _api_cron_update_job, methods=["PUT"])
    app.add_api_route("/api/cron/jobs/{job_id}", _api_cron_remove_job, methods=["DELETE"])
    app.add_api_route("/api/cron/jobs/{job_id}/trigger", _api_cron_trigger_job, methods=["POST"])
    app.add_api_route("/api/cron/jobs/{job_id}/runs", _api_cron_job_runs, methods=["GET"])
    app.add_api_route("/api/cron/runs", _api_cron_all_runs, methods=["GET"])
    app.add_api_route("/api/cron/reload", _api_cron_reload, methods=["POST"])
    app.add_api_route("/api/prefect/status", _api_prefect_status, methods=["GET"])
    # Portfolio management
    app.add_api_route("/api/portfolios/status", _api_portfolio_status, methods=["GET"])
    app.add_api_route("/api/portfolios/switch", _api_portfolio_switch, methods=["POST"])
    app.add_api_route("/api/portfolios/mode", _api_portfolio_mode, methods=["POST"])
    app.add_api_route("/api/portfolios/topup", _api_portfolio_topup, methods=["POST"])
    app.add_api_route("/api/portfolios/cashout", _api_portfolio_cashout, methods=["POST"])
    app.add_api_route("/api/portfolios/{pid}", _api_portfolio_detail, methods=["GET"])
    app.add_api_route("/api/portfolios/{pid}/allowed", _api_portfolio_get_allowed, methods=["GET"])
    app.add_api_route("/api/portfolios/{pid}/allowed", _api_portfolio_set_allowed, methods=["PUT"])
    app.add_api_route("/api/portfolios/{pid}/allowed/{symbol}", _api_portfolio_add_allowed, methods=["POST"])
    app.add_api_route("/api/portfolios/{pid}/allowed/{symbol}", _api_portfolio_remove_allowed, methods=["DELETE"])
    app.add_api_route("/api/portfolios/{pid}/holdings", _api_portfolio_add_holding, methods=["POST"])
    app.add_api_route("/api/portfolios/{pid}/holdings/{symbol}", _api_portfolio_remove_holding, methods=["DELETE"])
    app.add_api_route("/api/portfolios/{pid}/snapshots", _api_portfolio_snapshots, methods=["GET"])
    app.add_api_route("/api/portfolios/{pid}/snapshot", _api_portfolio_take_snapshot, methods=["POST"])
    app.add_api_route("/api/portfolios/buy", _api_portfolio_buy, methods=["POST"])
    app.add_api_route("/api/portfolios/sell", _api_portfolio_sell, methods=["POST"])
    app.add_api_route("/api/portfolios/{pid}/trades", _api_portfolio_trades, methods=["GET"])
    app.add_api_route("/api/portfolios/{pid}/performance", _api_portfolio_performance, methods=["GET"])
    # Strategy management
    app.add_api_route("/api/strategies", _api_strategy_list, methods=["GET"])
    app.add_api_route("/api/strategies", _api_strategy_create, methods=["POST"])
    app.add_api_route("/api/strategies/{sid}", _api_strategy_get, methods=["GET"])
    app.add_api_route("/api/strategies/{sid}", _api_strategy_update, methods=["PUT"])
    app.add_api_route("/api/strategies/{sid}", _api_strategy_delete, methods=["DELETE"])
    app.add_api_route("/api/strategies/{sid}/start", _api_strategy_start, methods=["POST"])
    app.add_api_route("/api/strategies/{sid}/stop", _api_strategy_stop, methods=["POST"])
    app.add_api_route("/api/strategies/{sid}/trigger", _api_strategy_trigger, methods=["POST"])
    app.add_api_route("/api/strategies/pending/trades", _api_strategy_pending, methods=["GET"])
    app.add_api_route("/api/strategies/pending/{trade_id}/approve", _api_strategy_approve, methods=["POST"])
    app.add_api_route("/api/strategies/pending/{trade_id}/reject", _api_strategy_reject, methods=["POST"])
    # Database / Analytics
    app.add_api_route("/api/analytics/daily-values", _api_daily_values, methods=["GET"])
    app.add_api_route("/api/analytics/trades", _api_analytics_trades, methods=["GET"])
    app.add_api_route("/api/analytics/events", _api_analytics_events, methods=["GET"])
    app.add_api_route("/api/analytics/strategy-events", _api_analytics_strategy_events, methods=["GET"])
    app.add_api_route("/api/analytics/db-status", _api_db_status, methods=["GET"])
    # Dashboard page
    app.add_api_route("/dashboard", _serve_dashboard, methods=["GET"], response_class=HTMLResponse)
    app.add_websocket_route("/ws/chat", _ws_chat)

    return app


def _get_agent() -> Agent | None:
    """Lazy-init the shared web agent with persistent sessions."""
    global _agent
    if _agent is not None:
        return _agent
    if _provider is None:
        return None
    try:
        verbose = config.get("agent", "verbose", default=False)
        _agent = PersistentAgent(
            provider=_provider,
            verbose=bool(verbose),
            store=_store,
            session_id=WEB_SESSION_ID,
        )
    except Exception as exc:
        logger.warning("[Web] Agent init failed: %s", exc)
        return None
    return _agent


def _reset_agent() -> None:
    """Discard the current agent so the next call rebuilds it."""
    global _agent
    _agent = None


# ── HTML ──────────────────────────────────────────────────────────────────────

async def _serve_index():
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


# ── REST API ──────────────────────────────────────────────────────────────────

def _mask_secrets(obj: Any, _parent_key: str = "") -> Any:
    """Recursively mask values whose key contains 'apikey' or 'token'."""
    if isinstance(obj, dict):
        return {k: _mask_secrets(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_mask_secrets(v) for v in obj]
    if isinstance(obj, str) and obj:
        key_lower = _parent_key.lower()
        if any(s in key_lower for s in ("apikey", "token", "secret", "password")):
            if len(obj) > 8:
                return obj[:4] + "*" * (len(obj) - 8) + obj[-4:]
            return "****"
    return obj


def _secret_keys_present(obj: Any, _parent_key: str = "") -> dict[str, str]:
    """Walk config and return a flat map of dotted-key → value for secret fields."""
    result: dict[str, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{_parent_key}.{k}" if _parent_key else k
            if isinstance(v, (dict, list)):
                result.update(_secret_keys_present(v, full))
            elif isinstance(v, str) and v:
                if any(s in k.lower() for s in ("apikey", "token", "secret", "password")):
                    result[full] = v
    return result


_MASKED_PLACEHOLDER = "••••••••"


async def _api_config_get():
    raw = config.as_dict()
    masked = _mask_secrets(copy.deepcopy(raw))
    cfg_path = config.config_path()

    # Build a list of which secret fields have a value set (without revealing them)
    secrets_set = {k: True for k in _secret_keys_present(raw)}

    return {
        "config": masked,
        "configPath": str(cfg_path) if cfg_path else None,
        "providerReady": _provider is not None,
        "secretsSet": secrets_set,
    }


def _deep_set(d: dict, keys: list[str], value: Any) -> None:
    """Set a value in a nested dict using a list of keys."""
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def _deep_get_raw(d: dict, keys: list[str]) -> Any:
    """Get a value from a nested dict using a list of keys."""
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


async def _api_config_save(request: Request):
    """Save new configuration to value_claw.json and hot-reload the provider.

    Secret fields that arrive as the masked placeholder or empty string
    are preserved from the existing config (not overwritten).
    """
    global _provider

    try:
        body = await request.json()
        new_config = body.get("config")
        if not isinstance(new_config, dict):
            return JSONResponse({"ok": False, "error": "Invalid config object."}, status_code=400)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    # Merge: for any secret field that is still the placeholder or empty,
    # keep the original value from the current config.
    existing = config.as_dict()
    existing_secrets = _secret_keys_present(existing)
    for dotted_key, original_value in existing_secrets.items():
        keys = dotted_key.split(".")
        incoming = _deep_get_raw(new_config, keys)
        if incoming is None or incoming == "" or incoming == _MASKED_PLACEHOLDER or "****" in str(incoming):
            _deep_set(new_config, keys, original_value)

    cfg_path = config.config_path()
    if cfg_path is None:
        cfg_path = config.VALUE_CLAW_HOME / "value_claw.json"

    try:
        json_text = json.dumps(new_config, indent=2, ensure_ascii=False)
        cfg_path.write_text(json_text + "\n", encoding="utf-8")
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"Write failed: {exc}"}, status_code=500)

    config.load(str(cfg_path), force=True)
    logger.info("[Web] Config saved to %s", cfg_path)

    _reset_agent()
    if _build_provider_fn:
        try:
            _provider = _build_provider_fn()
            logger.info("[Web] Provider rebuilt successfully.")
        except Exception as exc:
            logger.warning("[Web] Provider rebuild failed: %s", exc)
            _provider = None

    channels_started = await _maybe_start_channels()

    return {
        "ok": True,
        "configPath": str(cfg_path),
        "providerReady": _provider is not None,
        "channelsStarted": channels_started,
    }


async def _api_skills():
    agent = _get_agent()
    if agent is None:
        try:
            pkg_templates = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "templates", "skills",
            )
            skills_dirs = [pkg_templates, os.path.join(str(config.VALUE_CLAW_HOME), "context", "skills")]
            skills_dirs = [d for d in skills_dirs if os.path.isdir(d)]
            registry = SkillRegistry(skills_dirs=skills_dirs)
            skills_meta = registry.discover()
        except Exception:
            return {"total": 0, "categories": {}}
    else:
        registry = agent._registry
        skills_meta = registry.discover()

    categories: dict[str, list] = {}
    for sm in skills_meta:
        cat = sm.category or "uncategorised"
        categories.setdefault(cat, []).append({
            "name": sm.name,
            "description": sm.description,
            "category": cat,
            "path": sm.path,
            "emoji": sm.emoji,
        })

    cat_meta = {}
    for cat_key, cat_obj in registry.categories.items():
        cat_meta[cat_key] = {
            "name": cat_obj.name,
            "description": cat_obj.description,
            "emoji": cat_obj.emoji,
        }

    return {"total": len(skills_meta), "categories": categories, "categoryMeta": cat_meta}


async def _api_status():
    uptime = int(time.time() - _start_time)
    provider_name = config.get_str("llm", "provider", env="LLM_PROVIDER", default="deepseek")

    agent = _get_agent()
    if agent is None:
        return {
            "provider": "Not configured",
            "providerName": provider_name,
            "providerReady": False,
            "skillsLoaded": 0,
            "skillsTotal": 0,
            "memoryCount": 0,
            "historyLength": 0,
            "compactionCount": 0,
            "uptimeSeconds": uptime,
            "webSearchEnabled": False,
        }

    session_file = _store._path(WEB_SESSION_ID) if _store else None
    return {
        "provider": type(agent.provider).__name__,
        "providerName": provider_name,
        "providerReady": True,
        "skillsLoaded": len(agent.loaded_skill_names),
        "skillsTotal": len(agent._registry.discover()),
        "memoryCount": len(agent.memory.list_all()),
        "historyLength": len(agent.messages),
        "compactionCount": agent.compaction_count,
        "uptimeSeconds": uptime,
        "webSearchEnabled": agent._web_search_enabled,
        "sessionFile": session_file,
        "sessionPersistent": True,
    }


async def _api_memories():
    agent = _get_agent()
    if agent is None:
        return {"total": 0, "memories": []}
    memories = agent.memory.list_all()
    return {"total": len(memories), "memories": memories}


async def _api_identity():
    """Return soul, persona content, and the full tool list."""
    from ..core.tools import (
        CRON_TOOLS,
        KNOWLEDGE_TOOL,
        MEMORY_TOOLS,
        META_SKILL_TOOLS,
        PRIMITIVE_TOOLS,
        SKILL_TOOLS,
        WEB_SEARCH_TOOL,
    )

    def _read_md(directory: str) -> str | None:
        p = Path(directory)
        if p.is_file():
            return p.read_text(encoding="utf-8").strip()
        if p.is_dir():
            for f in sorted(p.iterdir()):
                if f.suffix in (".md", ".txt") and f.is_file():
                    return f.read_text(encoding="utf-8").strip()
        return None

    home = config.VALUE_CLAW_HOME
    soul = _read_md(str(home / "context" / "soul"))
    persona = _read_md(str(home / "context" / "persona"))
    tools_notes = _read_md(str(home / "context" / "tools"))
    index_file = home / "context" / "memory" / "INDEX.md"
    index_content = None
    if index_file.is_file():
        try:
            index_content = index_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass

    def _tool_info(schema: dict) -> dict:
        fn = schema.get("function", {})
        return {"name": fn.get("name", ""), "description": fn.get("description", "")}

    tools = []
    tool_groups = [
        ("Primitive", PRIMITIVE_TOOLS),
        ("Skills", SKILL_TOOLS),
        ("Meta", META_SKILL_TOOLS),
        ("Memory", MEMORY_TOOLS),
        ("Cron", CRON_TOOLS),
    ]
    for group, schemas in tool_groups:
        for s in schemas:
            info = _tool_info(s)
            info["group"] = group
            tools.append(info)

    tools.append({**_tool_info(WEB_SEARCH_TOOL), "group": "Search"})
    tools.append({**_tool_info(KNOWLEDGE_TOOL), "group": "Knowledge"})

    return {
        "soul": soul,
        "persona": persona,
        "toolsNotes": tools_notes,
        "indexContent": index_content,
        "soulConfigured": soul is not None,
        "personaConfigured": persona is not None,
        "toolsNotesConfigured": tools_notes is not None,
        "indexConfigured": index_content is not None,
        "tools": tools,
    }


async def _api_save_soul(request: Request):
    """Save soul content to context/soul/SOUL.md and reload agent identity."""
    try:
        body = await request.json()
        content = body.get("content", "").strip()
        if not content:
            return JSONResponse({"ok": False, "error": "Content cannot be empty."}, status_code=400)

        soul_dir = config.VALUE_CLAW_HOME / "context" / "soul"
        soul_dir.mkdir(parents=True, exist_ok=True)
        soul_file = soul_dir / "SOUL.md"
        soul_file.write_text(content + "\n", encoding="utf-8")
        logger.info("[Web] Soul saved to %s", soul_file)

        _reload_agent_identity()
        return {"ok": True, "path": str(soul_file)}
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_save_persona(request: Request):
    """Save persona content to context/persona/persona.md and reload agent identity."""
    try:
        body = await request.json()
        content = body.get("content", "").strip()
        if not content:
            return JSONResponse({"ok": False, "error": "Content cannot be empty."}, status_code=400)

        persona_dir = config.VALUE_CLAW_HOME / "context" / "persona"
        persona_dir.mkdir(parents=True, exist_ok=True)
        persona_file = persona_dir / "persona.md"
        persona_file.write_text(content + "\n", encoding="utf-8")
        logger.info("[Web] Persona saved to %s", persona_file)

        _reload_agent_identity()
        return {"ok": True, "path": str(persona_file)}
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_get_tools_notes():
    """Return the current TOOLS.md content."""
    tools_dir = config.VALUE_CLAW_HOME / "context" / "tools"
    content = None
    if tools_dir.is_dir():
        for f in sorted(tools_dir.iterdir()):
            if f.suffix in (".md", ".txt") and f.is_file():
                content = f.read_text(encoding="utf-8").strip()
                break
    elif tools_dir.is_file():
        content = tools_dir.read_text(encoding="utf-8").strip()
    return {"ok": True, "content": content}


async def _api_save_tools_notes(request: Request):
    """Save TOOLS.md content and reload agent identity."""
    try:
        body = await request.json()
        content = body.get("content", "").strip()

        tools_dir = config.VALUE_CLAW_HOME / "context" / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        tools_file = tools_dir / "TOOLS.md"
        tools_file.write_text(content + "\n", encoding="utf-8")
        logger.info("[Web] TOOLS.md saved to %s", tools_file)

        _reload_agent_identity()
        return {"ok": True, "path": str(tools_file)}
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_get_index():
    """Return the INDEX.md curated system info content."""
    index_path = config.VALUE_CLAW_HOME / "context" / "memory" / "INDEX.md"
    content = ""
    if index_path.is_file():
        try:
            content = index_path.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return {"content": content, "path": str(index_path)}


async def _api_save_index(request: Request):
    """Save INDEX.md content and refresh agent memory."""
    try:
        body = await request.json()
        content = body.get("content", "").strip()
        index_dir = config.VALUE_CLAW_HOME / "context" / "memory"
        index_dir.mkdir(parents=True, exist_ok=True)
        index_file = index_dir / "INDEX.md"
        index_file.write_text(content + "\n", encoding="utf-8")
        logger.info("[Web] INDEX.md saved to %s", index_file)

        agent = _get_agent()
        if agent is not None:
            agent.memory.storage._load()
            agent._init_system_prompt()

        return {"ok": True, "path": str(index_file)}
    except Exception as exc:
        return JSONResponse(
            {"ok": False, "error": str(exc)}, status_code=500
        )


async def _api_transcribe(request: Request):
    """Proxy audio to Deepgram STT and return transcript."""
    from ..core.stt import no_key_message, transcribe_bytes_async

    content_type = request.headers.get("content-type", "audio/webm")
    body = await request.body()
    if not body:
        return JSONResponse({"ok": False, "error": "No audio data received."}, status_code=400)

    try:
        transcript = await transcribe_bytes_async(body, content_type)
    except Exception as exc:
        logger.warning("[Web] Deepgram error: %s", exc)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=502)

    if transcript is None:
        return JSONResponse({"ok": False, "error": no_key_message()}, status_code=400)

    return {"ok": True, "transcript": transcript}


async def _maybe_start_channels() -> list[str]:
    """Start channels whose tokens are now configured but not yet running."""
    global _active_bots
    if _provider is None:
        return []

    wanted = []
    tg_token = config.get_str("channels", "telegram", "token", default="")
    if tg_token:
        wanted.append("telegram")
    dc_token = config.get_str("channels", "discord", "token", default="")
    if dc_token:
        wanted.append("discord")

    if not wanted:
        return []

    running_types = set()
    for bot in _active_bots:
        cls_name = type(bot).__name__.lower()
        if "telegram" in cls_name:
            running_types.add("telegram")
        elif "discord" in cls_name:
            running_types.add("discord")

    to_start = [ch for ch in wanted if ch not in running_types]
    if not to_start:
        return list(running_types)

    try:
        from ..server import start_channels
        new_bots = await start_channels(_provider, to_start, fastapi_app=_fastapi_app)
        _active_bots.extend(new_bots)
        return [ch for ch in wanted if ch in running_types or ch in to_start]
    except Exception as exc:
        logger.warning("[Web] Channel start failed: %s", exc)
        return list(running_types)


async def _api_channels_status():
    """Return status of messaging channels."""
    channels = []
    for bot in _active_bots:
        cls_name = type(bot).__name__
        if "Telegram" in cls_name:
            ch_type = "telegram"
        elif "Discord" in cls_name:
            ch_type = "discord"
        else:
            ch_type = cls_name
        channels.append({"type": ch_type, "running": True})

    running_types = {c["type"] for c in channels}

    tg_token = config.get_str("channels", "telegram", "token", default="")
    dc_token = config.get_str("channels", "discord", "token", default="")

    if tg_token and "telegram" not in running_types:
        channels.append({"type": "telegram", "running": False, "tokenSet": True})
    if dc_token and "discord" not in running_types:
        channels.append({"type": "discord", "running": False, "tokenSet": True})

    return {"channels": channels}


async def _api_channels_restart(request: Request):
    """Stop and restart all configured channels."""
    global _active_bots

    for bot in _active_bots:
        if hasattr(bot, "stop_async"):
            try:
                await bot.stop_async()
            except Exception:
                pass
    _active_bots = []

    started = await _maybe_start_channels()
    return {"ok": True, "channels": started}


def _reload_agent_identity() -> None:
    """Reload the agent's soul/persona/tools from disk without full reset."""
    global _agent
    if _agent is None:
        return
    from ..core.agent import _load_text_dir_or_file
    home = config.VALUE_CLAW_HOME
    _agent.soul_instruction = _load_text_dir_or_file(
        str(home / "context" / "soul"), label="Soul"
    )
    _agent.persona_instruction = _load_text_dir_or_file(
        str(home / "context" / "persona"), label="Persona"
    )
    _agent.tools_notes = _load_text_dir_or_file(
        str(home / "context" / "tools"), label="Tools"
    )
    _agent._needs_onboarding = False
    _agent._init_system_prompt()


# ── Files management ──────────────────────────────────────────────────────────

async def _api_clear_files(request: Request):
    """Delete all downloaded/generated files."""
    count = config.clear_files()
    return JSONResponse({"ok": True, "cleared": count})


async def _api_list_files(request: Request):
    """List files in the shared files directory."""
    d = config.files_dir()
    files = []
    for entry in sorted(d.iterdir()):
        if entry.is_file():
            files.append({
                "name": entry.name,
                "size": entry.stat().st_size,
                "modified": entry.stat().st_mtime,
            })
    return JSONResponse({"files": files, "dir": str(d)})


# ── Portfolio API ─────────────────────────────────────────────────────────

async def _api_portfolio_status():
    from ..core.portfolio import get_status
    return {"ok": True, **get_status()}


async def _api_portfolio_switch(request: Request):
    try:
        body = await request.json()
        pid = body.get("portfolio_id", "").strip()
        from ..core.portfolio import switch_portfolio
        result = switch_portfolio(pid)
        return result
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_portfolio_mode(request: Request):
    try:
        body = await request.json()
        mode = body.get("mode", "").strip()
        from ..core.portfolio import switch_mode
        result = switch_mode(mode)
        return result
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_portfolio_topup(request: Request):
    try:
        body = await request.json()
        amount = float(body.get("amount", 0))
        from ..core.portfolio import top_up
        result = top_up(
            amount,
            portfolio_id=body.get("portfolio_id"),
            mode=body.get("mode"),
        )
        return result
    except (ValueError, TypeError) as exc:
        return JSONResponse({"ok": False, "error": f"Invalid input: {exc}"}, status_code=400)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_portfolio_cashout(request: Request):
    try:
        body = await request.json()
        amount = float(body.get("amount", 0))
        from ..core.portfolio import cash_out
        result = cash_out(
            amount,
            portfolio_id=body.get("portfolio_id"),
            mode=body.get("mode"),
        )
        return result
    except (ValueError, TypeError) as exc:
        return JSONResponse({"ok": False, "error": f"Invalid input: {exc}"}, status_code=400)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_portfolio_detail(pid: str, request: Request):
    mode = request.query_params.get("mode")
    from ..core.portfolio import get_portfolio_detail
    data = get_portfolio_detail(pid, mode=mode)
    if data is None:
        return JSONResponse({"ok": False, "error": f"Portfolio '{pid}' not found."}, status_code=404)
    return {"ok": True, **data}


async def _api_portfolio_get_allowed(pid: str):
    from ..core.portfolio import get_allowed_symbols
    return get_allowed_symbols(portfolio_id=pid)


async def _api_portfolio_set_allowed(pid: str, request: Request):
    try:
        body = await request.json()
        symbols = body.get("symbols", [])
        if not isinstance(symbols, list):
            return JSONResponse({"ok": False, "error": "symbols must be a list."}, status_code=400)
        from ..core.portfolio import set_allowed_symbols
        return set_allowed_symbols(symbols, portfolio_id=pid)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_portfolio_add_allowed(pid: str, symbol: str):
    from ..core.portfolio import add_allowed_symbol
    return add_allowed_symbol(symbol, portfolio_id=pid)


async def _api_portfolio_remove_allowed(pid: str, symbol: str):
    from ..core.portfolio import remove_allowed_symbol
    return remove_allowed_symbol(symbol, portfolio_id=pid)


async def _api_portfolio_add_holding(pid: str, request: Request):
    try:
        body = await request.json()
        symbol = body.get("symbol", "").strip().upper()
        quantity = float(body.get("quantity", 0))
        cost_basis = float(body.get("cost_basis", 0))
        if not symbol or quantity <= 0:
            return JSONResponse({"ok": False, "error": "symbol and quantity > 0 required."}, status_code=400)
        from ..core.portfolio import add_holding
        result = add_holding(symbol, quantity, cost_basis, portfolio_id=pid, mode=body.get("mode"))
        if not result.get("ok"):
            return JSONResponse(result, status_code=400)
        return result
    except (ValueError, TypeError) as exc:
        return JSONResponse({"ok": False, "error": f"Invalid input: {exc}"}, status_code=400)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_portfolio_remove_holding(pid: str, symbol: str, request: Request):
    mode = request.query_params.get("mode")
    from ..core.portfolio import remove_holding
    result = remove_holding(symbol.upper(), portfolio_id=pid, mode=mode)
    return result


async def _api_portfolio_snapshots(pid: str, request: Request):
    days = int(request.query_params.get("days", 30))
    mode = request.query_params.get("mode")
    from ..core.portfolio import get_snapshots, _load_state
    if mode is None:
        state = _load_state()
        mode = state.active_mode
    return {"ok": True, "portfolio_id": pid, "mode": mode, "snapshots": get_snapshots(pid, mode=mode, days=days)}


async def _api_portfolio_take_snapshot(pid: str, request: Request):
    mode = request.query_params.get("mode")
    from ..core.portfolio import take_snapshot, _load_state
    if mode is None:
        state = _load_state()
        mode = state.active_mode
    snap = take_snapshot(pid, mode=mode)
    if snap is None:
        return JSONResponse({"ok": False, "error": "Portfolio empty or not found."}, status_code=404)
    from dataclasses import asdict
    return {"ok": True, "snapshot": asdict(snap)}


async def _api_portfolio_buy(request: Request):
    """Execute a buy trade via the API."""
    try:
        body = await request.json()
        from ..core.portfolio import buy
        result = buy(
            symbol=body.get("symbol", ""),
            quantity=float(body.get("quantity", 0)),
            price=float(body.get("price", 0)),
            portfolio_id=body.get("portfolio_id"),
            mode=body.get("mode"),
            thesis=body.get("thesis", ""),
        )
        if not result.get("ok"):
            return JSONResponse(result, status_code=400)
        return result
    except (ValueError, TypeError) as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


async def _api_portfolio_sell(request: Request):
    """Execute a sell trade via the API."""
    try:
        body = await request.json()
        from ..core.portfolio import sell
        result = sell(
            symbol=body.get("symbol", ""),
            quantity=float(body.get("quantity", 0)),
            price=float(body.get("price", 0)),
            portfolio_id=body.get("portfolio_id"),
            mode=body.get("mode"),
            thesis=body.get("thesis", ""),
        )
        if not result.get("ok"):
            return JSONResponse(result, status_code=400)
        return result
    except (ValueError, TypeError) as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


async def _api_portfolio_trades(pid: str, request: Request):
    """Get trade history for a portfolio."""
    mode = request.query_params.get("mode")
    limit = int(request.query_params.get("limit", "50"))
    from ..core.portfolio import get_trades
    trades = get_trades(pid, mode, limit)
    return {"ok": True, "trades": trades}


async def _api_portfolio_performance(pid: str, request: Request):
    """Get performance metrics for a portfolio."""
    mode = request.query_params.get("mode")
    days = int(request.query_params.get("days", "90"))
    from ..core.portfolio import get_performance
    return get_performance(pid, mode, days)


# ── Cron / Prefect API ────────────────────────────────────────────────────

def _get_scheduler():
    from ..server import get_scheduler
    return get_scheduler()


async def _api_cron_list_jobs():
    """List all scheduled jobs with metadata and last run info."""
    sched = _get_scheduler()
    if sched is None:
        return JSONResponse({"ok": False, "error": "Scheduler not running."}, status_code=503)
    return {"ok": True, "jobs": sched.get_jobs_detail(), "prefect_ui": sched.prefect_ui_url}


async def _api_cron_add_job(request: Request):
    """Add a new dynamic cron job."""
    sched = _get_scheduler()
    if sched is None:
        return JSONResponse({"ok": False, "error": "Scheduler not running."}, status_code=503)
    try:
        body = await request.json()
        job_id = body.get("job_id", "").strip()
        cron_expr = body.get("cron", "").strip()
        prompt = body.get("prompt", "").strip()
        if not job_id or not cron_expr or not prompt:
            return JSONResponse(
                {"ok": False, "error": "job_id, cron, and prompt are required."}, status_code=400,
            )
        result = sched.add_dynamic_job(
            job_id=job_id,
            cron_expr=cron_expr,
            prompt=prompt,
            deliver_to=body.get("deliver_to"),
            chat_id=body.get("chat_id"),
        )
        return {"ok": True, "message": result}
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_cron_update_job(job_id: str, request: Request):
    """Update an existing dynamic cron job (schedule, prompt, or delivery)."""
    sched = _get_scheduler()
    if sched is None:
        return JSONResponse({"ok": False, "error": "Scheduler not running."}, status_code=503)
    try:
        body = await request.json()
        result = sched.update_dynamic_job(
            job_id=job_id,
            cron_expr=body.get("cron"),
            prompt=body.get("prompt"),
            deliver_to=body.get("deliver_to"),
            chat_id=body.get("chat_id"),
        )
        return {"ok": True, "message": result}
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_cron_remove_job(job_id: str):
    """Remove a scheduled job."""
    sched = _get_scheduler()
    if sched is None:
        return JSONResponse({"ok": False, "error": "Scheduler not running."}, status_code=503)
    result = sched.remove_dynamic_job(job_id)
    return {"ok": True, "message": result}


async def _api_cron_trigger_job(job_id: str):
    """Manually trigger a job immediately."""
    sched = _get_scheduler()
    if sched is None:
        return JSONResponse({"ok": False, "error": "Scheduler not running."}, status_code=503)
    result = await sched.trigger_job(job_id)
    return {"ok": True, "message": result}


async def _api_cron_job_runs(job_id: str, request: Request):
    """Get recent Prefect flow runs for a specific job."""
    sched = _get_scheduler()
    if sched is None:
        return JSONResponse({"ok": False, "error": "Scheduler not running."}, status_code=503)
    max_results = int(request.query_params.get("limit", 20))
    runs = sched.get_job_runs(job_id, max_results=max_results)
    return {"ok": True, "job_id": job_id, "runs": runs}


async def _api_cron_all_runs(request: Request):
    """Get recent runs across all jobs."""
    sched = _get_scheduler()
    if sched is None:
        return JSONResponse({"ok": False, "error": "Scheduler not running."}, status_code=503)
    max_results = int(request.query_params.get("limit", 50))
    runs = sched.get_all_runs(max_results=max_results)
    return {"ok": True, "runs": runs}


async def _api_cron_reload():
    """Hot-reload all jobs from config files."""
    sched = _get_scheduler()
    if sched is None:
        return JSONResponse({"ok": False, "error": "Scheduler not running."}, status_code=503)
    count = sched.reload_jobs()
    return {"ok": True, "jobs_loaded": count}


async def _api_prefect_status():
    """Get Prefect server status and UI URL."""
    sched = _get_scheduler()
    if sched is None:
        return JSONResponse({"ok": False, "error": "Scheduler not running."}, status_code=503)
    return {"ok": True, **sched.prefect_status()}


# ── Web file sender ───────────────────────────────────────────────────────────

def _register_web_file_sender(loop: asyncio.AbstractEventLoop, ws: WebSocket) -> None:
    """Register a sync callback so the Agent can push file-download links to the web UI."""
    from ..core.tools import set_file_sender

    def _sender(path: str, caption: str = "") -> None:
        import base64 as _b64

        name = os.path.basename(path)
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            data = _b64.b64encode(fh.read()).decode()

        async def _push():
            try:
                await ws.send_json({
                    "type": "file",
                    "filename": name,
                    "size": size,
                    "caption": caption,
                    "data": data,
                })
            except Exception as exc:
                logger.warning("[Web] send_file via WS failed: %s", exc)

        future = asyncio.run_coroutine_threadsafe(_push(), loop)
        future.result(timeout=60)

    set_file_sender(_sender)


# ── Analytics / Database API ──────────────────────────────────────────────────

async def _api_daily_values(request: Request):
    from ..db import get_daily_values, is_initialized
    if not is_initialized():
        return {"ok": True, "data": [], "db_enabled": False}
    pid = request.query_params.get("portfolio_id", "us-stocks")
    mode = request.query_params.get("mode", "simulate")
    days = int(request.query_params.get("days", "90"))
    data = get_daily_values(pid, mode, days)
    return {"ok": True, "data": data, "db_enabled": True}


async def _api_analytics_trades(request: Request):
    from ..db import get_trades_from_db, is_initialized
    if not is_initialized():
        return {"ok": True, "trades": [], "db_enabled": False}
    pid = request.query_params.get("portfolio_id")
    mode = request.query_params.get("mode")
    sid = request.query_params.get("strategy_id")
    limit = int(request.query_params.get("limit", "100"))
    offset = int(request.query_params.get("offset", "0"))
    trades = get_trades_from_db(pid, mode, sid, limit, offset)
    return {"ok": True, "trades": trades, "db_enabled": True}


async def _api_analytics_events(request: Request):
    from ..db import get_portfolio_events, is_initialized
    if not is_initialized():
        return {"ok": True, "events": [], "db_enabled": False}
    pid = request.query_params.get("portfolio_id")
    event_type = request.query_params.get("event_type")
    limit = int(request.query_params.get("limit", "100"))
    events = get_portfolio_events(pid, event_type, limit)
    return {"ok": True, "events": events, "db_enabled": True}


async def _api_analytics_strategy_events(request: Request):
    from ..db import get_strategy_events, is_initialized
    if not is_initialized():
        return {"ok": True, "events": [], "db_enabled": False}
    sid = request.query_params.get("strategy_id")
    limit = int(request.query_params.get("limit", "100"))
    events = get_strategy_events(sid, limit)
    return {"ok": True, "events": events, "db_enabled": True}


async def _api_db_status():
    from ..db import is_initialized
    return {"ok": True, "db_enabled": is_initialized()}


async def _serve_dashboard():
    dashboard_path = Path(__file__).parent / "static" / "dashboard.html"
    if not dashboard_path.exists():
        return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)
    return HTMLResponse(dashboard_path.read_text(encoding="utf-8"))


# ── Strategy API ──────────────────────────────────────────────────────────────

async def _api_strategy_list():
    from ..core.strategy import list_strategies
    return {"ok": True, "strategies": list_strategies()}


async def _api_strategy_get(sid: str):
    from ..core.strategy import get_strategy, get_strategy_trades, list_pending_trades
    from dataclasses import asdict
    strat = get_strategy(sid)
    if not strat:
        return JSONResponse({"ok": False, "error": f"Strategy '{sid}' not found."}, status_code=404)
    info = asdict(strat)
    info["recent_trades"] = get_strategy_trades(sid, limit=10)
    info["pending_trades"] = list_pending_trades(sid)
    return {"ok": True, "strategy": info}


async def _api_strategy_create(request: Request):
    from ..core.strategy import register_strategy
    try:
        body = await request.json()
        result = register_strategy(
            strategy_id=body.get("id", "").strip(),
            name=body.get("name", "").strip(),
            strategy_type=body.get("type", "prompt"),
            portfolio_id=body.get("portfolio_id", "us-stocks"),
            schedule=body.get("schedule", "").strip(),
            execution_mode=body.get("execution_mode", "approval"),
            script_path=body.get("script_path"),
            prompt_template=body.get("prompt_template"),
            n8n_workflow_id=body.get("n8n_workflow_id"),
            params=body.get("params", {}),
        )
        if not result.get("ok"):
            return JSONResponse(result, status_code=400)
        return result
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_strategy_update(sid: str, request: Request):
    from ..core.strategy import update_strategy
    try:
        body = await request.json()
        result = update_strategy(
            strategy_id=sid,
            name=body.get("name"),
            schedule=body.get("schedule"),
            execution_mode=body.get("execution_mode"),
            prompt_template=body.get("prompt_template"),
            script_path=body.get("script_path"),
            n8n_workflow_id=body.get("n8n_workflow_id"),
            params=body.get("params"),
        )
        if not result.get("ok"):
            return JSONResponse(result, status_code=400)
        return result
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_strategy_delete(sid: str):
    from ..core.strategy import unregister_strategy
    result = unregister_strategy(sid)
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    return result


async def _api_strategy_start(sid: str):
    from ..core.strategy import get_strategy, set_strategy_status
    strat = get_strategy(sid)
    if not strat:
        return JSONResponse({"ok": False, "error": f"Strategy '{sid}' not found."}, status_code=404)
    if strat.status == "running":
        return JSONResponse({"ok": False, "error": f"Strategy '{sid}' is already running."}, status_code=400)
    sched = _get_scheduler()
    if sched:
        try:
            sched.register_strategy_job(sid, strat.schedule)
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    set_strategy_status(sid, "running")
    return {"ok": True, "strategy_id": sid, "status": "running"}


async def _api_strategy_stop(sid: str):
    from ..core.strategy import get_strategy, set_strategy_status
    strat = get_strategy(sid)
    if not strat:
        return JSONResponse({"ok": False, "error": f"Strategy '{sid}' not found."}, status_code=404)
    if strat.status == "stopped":
        return JSONResponse({"ok": False, "error": f"Strategy '{sid}' is already stopped."}, status_code=400)
    sched = _get_scheduler()
    if sched:
        sched.remove_strategy_job(sid)
    set_strategy_status(sid, "stopped")
    return {"ok": True, "strategy_id": sid, "status": "stopped"}


async def _api_strategy_trigger(sid: str):
    sched = _get_scheduler()
    if not sched:
        return JSONResponse({"ok": False, "error": "Scheduler not running."}, status_code=503)
    result = await sched.trigger_strategy(sid)
    import json as _json
    return _json.loads(result)


async def _api_strategy_pending(request: Request):
    from ..core.strategy import list_pending_trades
    sid = request.query_params.get("strategy_id")
    return {"ok": True, "pending_trades": list_pending_trades(sid)}


async def _api_strategy_approve(trade_id: str):
    from ..core.strategy import approve_trade
    result = approve_trade(trade_id)
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    return result


async def _api_strategy_reject(trade_id: str):
    from ..core.strategy import reject_trade
    result = reject_trade(trade_id)
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    return result


# ── WebSocket Chat ────────────────────────────────────────────────────────────

async def _ws_chat(websocket: WebSocket):
    await websocket.accept()
    logger.info("[Web] WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                message = payload.get("message", "").strip()
                image_data = payload.get("image")  # data:image/...;base64,...
            except (json.JSONDecodeError, AttributeError):
                message = data.strip()
                image_data = None

            if not message and not image_data:
                continue

            agent = _get_agent()
            if agent is None:
                await websocket.send_json({
                    "type": "error",
                    "content": "LLM provider is not configured yet. Go to the Config tab and set your API key, then save.",
                })
                continue

            if message.startswith("/compact"):
                hint = message[len("/compact"):].strip() or None
                result = agent.compact(instruction=hint)
                await websocket.send_json({"type": "response", "content": result})
                continue

            if message == "/status":
                status = await _api_status()
                await websocket.send_json({"type": "response", "content": json.dumps(status, indent=2)})
                continue

            if message == "/clear":
                if _store:
                    _store.delete(WEB_SESSION_ID)
                if agent is not None:
                    agent.clear_history()
                await websocket.send_json({"type": "response", "content": "Chat history cleared. Agent is still active with all skills and memory intact."})
                continue

            lock = _get_chat_lock()
            if lock.locked():
                await websocket.send_json({"type": "thinking", "content": "Processing previous message\u2026"})
            else:
                await websocket.send_json({"type": "thinking", "content": ""})

            loop = asyncio.get_event_loop()

            _register_web_file_sender(loop, websocket)

            try:
                token_queue: asyncio.Queue[str | None] = asyncio.Queue()

                def _on_token(text: str) -> None:
                    loop.call_soon_threadsafe(token_queue.put_nowait, text)

                async def _stream_tokens() -> None:
                    while True:
                        tok = await token_queue.get()
                        if tok is None:
                            break
                        try:
                            await websocket.send_json(
                                {"type": "stream", "content": tok}
                            )
                        except Exception:
                            break

                # Build multimodal input if image is attached
                chat_input: str | list = message or ""
                if image_data:
                    chat_input = [
                        {"type": "text", "text": message or "What is in this image?"},
                        {"type": "image_url", "image_url": {"url": image_data}},
                    ]

                async with lock:
                    stream_task = asyncio.create_task(_stream_tokens())
                    try:
                        response = await loop.run_in_executor(
                            None, agent.chat_stream, chat_input, _on_token
                        )
                    finally:
                        loop.call_soon_threadsafe(
                            token_queue.put_nowait, None
                        )
                        await stream_task
                await websocket.send_json(
                    {"type": "response", "content": response}
                )
            except Exception as exc:
                logger.exception("[Web] Chat error")
                await websocket.send_json({"type": "error", "content": str(exc)})

    except WebSocketDisconnect:
        logger.info("[Web] WebSocket client disconnected")
    except Exception:
        logger.exception("[Web] WebSocket error")
