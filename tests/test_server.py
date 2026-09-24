"""Tests for the glama-mcp server and gateway client.

The gateway client shares a tiny fake with the tests: an in-memory
HTTP-compatible object; gateway-level tests avoid the network entirely.
"""

from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from glama_mcp.gateway import GlamaGateway, _consume_sse, DEFAULT_MODEL
from glama_mcp.server import GlamaMCPServer, TOOLS, serve_stdio


class FakeGateway:
    def __init__(self):
        self.api_key = "test-key"
        self.calls = []

    def list_models(self):
        self.calls.append("list_models")
        return {"data": [{"id": "openai/gpt-4o"}, {"id": "anthropic/claude-2"}]}

    def chat_completion(self, messages, model=DEFAULT_MODEL, **kw):
        self.calls.append(("chat", messages, model))
        return {"id": "chatcmpl-1", "model": model,
                "choices": [{"message": {"role": "assistant",
                                         "content": "hello from fake"}}]}

    def stream_completion(self, messages, model=DEFAULT_MODEL):
        self.calls.append(("stream", messages, model))
        return {"streamed": True, "content": "hello streamed", "model": model}

    def request_status(self, request_id):
        return {"id": request_id, "status": "complete"}


def rpc(method, params=None, msg_id=1):
    msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


@pytest.fixture
def server():
    return GlamaMCPServer(FakeGateway())


def test_initialize(server):
    out = server.handle(rpc("initialize", {"protocolVersion": "2024-11-05"}))
    assert out["id"] == 1
    assert out["result"]["protocolVersion"] == "2024-11-05"
    assert out["result"]["serverInfo"]["name"] == "glama-gateway-mcp"


def test_notifications_get_no_reply(server):
    assert server.handle(rpc("notifications/initialized")) is None


def test_ping(server):
    out = server.handle(rpc("ping"))
    assert out["result"] == {}


def test_tools_list_has_our_tools(server):
    out = server.handle(rpc("tools/list"))
    names = [t["name"] for t in out["result"]["tools"]]
    assert "glama_list_models" in names
    assert "glama_chat_completion" in names
    assert "glama_stream_completion" in names
    assert "glama_request_status" in names


def test_unknown_method(server):
    out = server.handle(rpc("methods/bogus"))
    assert out["error"]["code"] == -32601


def test_chat_completion_dispatch(server):
    out = server.handle(rpc("tools/call", {
        "name": "glama_chat_completion",
        "arguments": {"messages": [{"role": "user", "content": "hi"}]},
    }))
    content = out["result"]["content"][0]["text"]
    assert server.gateway.calls[-1][0] == "chat"
    assert "hello from fake" in content


def test_chat_completion_requires_messages(server):
    out = server.handle(rpc("tools/call", {"name": "glama_chat_completion",
                                           "arguments": {}}))
    assert out["result"]["isError"] is True


def test_stream_dispatch(server):
    out = server.handle(rpc("tools/call", {
        "name": "glama_stream_completion",
        "arguments": {"messages": [{"role": "user", "content": "talk"}]},
    }))
    assert "hello streamed" in out["result"]["content"][0]["text"]


def test_request_status_dispatch(server):
    out = server.handle(rpc("tools/call", {
        "name": "glama_request_status",
        "arguments": {"request_id": "abc123"},
    }))
    assert '"complete"' in out["result"]["content"][0]["text"]


def test_unknown_tool(server):
    out = server.handle(rpc("tools/call", {"name": "nope", "arguments": {}}))
    assert out["result"]["isError"] is True


def test_tool_schemas_declare_inputs():
    by_name = {t["name"]: t for t in TOOLS}
    assert by_name["glama_chat_completion"]["inputSchema"]["required"] == ["messages"]


def test_missing_api_key_reports_error():
    g = FakeGateway()
    g.api_key = ""
    s = GlamaMCPServer(g)
    out = s.handle(rpc("tools/call", {"name": "glama_list_models",
                                      "arguments": {}}))
    assert out["result"]["isError"] is True
    assert "GLAMA_API_KEY" in out["result"]["content"][0]["text"]


class _StreamLine:
    def __init__(self, text):
        self.text = text

    def decode(self, errors="replace"):
        return self.text


def _sse_resp(lines):
    class R:
        def __iter__(self):
            return iter(lines)
    return R()


def test_consume_sse_reassembles_deltas():
    resp = _sse_resp([
        _StreamLine('data: {"choices":[{"delta":{"content":"Hel"}}]}'),
        _StreamLine('data: {"choices":[{"delta":{"content":"lo"}}],"model":"m"}'),
        _StreamLine('data: {"choices":[{"delta":{},"finish_reason":"stop"}]}'),
        _StreamLine("data: [DONE]"),
    ])
    out = _consume_sse(resp)
    assert out["content"] == "Hello"
    assert out["finish_reason"] == "stop"
    assert out["model"] == "m"
    assert out["streamed"] is True


def test_serve_stdio_roundtrip(monkeypatch, capsys):
    incoming = [
        json.dumps(rpc("initialize")) + "\n",
        json.dumps(rpc("tools/list", msg_id=2)) + "\n",
        json.dumps(rpc("tools/call", {
            "name": "glama_list_models", "arguments": {}}, msg_id=3)) + "\n",
    ]
    class In:
        def __iter__(self):
            return iter(incoming)
    monkeypatch.setattr(sys, "stdin", In())
    assert serve_stdio(FakeGateway()) == 0
    captured = capsys.readouterr().out.strip().splitlines()
    assert len(captured) == 3
    init = json.loads(captured[0])
    assert init["result"]["serverInfo"]["name"] == "glama-gateway-mcp"


def test_gateway_payload_shapes():
    """The OpenAI-compatible payload is well-formed (sans network)."""
    g = GlamaGateway(api_key="k", base_url="https://example.test/v1")

    def fake_urlopen(req, timeout=None, context=None):
        body = json.loads(req.data.decode())
        assert body["model"] == "openai/gpt-4o"
        assert body["messages"] == [{"role": "user", "content": "x"}]
        assert req.get_header("Authorization") == "Bearer k"

        class Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"ok": true}'

        return Resp()

    from unittest import mock
    with mock.patch("urllib.request.urlopen", fake_urlopen):
        out = g.chat_completion([{"role": "user", "content": "x"}])
    assert out == {"ok": True}