# Contributing to glama-gateway-mcp

## Ground rules

- Keep the package **standard-library only** and **Python 3.9 compatible**.
- Every change needs a test in `tests/`; run `python -m pytest` before pushing.
- Open an issue before opening a pull request.
- New upstream gateway features follow the same rule as the existing tools:
  accept a gateway-shaped payload, return it verbatim, never silently remap.

## Reporting bugs

Search the issues first. Include:

- the MCP client and how the server was launched,
- what you expected versus what happened, ideally with the raw JSON-RPC frame,
- Python version and whether `GLAMA_API_KEY` was set.

## Support expectations

Single-maintainer project maintained in spare time. Issues are the channel;
expect answers within a week.

## License

By contributing you agree your work is licensed under the MIT license.