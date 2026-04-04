"""
Interactive onboarding wizard for value_claw.

Guides a new user through LLM provider selection, API key entry,
fallback configuration, search services, channels, and skill tokens.
Writes value_claw.json.
"""

from __future__ import annotations

import getpass
import json
from pathlib import Path

from . import config

# ── ANSI helpers (no external deps) ──────────────────────────────────────────

_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_RESET = "\033[0m"


def _c(text: str, color: str) -> str:
    return f"{color}{text}{_RESET}"


def _heading(text: str) -> None:
    print()
    print(_c(f"  ── {text} ──", _CYAN))
    print()


def _yes_no(prompt: str, default: bool = False) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    ans = input(f"  {prompt} {hint}: ").strip().lower()
    if not ans:
        return default
    return ans in ("y", "yes")


# ── Provider definitions ─────────────────────────────────────────────────────

PROVIDERS = [
    {
        "key": "deepseek",
        "name": "DeepSeek",
        "default_model": "deepseek-chat",
        "default_base": "https://api.deepseek.com/v1",
        "env": "DEEPSEEK_API_KEY",
    },
    {
        "key": "grok",
        "name": "Grok (xAI)",
        "default_model": "grok-3",
        "default_base": "https://api.x.ai/v1",
        "env": "GROK_API_KEY",
    },
    {
        "key": "claude",
        "name": "Claude (Anthropic) — API key or OAuth token",
        "default_model": "claude-sonnet-4-6",
        "default_base": None,
        "env": "ANTHROPIC_API_KEY",
    },
    {
        "key": "gemini",
        "name": "Gemini (Google)",
        "default_model": "gemini-2.0-flash",
        "default_base": None,
        "env": "GEMINI_API_KEY",
    },
    {
        "key": "kimi",
        "name": "Kimi (Moonshot)",
        "default_model": "moonshot-v1-128k",
        "default_base": "https://api.moonshot.cn/v1",
        "env": "KIMI_API_KEY",
    },
    {
        "key": "glm",
        "name": "GLM (Zhipu / ChatGLM)",
        "default_model": "glm-4-flash",
        "default_base": "https://open.bigmodel.cn/api/paas/v4/",
        "env": "GLM_API_KEY",
    },
]

_PROVIDER_BY_KEY = {p["key"]: p for p in PROVIDERS}


# ── Core logic ───────────────────────────────────────────────────────────────

def run_onboard(config_path: str | None = None) -> Path:
    """Run the interactive onboarding wizard.  Returns path to saved config."""
    print()
    print(_c("  ╔══════════════════════════════════════╗", _CYAN))
    print(_c("  ║       value_claw — Setup Wizard      ║", _CYAN))
    print(_c("  ╚══════════════════════════════════════╝", _CYAN))
    print()

    cfg = _load_existing(config_path)

    # 1. Primary LLM
    provider = _choose_provider(cfg, "Choose your PRIMARY LLM provider:")
    api_key = _get_api_key(provider, cfg)

    prov = provider["key"]
    cfg.setdefault("llm", {})
    cfg["llm"]["provider"] = prov
    cfg["llm"].setdefault(prov, {})
    cfg["llm"][prov]["apiKey"] = api_key
    cfg["llm"][prov].setdefault("model", provider["default_model"])
    if provider["default_base"]:
        cfg["llm"][prov].setdefault("baseUrl", provider["default_base"])

    # 2. Fallback LLM
    _configure_fallback(cfg, provider)

    # 3. Search services
    _search_services(cfg)

    # 4. Channels
    _channel_keys(cfg)

    # 5. Skill tokens
    _skill_tokens(cfg)

    # 6. Validate primary
    _validate_key(cfg, provider)

    # 7. Save
    out_path = _save_config(cfg, config_path)

    print()
    print(_c("  ✔ Setup complete!", _GREEN))
    print(f"    Config saved to: {_c(str(out_path), _BOLD)}")
    print(f"    97 skills across 17 categories ready to use.")
    print()
    return out_path


def _load_existing(config_path: str | None) -> dict:
    try:
        config.load(config_path)
        return config.as_dict()
    except Exception:
        return {}


# ── Provider selection ────────────────────────────────────────────────────────

