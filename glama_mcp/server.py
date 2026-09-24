"""Models Context Protocol (MCP) stdio server exposing the Glama Gateway.

Implements the MCP protocol over stdin/stdout using newline-delimited JSON-RPC
2.0 messages. Zero dependencies; runs with the standard library alone.

Tools exposed:

  glama_list_models        list gateway models
  glama_chat_completion    one-shot chat completion
  glama_stream_completion  streamed chat completion (reassembled)
  glama_request_status     check a completion request by id

Environment:
  GLAMA_API_KEY       required for real upstream calls
  GLAMA_BASE_URL      default https://gateway.glama.ai/v1
  GLAMA_DEFAULT_MODEL default openai/gpt-4o
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

from .gateway import GlamaGateway, GatewayError, DEFAULT_MODEL

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "glama-gateway-mcp"
SERVER_VERSION = "1.0.0"

TOOLS: List[dict] = [
    {
        "name": "glama_list_models",
        "description": "List the models available through the Glama gateway "
                       "(OpenAI-format model ids).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "glama_chat_completion",
        "description": "Run a chat completion against the Glama gateway. "
                       "`messages` is an array of {role, content} objects.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"role": {"type": "string"},
                                       "content": {"type": "string"}},
                        "required": ["role", "content"],
                    },
                },
                "model": {"type": "string",
                          "description": "e.g. openai/gpt-4o, anthropic/claude-2"},
                "temperature": {"type": "number"},
                "max_tokens": {"type": "integer"},
            },
            "required": ["messages"],
        },
    },
    {
        "name": "glama_stream_completion",
        "description": "Streamed chat completion; deltas are reassembled into "
                       "one text answer with usage metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"role": {"type": "string"},
                                       "content": {"type": "string"}},
                        "required": ["role", "content"],
                    },
                },
                "model": {"type": "string"},
            },
            "required": ["messages"],
        },
    },
    {
        "name": "glama_request_status",
        "description": "Look up the status of a completion request by id.",
        "inputSchema": {
            "type": "object",
            "properties": {"request_id": {"type": "string"}},
            "required": ["request_id"],
        },
    },
]


class GlamaMCPServer:
    def __init__(self, gateway: Optional[GlamaGateway] = None):
        self.gateway = gateway or GlamaGateway()

    # ------------------------------------------------------------ dispatch
    def handle(self, msg: dict) -> Optional[dict]:
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params") or {}
        try:
            if method == "initialize":
                return self._reply(msg_id, {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                })
            if method in ("initialized", "notifications/initialized",
                          "notifications/cancelled"):
                return None  # notification: no reply
            if method == "ping":
                return self._reply(msg_id, {})
            if method == "tools/list":
                return self._reply(msg_id, {"tools": TOOLS})
            if method == "tools/call":
                reply = self._call_tool(params)
                if reply is not None and msg_id is not None:
                    reply["id"] = msg_id
                return reply
            return self._error(msg_id, -32601, f"Method not found: {method!r}")
        except GatewayError as exc:
            return self._error(msg_id, -32000, str(exc))
        except Exception as exc:  # never let a bad input kill the server
            return self._error(msg_id, -32602, f"Server error: {exc!r}")

    def _call_tool(self, params: dict) -> dict:
        name = params.get("name")
        args = params.get("arguments") or {}
        name = name or ""

        if name == "glama_list_models":
            if not self.gateway.api_key:
                return self._tool_error("GLAMA_API_KEY is not set; nothing to list.")
            return self._tool_result(self.gateway.list_models())

        if name == "glama_chat_completion":
            messages = args.get("messages")
            if not isinstance(messages, list) or not messages:
                return self._tool_error("`messages` is required and must be a non-empty list.")
            out = self.gateway.chat_completion(
                messages,
                model=args.get("model") or DEFAULT_MODEL,
                temperature=args.get("temperature"),
                max_tokens=args.get("max_tokens"),
            )
            return self._tool_result(out)

        if name == "glama_stream_completion":
            messages = args.get("messages")
            if not isinstance(messages, list) or not messages:
                return self._tool_error("`messages` is required and must be a non-empty list.")
            out = self.gateway.stream_completion(
                messages, model=args.get("model") or DEFAULT_MODEL)
            return self._tool_result(out)

        if name == "glama_request_status":
            rid = args.get("request_id")
            if not rid:
                return self._tool_error("`request_id` is required.")
            return self._tool_result(self.gateway.request_status(rid))

        return self._tool_error(f"Unknown tool: {name!r}")

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _reply(msg_id, result: dict) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    @staticmethod
    def _error(msg_id, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id,
                "error": {"code": code, "message": message}}

    @staticmethod
    def _tool_result(data: Any) -> dict:
        text = data if isinstance(data, str) else json.dumps(data, indent=2)
        return {"jsonrpc": "2.0", "id": None,
                "result": {"content": [{"type": "text", "text": text}], "isError": False}}

    @staticmethod
    def _tool_error(message: str) -> dict:
        return {"jsonrpc": "2.0", "id": None,
                "result": {"content": [{"type": "text", "text": message}], "isError": True}}


def serve_stdio(gateway: Optional[GlamaGateway] = None) -> int:
    """Read MCP messages from stdin, write replies to stdout."""
    server = GlamaMCPServer(gateway)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            # non-JSON drift on the stream is ignored; keep the server alive
            continue
        reply = server.handle(msg) if isinstance(msg, dict) else None
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
    return 0


def serve_stdio_entry() -> None:
    """Console-script entry point."""
    sys.exit(serve_stdio())