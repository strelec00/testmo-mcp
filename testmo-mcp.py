"""
Testmo MCP Server — FastMCP implementation.

Provides tools for AI assistants to manage test cases, folders, projects,
runs, automation runs, attachments, and more via the Testmo REST API.
"""

from testmo.server import mcp

# Import tool modules to register all tools on the mcp instance
import testmo.tools.projects  # noqa: F401
import testmo.tools.folders  # noqa: F401
import testmo.tools.milestones  # noqa: F401
import testmo.tools.cases  # noqa: F401
import testmo.tools.runs  # noqa: F401
import testmo.tools.attachments  # noqa: F401
import testmo.tools.automation  # noqa: F401
import testmo.tools.issues  # noqa: F401
import testmo.tools.composite  # noqa: F401
import testmo.tools.utility  # noqa: F401

if __name__ == "__main__":
    mcp.run(transport="stdio")
