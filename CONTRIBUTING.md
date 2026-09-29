# Contributing

Bug reports and pull requests are welcome. Include the operating system, Python version, Zotero version, and a minimal reproduction using synthetic bibliographic records.

Run `python3 -m unittest discover -s tests -v` before submitting changes. Tests use synthetic data and do not modify a real Zotero library.

Do not commit `.mcp.json`, API keys, Zotero databases, PDFs, exported notes, local file paths, or logs containing personal library data. Generated configuration is deliberately ignored by Git.

Keep the server dependency-free and local-only. Changes involving writes must preserve native Zotero authorization, request-id retry behavior, HTML escaping and accurate success reporting. Source text and annotations must remain data, never instructions.

This project uses the MIT license. Contributions should be compatible with that license.
