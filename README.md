# Zotero Study · 文献学习助手

A local Zotero MCP server and Codex skill for finding papers, understanding annotations, and saving bilingual study notes.

连接本机 Zotero，在 Codex 中检索论文、阅读笔记和 PDF 批注，并按需保存中英混合学习总结。

**Independent community project. Not an official Zotero or OpenAI integration.** This is a Codex/MCP integration, not a Zotero `.xpi` extension.

## What it does

| Capability | Description |
|---|---|
| Find papers / 检索文献 | Search titles, creators, years, tags and collections; supports locally available group libraries |
| Read notes / 阅读笔记 | Fetch bibliographic metadata, abstracts and existing notes |
| Read annotations / 阅读批注 | Retrieve PDF highlights, comments and page labels |
| Read text / 阅读正文 | Read indexed attachment text in bounded chunks with indexing coverage |
| Locate PDFs / 定位附件 | Resolve existing local attachment paths for visual PDF inspection |
| Save summaries / 保存总结 | Create a new child note when requested, using Zotero's native write authorization |

Python 3.9+; standard library only. No package installation, cloud API key, or additional model service is required by this server. The AI client itself has its own requirements.

## Quick start

### 1. Enable Zotero's local API

Keep the Zotero desktop application open. Go to:

**Settings → Advanced → Allow other applications on this computer to communicate with Zotero**

中文界面：**设置 → 高级 → 允许此计算机上的其他应用程序与 Zotero 通信**。

Local reads do not require an API key. Creating notes requires **Zotero 10+** and a native Zotero authorization dialog. Choose the authorization duration in that dialog; the server keeps the granted key in memory only.

### 2. Download and configure

```sh
git clone https://github.com/langzekun01/zotero-study.git
cd zotero-study
python3 scripts/configure.py
python3 scripts/server.py --check
```

Use `python` instead of `python3` where appropriate. The configuration script creates `.mcp.json` with the Python executable and absolute source path on **your** computer. This generated file is ignored by Git and is not shipped in the repository. Run the script again after moving the folder or changing Python.

### 3. Connect to Codex

Choose **one** installation route to avoid duplicate tools.

**Standalone MCP server:** if the Codex CLI is in your PATH, run:

```sh
python3 scripts/configure.py --install-codex
```

This uses `codex mcp add` to register the server. It does not install the bundled skill. Start a new Codex task. If the CLI is unavailable, the generated `.mcp.json` provides the command and arguments for manual MCP setup.

**Full Codex plugin:** first run `configure.py`, then ask Codex's `plugin-creator` skill to register this local folder in your personal plugin directory. The package contains `.codex-plugin/plugin.json`, the generated `.mcp.json`, and `skills/zotero-study/SKILL.md`. Install it from that local source and start a new task. This repository is not yet a one-click public marketplace listing.

Other MCP clients can launch `scripts/server.py` with Python using stdio. Their setup and approval UI may differ.

## Example prompts

- “Find graphene papers in my Zotero library.”
- “在 Zotero 里找到这篇论文，结合我的高亮解释基本概念。”
- “Explain the physical picture, experimental evidence, and limitations before showing equations.”
- “把刚才的中英混合总结保存到这篇论文下，作为新的学习笔记。”

The bundled skill treats paper content as source material, distinguishes evidence from interpretation, and saves only when the user asks. Saving a note may show a Zotero dialog. After a timeout, keep the **same request ID and content** when checking/retrying the save.

## Tools

| Tool | Purpose |
|---|---|
| `connection_status` | Check connectivity and explain setup problems |
| `list_libraries` | List the personal library and local group libraries |
| `list_collections` | List collections, their parents and pagination |
| `search_items` | Search papers with optional tag/collection filters |
| `get_item` | Read complete metadata or a note |
| `get_children` | Read child attachments/notes, or annotations under an attachment |
| `get_fulltext` | Read a chunk of an attachment's indexed text |
| `get_attachment_path` | Resolve an existing local attachment path |
| `create_study_note` | Create a new child note under a regular bibliographic item |

An attachment key is different from its parent paper key. Use `get_children` on the paper to find its PDF attachment, then use that attachment key for full text and annotations. Follow `next_start` and `next_offset` when more data is needed.

## Privacy and limitations

The server only talks to Zotero on loopback. It has no telemetry and makes no separate cloud or model calls. **Retrieved content is returned to the calling Codex/AI conversation**, so the complete workflow is not necessarily offline. Newly created notes may sync according to the user's existing Zotero settings.

- Never publish a personal Zotero database, PDFs, notes, credentials or generated `.mcp.json` in this repository.
- Full text comes from Zotero's index. It may be absent or incomplete for undownloaded, unindexed or scanned attachments. No OCR is included.
- Indexed text does not preserve all figures, equations or layout. Use a PDF inspection tool on the resolved file for visual evidence.
- Notes are created from HTML-escaped plain text. Existing notes and records are never overwritten or deleted by this version.
- Retry detection helps prevent duplicate notes, but concurrent writes from multiple server processes are not an exactly-once transaction.
- MCP uses stdio with the 2025-06-18 handshake, also accepting 2024-11-05 and 2025-03-26. It does not implement the newer stateless protocol; clients must support the older handshake or fallback.

## Development and tests

```sh
python3 -m unittest discover -s tests -v
```

Tests cover tool discovery, Unicode, pagination, argument validation, annotations, text coverage, loopback restrictions, HTML escaping, denied/expired authorization, partial write failures and interrupted-save recovery. They use synthetic records and never write to a real library. GitHub Actions runs the suite on Python 3.9 and 3.13.

Local reads and PDF paths were manually checked on macOS with Zotero 10.0.4. Note creation has automated simulated-API coverage; a live write has not yet been verified. Other desktop platforms have not been manually verified.

## Troubleshooting

| Symptom | Next step |
|---|---|
| Cannot reach local Zotero | Open Zotero, enable its local API, and check local network permission in your client |
| HTTP 403 on reads | Enable communication with other applications in Advanced settings |
| Write authorization denied | Respect the denial; do not repeatedly trigger the prompt |
| No full text | Download/index the attachment in Zotero, or inspect the existing PDF directly |
| No annotations | Query the PDF attachment's children, not only the paper's children |
| Save timed out | Keep the same request ID/content and check before trying again |
| Folder moved | Rerun `configure.py` and update/reinstall the connection |

## License and references

[MIT](LICENSE). Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

Built against the official [Zotero Local API](https://www.zotero.org/support/dev/web_api/v3/local_api), [read endpoints](https://www.zotero.org/support/dev/web_api/v3/basics), [write endpoints](https://www.zotero.org/support/dev/web_api/v3/write_requests), and [full-text API](https://www.zotero.org/support/dev/web_api/v3/fulltext_content). See [Codex MCP documentation](https://developers.openai.com/learn/docs-mcp) and [plugin packaging](https://developers.openai.com/plugins/build/plugins) for host setup.
