---
title: 'glama-gateway-mcp: a dependency-free MCP server for the Glama AI gateway'
tags:
  - Python
  - Model Context Protocol
  - LLM gateway
  - tool use
  - agent
authors:
  - name: Sai Karun Nandipati
    orcid: 0009-0007-9218-9750
    affiliation: 1
affiliations:
  - name: Department of Data Science and Artificial Intelligence, PB Siddhartha College of Arts and Science
    index: 1
date: 25 September 2026
bibliography: paper.bib
---

# Summary

`glama-gateway-mcp` is a Models Context Protocol (MCP) server that exposes the
Glama AI gateway - an OpenAI-compatible endpoint covering 100+ language models
from many providers - as four MCP tools: listing models, chat completion,
streamed completion (reassembled server-side for clients that cannot hold a
stream), and request-status lookup. It is a single dependency-free Python
process that speaks MCP over stdio using only the standard library, so any MCP
client (IDE, agent runtime, personal assistant) can reach any gateway model
through one credential.

# Statement of need

MCP is converging as the integration standard for agents and IDE tooling, but
each MCP client expects a server per capability, and standing up a language
model integration per provider (OpenAI, Anthropic, Google, plus dozens of
smaller hosts) fragments credentials, configuration, and maintenance across
every application. Glama collapses provider access into one OpenAI-compatible
API, but stops short of handing models to MCP clients. Researchers and
hobbyists running multi-application agent stacks routinely waste an evening
wiring the same endpoint into each new tool.

`glama-gateway-mcp` removes that wiring. One server, configured once, presents
the whole gateway to any MCP client. Because it returns gateway payloads
verbatim and reassembles streams server-side, its behaviour is predictable
regardless of client. Being standard-library-only means it runs on any Python
without an install step, and its protocol layer is small enough to audit by
reading one file - properties that matter in reproducible-research
environments where pinning dependencies is itself the norm.

# State of the field

Official MCP SDKs (Python, TypeScript) make it easy to author a server but add
a dependency graph and a versioned protocol client; many projects therefore
prefer a bounded, hand-rolled implementation (`MHousesAr/simple-mcp-server`,
`hidetatz/simple-mcp-stdio-server`) whose behaviour they can pin. Concurrently,
multi-provider gateways (OpenRouter, LiteLLM, and Glama) standardise access on
the OpenAI surface, and generic gateway MCP efforts such as MCP-AI-Gateway
route across providers but carry FastAPI, web dashboards, and Docker as their
feature set. `glama-gateway-mcp` occupies the smallest viable intersection: a
server whose entire runtime contract is the Glama gateway, with zero runtime
dependencies, per-application wiring blocks included, and an explicit design
rule - "accept a gateway-shaped payload, return it verbatim" - that keeps the
tool honest when the gateway evolves. Its unique contribution is reliability
through minimal surface, not feature breadth.

# Software design

The server is two modules. `gateway.py` is a small OpenAI-compatible client
built on `urllib`: it models list, chat completion, SSE stream consumption
(reassembling deltas into a finished message plus usage), and request status;
every response is passed through unmodified except for the JSON envelope.
`server.py` implements the MCP wire protocol over stdio using newline-delimited
JSON-RPC 2.0 - `initialize`, `tools/list`, `tools/call`, `ping`, and the
notification no-reply rules - with each tool defined by an explicit JSON
schema. Design decisions worth noting: the server echoes the caller's request
id on tool results (some clients silently drop `id: null`), errors are
surfaced as JSON-RPC error objects rather than swallowed, a missing API key is
a readable `isError` result rather than a hang, and unknown tools / malformed
lines never terminate the loop, so an agent's stream remains usable after a
bad frame. Environment-based configuration (`GLAMA_API_KEY`, `GLAMA_BASE_URL`,
`GLAMA_DEFAULT_MODEL`) keeps secrets out of the config files that ship in the
repository's `configs/` directory.

# Research impact statement

The repository ships wired `mcpServers` blocks for the author's research
projects (Celebrum, Samvit, Collabuild, S-AI, and others), so each project can
call gateway models through this single server; the stdio smoke test that runs
in CI validates the protocol handshake end to end. The inclusion of per
-application config is itself the beginning of an adoption trail, and
external adoption by other agent-tool users is the near-term target. None of
the gates that require elapsed calendar time (six months of public history,
tagged releases) has been manufactured; they are tracked honestly in
`paper/JOSS_SUBMISSION_READINESS.md`.

# AI usage disclosure

This software, documentation and tests were drafted with generative-AI
assistance (code generation, copy-editing, test scaffolding). All assisted
artifacts were reviewed, edited, and validated by the human author, who made
the design decisions. No AI rendered evaluative decisions in this submission.

# Acknowledgements

No direct funding was received; the author thanks the MCP and Glama
communities for their public design documentation.

# References