def _choose_provider(cfg: dict, title: str) -> dict:
    current = cfg.get("llm", {}).get("provider", "")
    print(_c(f"  {title}", _BOLD))
    print()
    for i, p in enumerate(PROVIDERS, 1):
        marker = _c(" (current)", _DIM) if p["key"] == current else ""
        print(f"    {_c(str(i), _CYAN)}. {p['name']}{marker}")
    print()

    while True:
        default_hint = ""
        if current:
            idx = next((i for i, p in enumerate(PROVIDERS) if p["key"] == current), None)
            if idx is not None:
                default_hint = f" [{idx + 1}]"

        choice = input(f"  Enter number (1-{len(PROVIDERS)}){default_hint}: ").strip()
        if not choice and current:
            return next(p for p in PROVIDERS if p["key"] == current)
        try:
            n = int(choice)
            if 1 <= n <= len(PROVIDERS):
                selected = PROVIDERS[n - 1]
                print(f"  → {_c(selected['name'], _GREEN)}")
                print()
                return selected
        except ValueError:
            pass
        print(_c("  Invalid choice, try again.", _RED))


def _get_api_key(provider: dict, cfg: dict) -> str:
    existing = cfg.get("llm", {}).get(provider["key"], {}).get("apiKey", "")
    has_existing = bool(existing) and existing != ""

    hint = ""
    if has_existing:
        masked = existing[:4] + "****" + existing[-4:] if len(existing) > 8 else "****"
        hint = f" (current: {masked}, press Enter to keep)"

    if provider["key"] == "claude":
        print(f"  {provider['name']} Authentication{hint}")
        print(_c("    Supports:", _DIM))
        print(_c("      • API key:     sk-ant-api03-...  (standard Anthropic API key)", _DIM))
        print(_c("      • OAuth token: sk-ant-oat01-...  (from Claude Code / Max subscription)", _DIM))
    else:
        print(f"  {provider['name']} API Key{hint}")

    key = getpass.getpass("  API Key / Token: ").strip()

    if not key and has_existing:
        print("  → Keeping existing key")
        return existing
    if not key:
        print(_c("  API key is required.", _RED))
        return _get_api_key(provider, cfg)

    if provider["key"] == "claude":
        if "oat" in key[:20]:
            print(f"  → OAuth token set ({key[:12]}****)")
            print(_c("    Will use Claude Code-compatible auth headers", _DIM))
        elif key.startswith("sk-ant-"):
            print(f"  → API key set ({key[:10]}****)")
        else:
            print(f"  → Token set ({key[:4]}****)")
    else:
        print(f"  → Key set ({key[:4]}****)")
    print()
    return key


# ── Fallback LLM ──────────────────────────────────────────────────────────────

def _configure_fallback(cfg: dict, primary: dict) -> None:
    _heading("Fallback LLM (Optional)")
    print(_c("    When the primary LLM fails (rate limit, quota, errors),", _DIM))
    print(_c("    ValueClaw can automatically switch to a fallback provider.", _DIM))
    print()

    current_fallback = cfg.get("llm", {}).get("fallback", "")
    if current_fallback:
        print(f"    Current fallback: {_c(current_fallback, _GREEN)}")

    if not _yes_no("Configure a fallback LLM?", default=bool(current_fallback)):
        cfg.setdefault("llm", {})["fallback"] = ""
        return

    others = [p for p in PROVIDERS if p["key"] != primary["key"]]
    print()
    for i, p in enumerate(others, 1):
        marker = _c(" (current)", _DIM) if p["key"] == current_fallback else ""
        print(f"    {_c(str(i), _CYAN)}. {p['name']}{marker}")
    print()

    while True:
        choice = input(f"  Fallback provider (1-{len(others)}, Enter to skip): ").strip()
        if not choice:
            if current_fallback:
                cfg["llm"]["fallback"] = current_fallback
                print(f"  → Keeping {current_fallback}")
            return
        try:
            n = int(choice)
            if 1 <= n <= len(others):
                fb = others[n - 1]
                break
        except ValueError:
            pass
        print(_c("  Invalid choice, try again.", _RED))

    cfg["llm"]["fallback"] = fb["key"]
    print(f"  → Fallback: {_c(fb['name'], _GREEN)}")

    fb_existing = cfg.get("llm", {}).get(fb["key"], {}).get("apiKey", "")
    if not fb_existing:
        fb_key = _get_api_key(fb, cfg)
        cfg["llm"].setdefault(fb["key"], {})
        cfg["llm"][fb["key"]]["apiKey"] = fb_key
        cfg["llm"][fb["key"]].setdefault("model", fb["default_model"])
        if fb["default_base"]:
            cfg["llm"][fb["key"]].setdefault("baseUrl", fb["default_base"])
    else:
        masked = fb_existing[:4] + "****" + fb_existing[-4:] if len(fb_existing) > 8 else "****"
        print(f"  → Fallback key already configured ({masked})")
    print()


