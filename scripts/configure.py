#!/usr/bin/env python3
"""Wire this plugin's stdio server to the current Python and installation path."""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def generate_config(root, python):
    return {"mcpServers": {"zotero-study": {
        "command": python,
        "args": [str(root / "scripts" / "server.py")],
        "startup_timeout_sec": 10,
        "tool_timeout_sec": 90
    }}}


def install_command(root, python, codex="codex"):
    return [codex, "mcp", "add", "zotero-study", "--", python,
            str(root / "scripts" / "server.py")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-codex", action="store_true",
                        help="Also register the MCP server using the installed Codex CLI. Do not use if this server is already provided by an installed Zotero Study plugin.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    config = generate_config(root, sys.executable)
    (root / ".mcp.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print("Configured Zotero Study at " + str(root))
    if args.install_codex:
        executable = shutil.which("codex")
        if not executable:
            parser.error("Codex CLI was not found in PATH. Config generated; add this local plugin in Codex or install the CLI first.")
        subprocess.run(install_command(root, sys.executable, executable), check=True)
        print("MCP server registered. Start a new Codex task to use it.")
    else:
        print("Optional standalone MCP registration (if not installing as a plugin):")
        print(shlex.join(install_command(root, sys.executable)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
