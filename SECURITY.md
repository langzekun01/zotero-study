# Security and privacy

- The server connects only to the local Zotero API on loopback. Do not forward port 23119 to another machine or the public internet.
- It ignores HTTP proxy environment settings and rejects HTTP redirects and remote attachment URLs.
- Retrieved text is returned to the calling AI client and may be processed according to that client's data policies. Local Zotero access does not make the whole AI workflow offline.
- Local write keys are held only in process memory and are never returned through MCP. New notes may sync through the user's existing Zotero settings.
- The only write tool creates a new child note. It does not edit or delete existing records.
- A stable request ID and a persistent note tag help recover from interrupted saves. This is not an exactly-once guarantee across concurrent server processes; avoid issuing the same save simultaneously from multiple clients.
- Never include live library content, credentials, private filesystem paths or personal PDFs in public issue reports.

For security problems, use GitHub's private vulnerability reporting if it is enabled for this repository. Otherwise open a minimal issue asking for a private reporting channel without disclosing exploit details or sensitive data.
