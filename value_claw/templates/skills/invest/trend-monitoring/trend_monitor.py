#!/usr/bin/env python3
"""
Trend Monitoring Pipeline — stock analysis with chart generation and LLM analysis.

Usage:
    python trend_monitor.py TSLA AAPL NVDA           # Analyze tickers
    python trend_monitor.py TSLA --no-llm             # Charts only, skip LLM
    python trend_monitor.py TSLA --no-news            # Skip news fetching
    python trend_monitor.py TSLA --format json        # JSON output
"""

import argparse
import datetime
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from lib.chart import analyze_stock  # noqa: E402
from lib.indicators import generate_indicator_chart  # noqa: E402
from lib.news import fetch_all_news  # noqa: E402
from lib.prompt import generate_analysis_prompt, generate_key_stats  # noqa: E402

DEFAULT_TICKERS = ["TSLA", "AAPL", "NVDA", "AMD", "MSFT", "GOOGL", "AMZN"]
DATA_DIR = os.path.expanduser("~/.value_claw/trend_monitoring")


def find_config():
    """Search for value_claw.json in standard locations."""
    candidates = [
        os.path.join(os.getcwd(), "value_claw.json"),
        os.path.expanduser("~/.value_claw/value_claw.json"),
    ]
    d = SCRIPT_DIR
    for _ in range(8):
        candidates.append(os.path.join(d, "value_claw.json"))
        d = os.path.dirname(d)
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def load_config(config_path=None):
    """Load value_claw.json config."""
    path = config_path or find_config()
    if path and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _resolve_llm_config(config):
    """Resolve the default LLM provider settings from config."""
    provider = config.get("llm", {}).get("provider", "deepseek").lower()

    provider_map = {
        "deepseek": ("deepseek", "https://api.deepseek.com/v1", "deepseek-chat"),
        "grok": ("grok", "https://api.x.ai/v1", "grok-3"),
        "kimi": ("kimi", "https://api.moonshot.cn/v1", "moonshot-v1-128k"),
        "moonshot": ("kimi", "https://api.moonshot.cn/v1", "moonshot-v1-128k"),
        "glm": ("glm", "https://open.bigmodel.cn/api/paas/v4/", "glm-4-flash"),
        "zhipu": ("glm", "https://open.bigmodel.cn/api/paas/v4/", "glm-4-flash"),
    }

    if provider in ("claude", "anthropic"):
        return "claude", config.get("llm", {}).get("claude", {})

    if provider == "gemini":
        return "gemini", config.get("llm", {}).get("gemini", {})

    cfg_key, default_url, default_model = provider_map.get(provider, ("deepseek", "https://api.deepseek.com/v1", "deepseek-chat"))
    section = config.get("llm", {}).get(cfg_key, {})
    return "openai", {
        "apiKey": section.get("apiKey", ""),
        "baseUrl": section.get("baseUrl", default_url),
        "model": section.get("model", default_model),
    }


def query_llm(prompt_text, config):
    """Query the default configured LLM provider for analysis."""
    kind, cfg = _resolve_llm_config(config)

    if kind == "claude":
        return _query_claude(prompt_text, cfg)
    elif kind == "gemini":
        return _query_gemini(prompt_text, cfg)
    else:
        return _query_openai_compatible(prompt_text, cfg)


def _query_openai_compatible(prompt_text, cfg):
    """OpenAI-compatible chat completion (DeepSeek, Grok, Kimi, GLM, etc.)."""
    import requests as req

    api_key = cfg.get("apiKey", "")
    if not api_key:
        return "Error: No API key configured for LLM provider."

    base_url = cfg.get("baseUrl", "").rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = {
        "model": cfg.get("model", ""),
        "messages": [
            {"role": "system", "content": "You are a helpful financial analyst assistant."},
            {"role": "user", "content": prompt_text},
        ],
        "stream": False,
        "temperature": 0.7,
    }
    try:
        resp = req.post(url, headers=headers, json=data, timeout=90)
        if resp.status_code == 200:
            choices = resp.json().get("choices", [])
            if choices:
                return choices[0]["message"]["content"]
        return f"Error: API returned {resp.status_code} — {resp.text[:200]}"
    except Exception as e:
        return f"Error: {e}"


