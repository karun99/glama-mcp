# glama-gateway-mcp

A Models Context Protocol (MCP) server that exposes the **Glama AI gateway**
(https://gateway.glama.ai/v1, an OpenAI-compatible endpoint for 100+ models)
as MCP tools. Standard library only, Python 3.9+, no model downloads.

## Statement of need

MCP clients (Claude Desktop, Cursor, and a growing list of agent runtimes)
each expect an MCP server per capability. When a research project needs to
call language models across many providers — `openai/...`, `anthropic/...`,
`google/...`, and dozens more — wiring every client to every provider is a
tangle of credentials and bespoke plugins. Glama centralizes provider access
behind one OpenAI-compatible API, but it does not, by itself, hand a model
to an MCP client.

`glama-gateway-mcp` closes exactly that seam. It is a thin, dependency-free
MCP server that fronts the gateway: an agent (or IDE, or personal assistant)
talks MCP to this one server and gains `openai/gpt-4o`, `anthropic/claude-2`,
and any other gateway model through four tools — listing models, chat
completion, streaming completion, and request-status lookup. One API key, one
credential, one endpoint for every connected application.

Distinguishing design choices:

- **stdio MCP, implemented on the stdlib** — the protocol layer uses only
  `json`, `urllib` and `sys`, so it runs anywhere Python runs and is trivial
  to audit.
- **OpenAI-compatible request/response shapes** — the gateway returns raw
  gateway bodies, so no field mapping is ever wrong.
- **Server-side stream reassembly** — MCP clients that cannot hold a live SSE
  stream still receive the full completion text plus usage metadata.
- **Clean JSON-RPC errors** — a missing key, unreachable gateway, or unknown
  tool yields a readable MCP error instead of a hang or silent failure.

## Install

```sh
pip install .
# development:
pip install -e ".[dev]"
```

Requires Python 3.9+. Runtime dependencies: none.

## Usage

Export your Glama key, then run the server:

```sh
export GLAMA_API_KEY="your_key_here"
export GLAMA_DEFAULT_MODEL="openai/gpt-4o"    # optional
glama-mcp
```

or run it as a module:

```sh
python -m glama_mcp
```

Connect any MCP client to the `glama-mcp` stdio command. The exposed tools:

| Tool | Purpose |
|---|---|
| `glama_list_models` | list models available through the gateway |
| `glama_chat_completion` | one-shot chat completion |
| `glama_stream_completion` | streamed completion (reassembled) |
| `glama_request_status` | status of a completion request by id |

### Per-application wiring

Ready-to-paste `mcpServers` blocks for individual applications live in
[`configs/`](configs/): Celebrum, Samvit, Collabuild, S-AI, hermes-agent,
teddy-techlearn, health-quest, ai-content-studio, and the portfolio site.
Each block registers this server for that application's MCP client.

```json
{
  "mcpServers": {
    "glama-gateway": {
      "command": "glama-mcp",
      "env": { "GLAMA_API_KEY": "your_key_here" }
    }
  }
}
```

### Verifying the server by hand

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | python -m glama_mcp
```

## Tests

```sh
python -m pytest
```

The suite covers the gateway client (payload shapes, SSE reassembly), protocol
handshake, tool discovery and dispatch, error handling, missing-key behaviour,
and a full stdio round trip.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Keep it dependency-free and Python 3.9
compatible; every change needs a test.

## JOSS paper

Submission materials in [`paper/`](paper/): `paper.md`, `paper.bib`, and
`JOSS_SUBMISSION_READINESS.md` (records which gates are met and which still
require calendar time).

## License

MIT — see [LICENSE](LICENSE).

## AI usage disclosure

Code and documentation were drafted with generative-AI assistance and reviewed
by the human maintainer, who made the design decisions. This disclosure is kept
in line with the JOSS AI usage policy.