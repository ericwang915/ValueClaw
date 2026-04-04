"""Fallback LLM provider — tries primary, falls back to secondary on failure."""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any

from .base import LLMProvider

logger = logging.getLogger(__name__)


class FallbackProvider(LLMProvider):
    """Wraps two LLM providers with automatic failover.

    Tries the primary provider first.  If it raises any exception (rate limit,
    auth error, quota exhausted, server error …), logs the failure and
    transparently retries the same request on the fallback provider.
    """

    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self._active: LLMProvider = primary
        self._primary_failed = False

    @property
    def supports_images(self) -> bool:  # type: ignore[override]
        return self._active.supports_images

    @property
    def model_name(self) -> str:  # type: ignore[override]
        return getattr(self._active, "model_name", "unknown")

    def _switch_to_fallback(self, exc: Exception) -> None:
        fallback_model = getattr(self.fallback, "model_name", "fallback")
        logger.warning(
            "[Fallback] Primary LLM failed (%s: %s), switching to %s",
            type(exc).__name__, exc, fallback_model,
        )
        self._active = self.fallback
        self._primary_failed = True

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = "auto",
        **kwargs: Any,
    ) -> Any:
        if self._primary_failed:
            return self.fallback.chat(messages, tools, tool_choice, **kwargs)

        try:
            return self.primary.chat(messages, tools, tool_choice, **kwargs)
        except Exception as exc:
            self._switch_to_fallback(exc)
            return self.fallback.chat(messages, tools, tool_choice, **kwargs)

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = "auto",
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, Any]:
        if self._primary_failed:
            return (yield from self.fallback.chat_stream(
                messages, tools, tool_choice, **kwargs
            ))

        try:
            return (yield from self.primary.chat_stream(
                messages, tools, tool_choice, **kwargs
            ))
        except Exception as exc:
            self._switch_to_fallback(exc)
            return (yield from self.fallback.chat_stream(
                messages, tools, tool_choice, **kwargs
            ))