_OAUTH_BETAS = ",".join([
    "claude-code-20250219",
    "oauth-2025-04-20",
    "interleaved-thinking-2025-05-14",
])
_OAUTH_SYSTEM_PREFIX = "You are Claude Code, Anthropic's official CLI for Claude."


def _query_claude(prompt_text, cfg):
    """Anthropic Claude API call with OAuth token support."""
    api_key = cfg.get("apiKey", "")
    if not api_key:
        return "Error: No Claude API key configured."
    model = cfg.get("model", "claude-sonnet-4-20250514")

    try:
        import anthropic
        is_oauth = "oat" in api_key[:20]
        client_kwargs = {"timeout": 300.0}

        if is_oauth:
            client_kwargs["api_key"] = None
            client_kwargs["auth_token"] = api_key
            client_kwargs["default_headers"] = {
                "accept": "application/json",
                "anthropic-dangerous-direct-browser-access": "true",
                "anthropic-beta": _OAUTH_BETAS,
                "user-agent": "claude-cli/2.1.75",
                "x-app": "cli",
            }
        else:
            client_kwargs["api_key"] = api_key

        client = anthropic.Anthropic(**client_kwargs)

        api_kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_text}],
        }

        if is_oauth:
            api_kwargs["system"] = [
                {"type": "text", "text": _OAUTH_SYSTEM_PREFIX},
                {"type": "text", "text": "You are a helpful financial analyst assistant."},
            ]
            api_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 10240}
            api_kwargs["temperature"] = 1
            api_kwargs["max_tokens"] = 16384
        else:
            api_kwargs["system"] = "You are a helpful financial analyst assistant."
            api_kwargs["max_tokens"] = 4096

        resp = client.messages.create(**api_kwargs)
        for block in resp.content:
            if hasattr(block, "text") and block.type == "text":
                return block.text
        return "Error: empty response"
    except Exception as e:
        return f"Error: {e}"


def _query_gemini(prompt_text, cfg):
    """Google Gemini API call."""
    api_key = cfg.get("apiKey", "")
    if not api_key:
        return "Error: No Gemini API key configured."

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(cfg.get("model", "gemini-2.0-flash-exp"))
        resp = model.generate_content(f"You are a financial analyst.\n\n{prompt_text}")
        return resp.text if resp.text else "Error: empty response"
    except Exception as e:
        return f"Error: {e}"


def parse_llm_output(text):
    """Parse [SIGNAL], [CONFIDENCE], [SUMMARY], [REASONING] from LLM output."""
    signal, confidence, summary = "Unknown", "Unknown", "No summary."
    current = None
    summary_lines = []

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == "[SIGNAL]":
            current = "SIGNAL"
            continue
        elif stripped == "[CONFIDENCE]":
            current = "CONFIDENCE"
            continue
        elif stripped == "[SUMMARY]":
            current = "SUMMARY"
            continue
        elif stripped == "[REASONING]":
            current = None
            continue

        if current == "SIGNAL" and stripped:
            signal = stripped
            current = None
        elif current == "CONFIDENCE" and stripped:
            confidence = stripped
            current = None
        elif current == "SUMMARY" and stripped:
            summary_lines.append(stripped)

    if summary_lines:
        summary = "\n".join(summary_lines)
    return signal, confidence, summary


