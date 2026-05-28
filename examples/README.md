# examples/

Captured request bodies and reports from each harness audit.

Naming convention:

- `<harness-slug>-req.json` — sanitized request body captured from the
  harness on the wire
- `<harness-slug>-report.json` — output of `tools/check_cache.py` against
  that body
- `<harness-slug>-<date>.flow` — (optional) full mitmproxy flow file

Examples must be sanitized of:

- API keys (in headers or body)
- User PII
- Proprietary source code from the user's repo (replace with stub
  content of similar token length if needed to preserve cache
  semantics)

Keep:

- Full system prompt
- Full tool definitions
- All `cache_control` / `cachePoint` markers
- Conversation structure (replace content text if needed but preserve
  approximate token counts so caching thresholds still trigger)
