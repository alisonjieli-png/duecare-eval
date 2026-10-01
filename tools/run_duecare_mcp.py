#!/usr/bin/env python3
"""Launch the read-only MCP stdio adapter from a source checkout."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from duecare_eval.mcp_server import main

if __name__ == "__main__":
    main()
