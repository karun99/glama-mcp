# JOSS submission readiness — glama-gateway-mcp

Honest ledger of which JOSS gates are met and which still require time.

## Already met

- **OSI-approved license**: `LICENSE` (MIT), plain text.
- **Open repository**: GitHub `karun99/glama-mcp`, browsable, clonable without
  registration, public issue tracker.
- **Installable packaging**: `pyproject.toml`, `pip install .`, console script
  `glama-mcp`, and `python -m glama_mcp`.
- **Automated tests**: pytest suite (client payloads, SSE reassembly, protocol
  handshake, dispatch, error paths, stdio round trip) plus CI.
- **Documentation**: README (statement of need, install, usage, verification
  command), `CONTRIBUTING.md`, API docstrings.
- **`paper.md` / `paper.bib`**: all required sections present.
- **AI usage disclosure**: included, per JOSS AI usage policy.

## Gates that need calendar time / evidence

| Gate | Status | What turns it green |
|---|---|---|
| Six months of public history | Not met (new repo) | Open development over > 6 months with iterative commits |
| Tagged releases / changelog | Not met | Cut a `v1.0.0`; maintain `CHANGELOG.md` |
| No "thin API client" objection | **Risk** | JOSS lists thin API clients as out of scope. Mitigation: present this as an MCP gateway/infrastructure package; its research contribution is the dependency-free MCP-over-stdio protocol layer, SSE reassembly, and reproducible per-application wiring. If a reviewer sees a plain API wrapper, this may be desk-rejected on scope—allow room in the paper for that framing, or publish via pyOpenSci/other venues instead |
| Demonstrated research impact | Weak | Record adoption: other groups' agent stacks using the configs, or a preprint/experiment that used the gateway through this server |

## Recommended path

1. Reach a stable API surface, tag `v1.0.0`, add `CHANGELOG.md`.
2. Keep the protocol layer's "verify by hand" command in the README so
   reviewers can test locally without a key.
3. Document at least one external or experimental use after > 6 months of
   visible history.
4. Re-assess scope framing; if "thin API client" remains a risk, target
   pyOpenSci instead of JOSS for this specific package.