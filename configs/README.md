# Application wiring

Every `.mcp.json` in this directory registers the `glama-gateway` MCP server
for one application. Copy the matching file into that repo (or your MCP
client's config folder) and fill in `GLAMA_API_KEY` — the value can also be an
environment variable so the key never lives in a committed file.

| Application | File | What it gains |
|---|---|---|
| Celebrum | `celebrum.mcp.json` | gateway models for persona/memory tooling |
| Samvit | `samvit.mcp.json` | LLM access under VISION/ULTRON gating |
| Collabuild | `collabuild.mcp.json` | model-backed research agents |
| S-AI | `s-ai.mcp.json` | one more provider behind the swarm's MCP builder |
| S-AI Update | `s-ai-update.mcp.json` | hardened synthetic-executive LLM path |
| AI Content Studio | `ai-content-studio.mcp.json` | content and model-ops generation |
| Teddy × TechLearn | `teddy-techlearn.mcp.json` | study-companion chat |
| Health Quest | `health-quest.mcp.json` | content generation for the game |
| hermes-agent | `hermes-agent.mcp.json` | agent-loop LLM calls |
| Portfolio site | `karun99.github.io.mcp.json` | (optional) site tooling |

All blocks share the same shape:

```json
{
  "mcpServers": {
    "glama-gateway": {
      "command": "glama-mcp",
      "env": { "GLAMA_API_KEY": "${GLAMA_API_KEY}" }
    }
  }
}
```

## Using the blocks

- **MCP clients with a config file** (Claude Desktop, Cursor, VS Code): merge
  the `mcpServers` key from your app's file into the client config.
- **Standalone apps**: write the file as `.mcp.json` in the app repo root and
  have the app's MCP client read it.
- **Verification after wiring**: run the handshake from the README to confirm
  the server answers before the client tries to use the tools.

## Privacy note

`GLAMA_API_KEY` must never be committed. Use a `.env` file or your client's
secret store; CI and the sample configs only ever reference the variable.