# ── Search services ───────────────────────────────────────────────────────────

def _search_services(cfg: dict) -> None:
    _heading("Search Services (Optional)")

    _prompt_optional_key(cfg, ["tavily", "apiKey"],
                         "Tavily API Key", "(financial web search with topic filters)")
    _prompt_optional_key(cfg, ["brave", "apiKey"],
                         "Brave Search API Key", "(unbiased web search)")
    _prompt_optional_key(cfg, ["perplexity", "apiKey"],
                         "Perplexity API Key", "(sonar-pro deep research)")
    _prompt_optional_key(cfg, ["deepgram", "apiKey"],
                         "Deepgram API Key", "(voice input)")


# ── Channels ──────────────────────────────────────────────────────────────────

def _channel_keys(cfg: dict) -> None:
    _heading("Channels")

    channels = cfg.setdefault("channels", {})

    # Telegram
    tg = channels.setdefault("telegram", {"token": "", "allowedUsers": [], "allowedGroups": []})
    _prompt_optional_key(cfg, ["channels", "telegram", "token"],
                         "Telegram Bot Token", "(from @BotFather)")
    if tg.get("token"):
        allowed = input("  Telegram Allowed User IDs (comma-separated, Enter = all): ").strip()
        if allowed:
            tg["allowedUsers"] = [uid.strip() for uid in allowed.split(",") if uid.strip()]
            print(f"  → {len(tg['allowedUsers'])} user(s) whitelisted")

        groups = input("  Telegram Allowed Group IDs (comma-separated, Enter = none): ").strip()
        if groups:
            tg["allowedGroups"] = [gid.strip() for gid in groups.split(",") if gid.strip()]
            print(f"  → {len(tg['allowedGroups'])} group(s) whitelisted")
        print()

    # Discord
    channels.setdefault("discord", {"token": "", "allowedUsers": [], "allowedChannels": []})
    _prompt_optional_key(cfg, ["channels", "discord", "token"],
                         "Discord Bot Token", "")

    dc = channels["discord"]
    if dc.get("token"):
        dc_channels = input("  Discord Allowed Channel IDs (comma-separated, Enter = all): ").strip()
        if dc_channels:
            dc["allowedChannels"] = [ch.strip() for ch in dc_channels.split(",") if ch.strip()]
            print(f"  → {len(dc['allowedChannels'])} channel(s) whitelisted")
        print()


# ── Skill tokens ──────────────────────────────────────────────────────────────

