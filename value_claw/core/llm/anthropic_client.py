"""
Anthropic (Claude) provider — adapts the Anthropic API to the OpenAI-compatible
response format used by Agent.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Generator
from typing import Any, Dict, List, Optional

import anthropic

from .base import LLMProvider
from .response import MockChoice, MockFunction, MockMessage, MockResponse, MockToolCall

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 5  # seconds


_OAUTH_BETAS = ",".join([
    "claude-code-20250219",
    "oauth-2025-04-20",
    "fine-grained-tool-streaming-2025-05-14",
    "interleaved-thinking-2025-05-14",
])

_OAUTH_SYSTEM_PREFIX = "You are Claude Code, Anthropic's official CLI for Claude."


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider with API key or OAuth token support.

    Supports all authentication methods:
    - Standard API key (``sk-ant-api03-...``) → uses ``x-api-key`` header
    - OAuth token (``sk-ant-oat01-...``) → uses ``Authorization: Bearer`` +
      required ``anthropic-beta`` headers and Claude Code identity
    - Environment variable ``ANTHROPIC_API_KEY``
    """

    supports_images = True

    def __init__(self, api_key: str, model_name: str = "claude-sonnet-4-6"):
        self._is_oauth = "oat" in api_key[:20]
        client_kwargs: dict[str, Any] = {"timeout": 300.0}

        if self._is_oauth:
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

        self.client = anthropic.Anthropic(**client_kwargs)
        self.model_name = model_name
        self._auth_type = "oauth" if self._is_oauth else "api-key"
        logger.info("[Anthropic] model=%s auth=%s", model_name, self._auth_type)

    # ── shared helpers ────────────────────────────────────────────────────

    def _prepare_request(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: Any,
        **kwargs: Any,
    ) -> dict:
        """Build the kwargs dict for ``messages.create`` / ``stream``."""
        system_prompt = ""
        filtered_messages: list[dict] = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt += msg["content"] + "\n"

            elif msg["role"] == "tool":
                filtered_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg["tool_call_id"],
                        "content": msg["content"],
                    }],
                })

            elif msg["role"] == "assistant" and "tool_calls" in msg:
                content_block: list[dict] = []
                if msg.get("content"):
                    content_block.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    tc_id = tc["id"] if isinstance(tc, dict) else tc.id
                    func = tc["function"] if isinstance(tc, dict) else tc.function
                    fname = func["name"] if isinstance(func, dict) else func.name
                    fargs = json.loads(
                        func["arguments"] if isinstance(func, dict) else func.arguments
                    )
                    content_block.append({
                        "type": "tool_use",
                        "id": tc_id,
                        "name": fname,
                        "input": fargs,
                    })
                filtered_messages.append({"role": "assistant", "content": content_block})

            elif msg["role"] == "user" and isinstance(msg.get("content"), list):
                filtered_messages.append({
                    "role": "user",
                    "content": self._convert_user_content(msg["content"]),
                })

            else:
                filtered_messages.append(msg)

        filtered_messages = self._merge_consecutive(filtered_messages)

        if self._is_oauth:
            filtered_messages = self._ensure_content_blocks(filtered_messages)

        anthropic_tools = []
        if tools:
            for t in tools:
                if t["type"] == "function":
                    anthropic_tools.append({
                        "name": t["function"]["name"],
                        "description": t["function"]["description"],
                        "input_schema": t["function"]["parameters"],
                    })

        max_tokens = kwargs.get("max_tokens", 4096)
        api_kwargs: dict = {
            "model": self.model_name,
            "messages": filtered_messages,
            "max_tokens": max_tokens,
        }

        if self._is_oauth:
            sys_blocks: list[dict] = [
                {"type": "text", "text": _OAUTH_SYSTEM_PREFIX},
            ]
            if system_prompt:
                sys_blocks.append({"type": "text", "text": system_prompt})
            api_kwargs["system"] = sys_blocks
            api_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 2048}
            api_kwargs["temperature"] = 1
            api_kwargs["max_tokens"] = max(max_tokens, 8192)
        elif system_prompt:
            api_kwargs["system"] = system_prompt

        if anthropic_tools:
            api_kwargs["tools"] = anthropic_tools
            if tool_choice == "required":
                api_kwargs["tool_choice"] = {"type": "any"}
            elif tool_choice == "none":
                pass
            else:
                api_kwargs["tool_choice"] = {"type": "auto"}

        if self._is_oauth:
            for idx, m in enumerate(filtered_messages):
                ct = type(m.get("content")).__name__
                logger.debug(
                    "[Anthropic] msg[%d] role=%s content_type=%s keys=%s",
                    idx, m.get("role"), ct, list(m.keys()),
                )

        return api_kwargs

    @staticmethod
    def _response_from_blocks(
        content_text: str,
        tool_calls: list[MockToolCall],
    ) -> MockResponse:
        return MockResponse(choices=[
            MockChoice(message=MockMessage(
                content=content_text or None,
                tool_calls=tool_calls or None,
            ))
        ])

    # ── non-streaming ─────────────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = "auto",
        **kwargs: Any,
    ) -> Any:
        api_kwargs = self._prepare_request(
            messages, tools, tool_choice, **kwargs
        )

        for attempt in range(_MAX_RETRIES):
            try:
                response = self.client.messages.create(**api_kwargs)
                break
            except anthropic.RateLimitError:
                if attempt == _MAX_RETRIES - 1:
                    raise
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning("[Anthropic] 429 rate limit, retry %d/%d in %ds", attempt + 1, _MAX_RETRIES, delay)
                time.sleep(delay)

        content_text = ""
        tool_calls: list[MockToolCall] = []
        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append(MockToolCall(
                    id=block.id,
                    function=MockFunction(
                        name=block.name,
                        arguments=json.dumps(block.input),
                    ),
                ))
            # skip "thinking" blocks — internal reasoning, not user-facing

        return self._response_from_blocks(content_text, tool_calls)

    # ── streaming ─────────────────────────────────────────────────────────

    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = "auto",
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, MockResponse]:
        """Stream Anthropic responses, yielding text deltas."""
        api_kwargs = self._prepare_request(
            messages, tools, tool_choice, **kwargs
        )

        content_text = ""
        tool_calls: list[MockToolCall] = []
        current_tool: dict[str, Any] | None = None

        last_err: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                stream_ctx = self.client.messages.stream(**api_kwargs)
                break
            except anthropic.RateLimitError as exc:
                last_err = exc
                if attempt == _MAX_RETRIES - 1:
                    raise
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning("[Anthropic] 429 rate limit on stream, retry %d/%d in %ds", attempt + 1, _MAX_RETRIES, delay)
                time.sleep(delay)
        else:
            raise last_err  # type: ignore[misc]

        with stream_ctx as stream:
            for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    if block.type == "tool_use":
                        current_tool = {
                            "id": block.id,
                            "name": block.name,
                            "args": "",
                        }
                elif event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        content_text += delta.text
                        yield {"type": "text_delta", "text": delta.text}
                    elif delta.type == "input_json_delta":
                        if current_tool is not None:
                            current_tool["args"] += delta.partial_json
                    # skip thinking_delta — internal reasoning
                elif event.type == "content_block_stop":
                    if current_tool is not None:
                        tool_calls.append(MockToolCall(
                            id=current_tool["id"],
                            function=MockFunction(
                                name=current_tool["name"],
                                arguments=current_tool["args"] or "{}",
                            ),
                        ))
                        current_tool = None

        return self._response_from_blocks(content_text, tool_calls)

    # ── multimodal conversion ────────────────────────────────────────────

    @staticmethod
    def _convert_user_content(parts: list[dict]) -> list[dict]:
        """Convert OpenAI-style content parts to Anthropic format.

        Handles ``image_url`` with ``data:`` URIs (base64) or plain URLs.
        """
        import base64 as _b64
        import re as _re

        out: list[dict] = []
        for p in parts:
            if p.get("type") == "text":
                out.append({"type": "text", "text": p["text"]})
            elif p.get("type") == "image_url":
                url = p["image_url"]["url"]
                m = _re.match(
                    r"data:(image/\w+);base64,(.+)", url, _re.DOTALL
                )
                if m:
                    out.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": m.group(1),
                            "data": m.group(2),
                        },
                    })
                else:
                    try:
                        import urllib.request

                        resp = urllib.request.urlopen(url, timeout=15)
                        data = resp.read()
                        ct = resp.headers.get(
                            "Content-Type", "image/jpeg"
                        ).split(";")[0]
                        out.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": ct,
                                "data": _b64.b64encode(data).decode(),
                            },
                        })
                    except Exception:
                        out.append({
                            "type": "text",
                            "text": f"[image: {url}]",
                        })
            else:
                out.append(p)
        return out

    # ── utilities ─────────────────────────────────────────────────────────

    @staticmethod
    def _ensure_content_blocks(messages: list[dict]) -> list[dict]:
        """Convert all message content to list-of-blocks format and strip
        non-standard fields.

        Required by the interleaved-thinking beta — the Anthropic API
        rejects plain-string ``content`` on any message when this beta
        is active.  Also strips extra keys (``_ts``, etc.) that
        Pydantic validation would reject.

        Empty or whitespace-only text blocks are replaced with a dot — the
        API returns 400 if any text block lacks non-whitespace characters.
        """
        _PLACEHOLDER = "."
        out = []
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                content = [{"type": "text", "text": content or _PLACEHOLDER}]
            elif content is None:
                content = [{"type": "text", "text": _PLACEHOLDER}]
            elif isinstance(content, list):
                fixed: list[dict] = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        if not text or not text.strip():
                            block = {**block, "text": _PLACEHOLDER}
                        fixed.append(block)
                    elif isinstance(block, dict):
                        fixed.append(block)
                    else:
                        fixed.append({"type": "text", "text": str(block) or _PLACEHOLDER})
                content = fixed if fixed else [{"type": "text", "text": _PLACEHOLDER}]
            else:
                content = [{"type": "text", "text": str(content) or _PLACEHOLDER}]
            clean = {"role": msg["role"], "content": content}
            out.append(clean)
        return out

    @staticmethod
    def _merge_consecutive(messages: list[dict]) -> list[dict]:
        """Merge consecutive messages with the same role (Anthropic requirement)."""
        if not messages:
            return messages
        merged: list[dict] = [messages[0]]
        for msg in messages[1:]:
            if msg["role"] == merged[-1]["role"]:
                prev_content = merged[-1].get("content", "")
                curr_content = msg.get("content", "")
                if isinstance(prev_content, str) and isinstance(curr_content, str):
                    merged[-1]["content"] = prev_content + "\n" + curr_content
                elif isinstance(prev_content, list) and isinstance(curr_content, list):
                    merged[-1]["content"] = prev_content + curr_content
                elif isinstance(prev_content, str) and isinstance(curr_content, list):
                    merged[-1]["content"] = [
                        {"type": "text", "text": prev_content}
                    ] + curr_content
                elif isinstance(prev_content, list) and isinstance(curr_content, str):
                    merged[-1]["content"] = prev_content + [
                        {"type": "text", "text": curr_content}
                    ]
            else:
                merged.append(msg)
        return merged
