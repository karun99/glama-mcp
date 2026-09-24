"""Glama Gateway client — OpenAI-compatible, standard library only.

Dispatches to https://gateway.glama.ai/v1 (or GLAMA_BASE_URL) using
urllib. No third-party dependencies, matching the rest of the ecosystem's
preference for zero-dep tooling.

The gateway accepts OpenAI-format models (e.g. "openai/gpt-4o",
"anthropic/claude-2") and returns OpenAI-format responses; we keep the raw
response bodies intact and add only a thin envelope so an MCP client can
present them as tool results.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

BASE_URL = "https://gateway.glama.ai/v1"
DEFAULT_MODEL = os.environ.get("GLAMA_DEFAULT_MODEL", "openai/gpt-4o")


class GatewayError(RuntimeError):
    """Raised when the upstream gateway refuses or fails a request."""

    def __init__(self, message: str, status: Optional[int] = None,
                 body: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.body = body


class GlamaGateway:
    def __init__(self, api_key: Optional[str] = None,
                 base_url: str = BASE_URL, timeout: float = 60.0):
        self.api_key = api_key or os.environ.get("GLAMA_API_KEY", "")
        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.timeout = timeout
        self._ctx = ssl.create_default_context()

    # ------------------------------------------------------------------ core
    def _request(self, method: str, path: str,
                 payload: Optional[dict] = None) -> Any:
        url = self.base_url + path
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        data = json.dumps(payload).encode() if payload is not None else b""
        req = urllib.request.Request(url, data=data or None, headers=headers,
                                     method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout,
                                        context=self._ctx) as resp:
                raw = resp.read().decode()
                return self._parse(raw, resp.status)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            raise GatewayError(
                f"gateway {path} failed with HTTP {exc.code}", exc.code, body)
        except urllib.error.URLError as exc:
            raise GatewayError(f"gateway unreachable: {exc.reason}")

    @staticmethod
    def _parse(raw: str, status: int) -> Any:
        if not raw.strip():
            return {"raw": "", "status_code": status}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw, "status_code": status}
        return data

    # ------------------------------------------------------------------ API
    def list_models(self) -> list:
        return self._request("GET", "/models")

    def chat_completion(self, messages: List[Dict[str, str]],
                        model: str = DEFAULT_MODEL,
                        temperature: Optional[float] = None,
                        max_tokens: Optional[int] = None,
                        **extra) -> Any:
        payload: dict = {"model": model, "messages": messages}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        payload.update(extra)
        return self._request("POST", "/chat/completions", payload)

    def stream_completion(self, messages: List[Dict[str, str]],
                          model: str = DEFAULT_MODEL) -> dict:
        """Streamed completion: returns the concatenated deltas plus meta.

        We call the same /chat/completions endpoint with stream=true, read
        the SSE lines, and reconstruct the finished message server-side so
        MCP clients that cannot hold a stream still receive the text.
        """
        payload = {"model": model, "messages": messages, "stream": True}
        url = self.base_url + "/chat/completions"
        headers = {"Content-Type": "application/json",
                   "Accept": "text/event-stream"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=None,
                                        context=self._ctx) as resp:
                return _consume_sse(resp)
        except urllib.error.HTTPError as exc:
            raise GatewayError(
                f"gateway stream failed with HTTP {exc.code}", exc.code,
                exc.read().decode(errors="replace"))
        except urllib.error.URLError as exc:
            raise GatewayError(f"gateway unreachable: {exc.reason}")

    def request_status(self, request_id: str) -> Any:
        return self._request("GET", f"/completion-requests/{request_id}")


def _consume_sse(resp) -> dict:
    """Read a Server-Sent-Events body and rebuild the finished message."""
    chunks: List[str] = []
    finish_reason = None
    usage = None
    model = None
    for raw_line in resp:
        line = raw_line.decode(errors="replace").strip()
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        choices = event.get("choices") or []
        if choices:
            delta = choices[0].get("delta") or {}
            if delta.get("content"):
                chunks.append(delta["content"])
            if choices[0].get("finish_reason"):
                finish_reason = choices[0]["finish_reason"]
            model = model or event.get("model")
        if event.get("usage"):
            usage = event["usage"]
    content = "".join(chunks)
    return {
        "streamed": True,
        "content": content,
        "finish_reason": finish_reason,
        "model": model,
        "usage": usage,
        "delta_count": len(chunks),
    }