def _skill_tokens(cfg: dict) -> None:
    _heading("Skill Tokens (Optional)")
    print(_c("    These enable specific skills. Press Enter to skip any.", _DIM))
    print()

    skills = cfg.setdefault("skills", {})

    # Twitter
    tw = skills.setdefault("twitter", {})
    tw_existing = tw.get("bearerToken", "")
    if not tw_existing:
        if _yes_no("Configure Twitter API keys? (for twitter-post & twitter-news)", default=False):
            tw["bearerToken"] = input("    Bearer Token: ").strip()
            tw["apiKey"] = input("    API Key: ").strip()
            tw["apiSecret"] = getpass.getpass("    API Secret: ").strip()
            tw["accessToken"] = input("    Access Token: ").strip()
            tw["accessTokenSecret"] = getpass.getpass("    Access Token Secret: ").strip()
            if tw["bearerToken"]:
                print(_c("  → Twitter keys configured", _GREEN))
            print()
    else:
        masked = tw_existing[:6] + "****" if len(tw_existing) > 10 else "****"
        print(f"  Twitter: already configured ({masked})")

    # Tushare
    _prompt_optional_key(cfg, ["skills", "tushare", "token"],
                         "Tushare Token", "(China A-share data)")

    # n8n
    _prompt_optional_key(cfg, ["skills", "n8n", "apiKey"],
                         "n8n API Key", "(workflow automation)")

    # Interactive Brokers
    ib = skills.setdefault("interactiveBrokers", {
        "host": "127.0.0.1", "port": 7497, "clientId": 1, "paperTrading": True,
    })
    ib_existing = ib.get("host", "")
    if ib_existing and ib_existing != "127.0.0.1":
        print(f"  Interactive Brokers: configured ({ib_existing}:{ib.get('port', 7497)})")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prompt_optional_key(cfg: dict, path: list[str], label: str, desc: str) -> None:
    """Prompt for an optional key at a nested config path."""
    node = cfg
    for k in path[:-1]:
        node = node.setdefault(k, {})
    key_name = path[-1]
    existing = node.get(key_name, "")
    has_existing = bool(existing) and existing != ""

    if has_existing:
        masked = existing[:4] + "****" + existing[-4:] if len(existing) > 8 else "****"
        prompt = f"  {label} {desc} (current: {masked}, Enter to keep): "
    else:
        prompt = f"  {label} {desc}: "

    val = input(prompt).strip()
    if val:
        node[key_name] = val
        print(f"  → {label} set")
    elif has_existing:
        pass  # keep existing


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_key(cfg: dict, provider: dict) -> None:
    """Make a quick test call to validate the API key."""
    prov_key = provider["key"]
    api_key = cfg["llm"][prov_key]["apiKey"]

    is_oauth = prov_key == "claude" and "oat" in api_key[:20]
    label = "OAuth token" if is_oauth else "API key"
    print(f"  Validating {provider['name']} {label}...", end=" ", flush=True)

    try:
        if prov_key in ("deepseek", "grok", "kimi", "glm"):
            from .core.llm.openai_compatible import OpenAICompatibleProvider
            base_url = cfg["llm"][prov_key].get("baseUrl", provider["default_base"])
            model = cfg["llm"][prov_key].get("model", provider["default_model"])
            p = OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model_name=model)
            p.chat([{"role": "user", "content": "hi"}], max_tokens=5)
        elif prov_key == "claude":
            from .core.llm.anthropic_client import AnthropicProvider
            model = cfg["llm"][prov_key].get("model", provider["default_model"])
            p = AnthropicProvider(api_key=api_key, model_name=model)
            p.chat([{"role": "user", "content": "hi"}], max_tokens=16384 if is_oauth else 5)
        elif prov_key == "gemini":
            from .core.llm.gemini_client import GeminiProvider
            p = GeminiProvider(api_key=api_key)
            p.chat([{"role": "user", "content": "hi"}], max_tokens=5)
        else:
            print(_c("skipped (unknown provider type)", _YELLOW))
            return

        auth_info = " (OAuth → Claude Code headers)" if is_oauth else ""
        print(_c(f"✔ Valid!{auth_info}", _GREEN))
    except Exception as exc:
        err_str = str(exc)
        if len(err_str) > 100:
            err_str = err_str[:100] + "..."
        print(_c(f"✘ {err_str}", _RED))
        if is_oauth:
            print(_c("  OAuth tokens require an active Claude Max/Team subscription.", _DIM))
        print(_c("  You can fix this later in value_claw.json or the web dashboard.", _DIM))


# ── Save ──────────────────────────────────────────────────────────────────────

def _save_config(cfg: dict, config_path: str | None) -> Path:
    """Write config to disk (defaults to ~/.value_claw/value_claw.json)."""
    if config_path:
        out = Path(config_path)
    else:
        out = config.VALUE_CLAW_HOME / "value_claw.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    cfg.setdefault("channels", {
        "telegram": {"token": "", "allowedUsers": [], "allowedGroups": []},
        "discord": {"token": "", "allowedUsers": [], "allowedChannels": []},
    })
    cfg.setdefault("tavily", {}).setdefault("apiKey", "")
    cfg.setdefault("deepgram", {}).setdefault("apiKey", "")
    cfg.setdefault("heartbeat", {"intervalSec": 60, "alertChatId": None})
    cfg.setdefault("memory", {"dir": None})
    cfg.setdefault("web", {"host": "0.0.0.0", "port": 7788})
    cfg.setdefault("skills", {})
    cfg.setdefault("agent", {"autoCompactThreshold": 0, "verbose": True})
    cfg.setdefault("isolation", {"perGroup": False})
    cfg.setdefault("concurrency", {"maxAgents": 4})
    cfg["llm"].setdefault("fallback", "")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    config.load(str(out), force=True)
    return out


def needs_onboard(config_path: str | None = None) -> bool:
    """Check if onboarding is needed (no config or no API key)."""
    try:
        config.load(config_path)
    except Exception:
        return True

    provider = config.get_str("llm", "provider", default="")
    if not provider:
        return True

    api_key = config.get_str("llm", provider, "apiKey", default="")
    return not api_key