def combine_images(trend_path, indicator_path, output_dir, ticker):
    """Vertically stack trend chart + indicator table into a combined image."""
    try:
        from PIL import Image

        if not (trend_path and os.path.exists(trend_path)):
            return indicator_path
        if not (indicator_path and os.path.exists(indicator_path)):
            return trend_path

        img1 = Image.open(trend_path)
        img2 = Image.open(indicator_path)
        w1, h1 = img1.size
        w2, h2 = img2.size
        max_w = max(w1, w2)
        new_img = Image.new("RGB", (max_w, h1 + h2), (255, 255, 255))
        new_img.paste(img1, ((max_w - w1) // 2, 0))
        new_img.paste(img2, ((max_w - w2) // 2, h1))

        comb_dir = os.path.join(output_dir, "images", "combined")
        os.makedirs(comb_dir, exist_ok=True)
        path = os.path.join(comb_dir, f"{ticker}_combined.png")
        new_img.save(path)
        print(f"  Combined image: {path}")
        return path
    except ImportError:
        print("  Pillow not installed, using trend chart only")
        return trend_path or indicator_path
    except Exception as e:
        print(f"  Error combining images: {e}")
        return trend_path or indicator_path


def run_pipeline(tickers, config, skip_llm=False, skip_news=False, output_format="text"):
    """Main pipeline: analyze tickers, generate charts, run LLM."""
    output_dir = DATA_DIR
    os.makedirs(output_dir, exist_ok=True)

    provider_name = config.get("llm", {}).get("provider", "deepseek")
    print(f"LLM Provider: {provider_name}")

    if not skip_news:
        print("\n[1/4] Fetching news...")
        fetch_all_news(tickers, output_dir)
    else:
        print("\n[1/4] Skipping news fetch")

    results = []

    for i, ticker in enumerate(tickers, 1):
        print(f"\n[2/4] Analyzing {ticker} ({i}/{len(tickers)})...")

        print("  Generating key stats...")
        generate_key_stats(ticker, output_dir)

        print("  Generating trend chart...")
        res = analyze_stock(ticker, output_dir)
        trend_path = res.get("ChartPath") if res else None

        print("  Generating indicator table...")
        indicator_path = generate_indicator_chart(ticker, output_dir)

        combined_path = combine_images(trend_path, indicator_path, output_dir, ticker)

        signal, confidence, summary = "N/A", "N/A", "LLM analysis skipped"

        if not skip_llm:
            print("  Building prompt & querying LLM...")
            prompt = generate_analysis_prompt(ticker, output_dir)
            llm_raw = query_llm(prompt, config)
            signal, confidence, summary = parse_llm_output(llm_raw)
            print(f"  Signal: {signal} | Confidence: {confidence}")

        result = {
            "ticker": ticker,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "signal": signal,
            "confidence": confidence,
            "summary": summary,
            "trend_chart": trend_path,
            "indicator_chart": indicator_path,
            "combined_image": combined_path,
            **(res or {}),
        }
        results.append(result)

    if output_format == "json":
        safe_results = []
        for r in results:
            sr = {k: (None if isinstance(v, float) and v != v else v) for k, v in r.items()}
            safe_results.append(sr)
        print("\n" + json.dumps(safe_results, indent=2, default=str))
    else:
        print("\n" + "=" * 60)
        print("  TREND MONITORING REPORT")
        print("=" * 60)
        for r in results:
            print(f"\n  {r['ticker']} | {r['date']}")
            print(f"  Signal: {r['signal']} | Confidence: {r['confidence']}")
            if r.get("Trend_30d"):
                print(f"  30d Trend: {r['Trend_30d']} ({r.get('Change_30d%', 0):.1f}%)")
            if r.get("Patterns") and r["Patterns"] != "None":
                print(f"  Patterns: {r['Patterns']}")
            if r.get("Signals") and r["Signals"] != "Neutral":
                print(f"  Signals: {r['Signals']}")
            if r.get("combined_image"):
                print(f"  Image: {r['combined_image']}")
            print(f"  Summary: {r['summary'][:200]}")
        print("\n" + "=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(description="Trend Monitoring — stock analysis with chart generation")
    parser.add_argument("tickers", nargs="*", help="Stock tickers to analyze (e.g. TSLA AAPL NVDA)")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM analysis")
    parser.add_argument("--no-news", action="store_true", help="Skip news fetching")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--config", help="Path to value_claw.json")
    args = parser.parse_args()

    config = load_config(args.config)

    tickers = args.tickers
    if not tickers:
        tm_cfg = config.get("skills", {}).get("trendMonitoring", {})
        tickers = tm_cfg.get("defaultTickers", DEFAULT_TICKERS)

    print("Trend Monitoring Pipeline")
    print(f"Tickers: {', '.join(tickers)}")
    print(f"LLM: {'skip' if args.no_llm else 'enabled'}")
    print(f"News: {'skip' if args.no_news else 'enabled'}")

    run_pipeline(tickers, config, skip_llm=args.no_llm, skip_news=args.no_news, output_format=args.format)


if __name__ == "__main__":
    main()
