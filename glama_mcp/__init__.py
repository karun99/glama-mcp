"""glama-mcp — Models Context Protocol server for the Glama AI gateway.

Exposes glama.ai's OpenAI-compatible gateway (https://gateway.glama.ai/v1)
as MCP tools: model listing, chat completion, streaming completion, and
request-status lookup. Standard library only, Python 3.9+.
"""

from .gateway import GlamaGateway, GatewayError, BASE_URL, DEFAULT_MODEL
from .server import GlamaMCPServer, serve_stdio, TOOLS

__version__ = "1.0.0"

__all__ = [
    "GlamaGateway", "GatewayError", "GlamaMCPServer", "serve_stdio",
    "TOOLS", "BASE_URL", "DEFAULT_MODEL", "__version__",
]