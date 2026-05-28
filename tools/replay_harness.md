# Replaying a harness's request to verify caching

End-to-end recipe for capturing a real outbound provider call from any
harness, sanitizing it, and re-firing it through `check_cache.py` for
independent verification.

## 1. Start mitmdump

```bash
mitmdump -p 8090 -w /tmp/harness.flow \
  --set confdir=~/.mitmproxy \
  --ssl-insecure
```

Leave running.

## 2. Point the harness at the proxy

Pick whichever the harness supports, in order of preference:

### Option A — harness has a "base URL" override

Many harnesses let you override the provider endpoint:

- Cline / Roo: settings → "Anthropic Base URL" → `http://127.0.0.1:8090`
- Aider: `--openai-api-base http://127.0.0.1:8090/v1`
- Continue: `apiBase` field in config
- Generic Anthropic SDK: `ANTHROPIC_BASE_URL=http://127.0.0.1:8090`
- Generic OpenAI SDK: `OPENAI_BASE_URL=http://127.0.0.1:8090/v1`

This avoids needing the mitmproxy cert installed.

### Option B — HTTPS_PROXY + trust the mitm cert

```bash
export HTTPS_PROXY=http://127.0.0.1:8090
export SSL_CERT_FILE=~/.mitmproxy/mitmproxy-ca-cert.pem
export REQUESTS_CA_BUNDLE=~/.mitmproxy/mitmproxy-ca-cert.pem
export NODE_EXTRA_CA_CERTS=~/.mitmproxy/mitmproxy-ca-cert.pem
```

Then launch the harness with that env. Works for most Python/Node
harnesses. Doesn't work for pinned certs or Go binaries that bake in
their own root store.

## 3. Run the harness for two turns

Make sure the second turn is byte-identical context to the first. The
easiest way: run the exact same one-shot task twice in a row from a
fresh state, or send the same chat message twice.

## 4. Extract the request body

Open the capture:

```bash
mitmproxy --rfile /tmp/harness.flow
```

Find the first call to the provider. Press Enter, then `e` → request →
`copy to clipboard` or pipe to a file.

Programmatic alternative:

```python
from mitmproxy.io import FlowReader
import json, sys

with open("/tmp/harness.flow", "rb") as f:
    for flow in FlowReader(f).stream():
        if "anthropic.com" in flow.request.host or "openai.com" in flow.request.host:
            body = json.loads(flow.request.content.decode())
            print(json.dumps(body, indent=2))
            break
```

Save to `req.json`.

## 5. Sanitize

Remove from `req.json`:

- Any `api-key` / `authorization` headers (the body-only JSON shouldn't
  have these but check).
- User PII in conversation content if you plan to commit the example.

Keep:

- Full system prompt
- Full tool definitions
- Full conversation history
- All `cache_control` fields

## 6. Replay against the live provider

```bash
ANTHROPIC_API_KEY=sk-ant-... \
  python tools/check_cache.py --provider anthropic --body req.json
```

Output should be JSON with cold/warm usage and hit rates.

## 7. Record in the audit file

Copy the cold and warm `usage` blocks into the harness's audit file
under `## Wire capture`. Compute hit rate. Verdict.

## Anti-cheating notes

- Don't replay with a modified body. The whole point is to verify what
  the harness actually sends.
- Don't use `--sleep 600` to test the cache outside its TTL and then
  claim the harness doesn't cache. Use a reasonable sleep (1-30s).
- Two cold calls from different IPs/regions don't share an OpenAI cache
  reliably. Run both calls from the same machine.
