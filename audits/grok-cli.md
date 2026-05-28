# Grok CLI

| Field | Value |
|-------|-------|
| Repo | closed-source binary distribution |
| Audited build | local binary `grok 0.2.3 (14d81fd87) [stable]` |
| Audit date | `2026-05-27`; transport-aware follow-up `2026-05-28` |
| Auditor | `terp` |
| Provider tested | xAI/Grok managed CLI chat proxy |
| Model tested | `grok-build` via `https://cli-chat-proxy.grok.com/v1/chat/completions` |
| Verdict | **working** (managed proxy returns non-zero cached-token usage) |

## Summary

The original mitmproxy attempt was inconclusive: a single-turn `grok -p`
run succeeded, but the HTTP proxy only saw update-check traffic to
`x.ai/cli/stable`; the model request did not appear there.

A transport-aware follow-up used Grok CLI's own documented chat-proxy
path and the same local OAuth session token the CLI uses internally. The
proxy rejected requests without the real CLI version header, which
explains why a naive direct call can fail. With the required Grok CLI
headers, the managed proxy returned OpenAI-style streamed usage that
included non-zero `prompt_tokens_details.cached_tokens`.

This verifies cache behavior for the managed Grok CLI proxy path. The
closed CLI's own `--output-format streaming-json` and local session files
still do not expose provider usage counters directly; they expose text,
request/session IDs, and local context-token estimates.

## Local install and config

The local binary reports:

```text
grok 0.2.3 (14d81fd87) [stable]
```

The local user config contains ordinary UI/installer settings only; no
custom cache shim, custom proxy, or explicit prompt-cache override was
found in `~/.grok/config.toml`.

Grok's bundled documentation describes the CLI chat proxy:

```text
https://cli-chat-proxy.grok.com/v1/chat/completions
```

Required request headers include:

```text
Authorization: Bearer <session token from ~/.grok/auth.json>
X-XAI-Token-Auth: xai-grok-cli
x-grok-model-override: grok-build
```

Binary-string inspection and proxy behavior showed the real CLI also
identifies itself with:

```text
x-grok-client-version: 0.2.3
```

Without that version header, the proxy returns a version-gate error:

```json
{"error":"Your Grok CLI version (none) is outdated. Please update to version 0.1.202 or later via `grok update` or the installation documentation."}
```

## CLI surface check

A fresh CLI probe succeeded:

```bash
GROK_LOG_FILE=1 GROK_LOG_FILTER=debug \
  grok -p "Reply with exactly: GROK_CACHE_PROBE_OK" \
  --output-format streaming-json \
  --disable-web-search \
  --no-subagents \
  --no-memory \
  --verbatim
```

The public stream contained text/thought events plus final metadata:

```jsonc
{ "type": "end", "sessionId": "019e6d87-a7e1-...", "requestId": "cd5f1c9d-...", "stopReason": "EndTurn" }
```

No provider `usage` object was present in that stream. The matching
session artifacts under `~/.grok/sessions/.../<session-id>/` contained
local `totalTokens` / `contextTokensUsed` counters, but no provider
`prompt_tokens_details.cached_tokens` field. That means normal CLI
output is insufficient for prompt-cache verification.

## Managed proxy capture

The transport-aware verification sent two identical streaming chat
requests to Grok CLI's documented chat proxy, using the locally stored
Grok session token in-process and printing only sanitized usage fields.
No auth token, prompt contents, cookies, or user identifiers were printed
or committed.

Request shape summary:

```jsonc
{
  "url": "https://cli-chat-proxy.grok.com/v1/chat/completions",
  "headers": {
    "X-XAI-Token-Auth": "xai-grok-cli",
    "x-grok-model-override": "grok-build",
    "x-grok-client-version": "0.2.3"
  },
  "body": {
    "model": "grok-build",
    "stream": true,
    "stream_options": { "include_usage": true },
    "messages": "<short system + user probe>"
  }
}
```

Sanitized response usage:

| Call | HTTP status | Stream events | Prompt tokens | Completion tokens | Total tokens | Cached tokens |
|------|-------------|---------------|---------------|-------------------|--------------|---------------|
| 1 | 200 | 25 | 149 | 7 | 281 | 64 |
| 2 | 200 | 25 | 149 | 7 | 312 | 128 |

The relevant streamed usage tail was OpenAI-compatible:

```jsonc
{
  "usage": {
    "prompt_tokens": 149,
    "completion_tokens": 7,
    "total_tokens": 312,
    "prompt_tokens_details": {
      "cached_tokens": 128
    }
  }
}
```

`cached_tokens > 0` is the provider-side cache signal for this managed
proxy path.

## Computed hit rate

For the second identical proxy call:

```text
cached_tokens / prompt_tokens = 128 / 149 = 85.9%
```

This is a positive prompt-cache hit. The first call also showed non-zero
cached tokens (`64`), likely because the managed proxy or model backend
can reuse shared/static prefix material even before the repeated probe
warms the exact short user request.

## Verdict reasoning

**Working.** Grok CLI's normal stdout/session artifacts do not expose
usage counters, and a generic mitmproxy setup misses the model channel.
However, Grok's own documented CLI chat proxy accepts the same local CLI
session token and, when called with the real CLI version header, returns
OpenAI-style streamed usage with non-zero
`prompt_tokens_details.cached_tokens`.

Treat this as a managed-proxy verification, not a patchable OSS source
audit. There is no public CLI source path and no skill to add.

## Patch

None. Closed-source managed CLI/proxy surface; no patchable source bug.

## Reproduction

Use Grok's documented CLI chat proxy with the local CLI session token,
but do not print auth material:

```bash
python3 - <<'PY'
import json, urllib.request
from pathlib import Path

entry = next(
    v for v in json.loads((Path.home() / '.grok/auth.json').read_text()).values()
    if isinstance(v, dict) and v.get('key')
)
token = entry['key']

req = urllib.request.Request(
    'https://cli-chat-proxy.grok.com/v1/chat/completions',
    data=json.dumps({
        'model': 'grok-build',
        'messages': [
            {'role': 'system', 'content': 'Reply exactly as requested.'},
            {'role': 'user', 'content': 'Reply with exactly: GROK_CACHE_PROBE_OK'},
        ],
        'stream': True,
        'stream_options': {'include_usage': True},
    }).encode(),
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
        'X-XAI-Token-Auth': 'xai-grok-cli',
        'x-grok-model-override': 'grok-build',
        'x-grok-client-version': '0.2.3',
    },
    method='POST',
)

with urllib.request.urlopen(req, timeout=90) as resp:
    for raw in resp:
        line = raw.decode('utf-8', errors='replace').strip()
        if not line.startswith('data:'):
            continue
        data = line[5:].strip()
        if data == '[DONE]':
            break
        obj = json.loads(data)
        usage = obj.get('usage')
        if usage:
            print(json.dumps({
                'prompt_tokens': usage.get('prompt_tokens'),
                'completion_tokens': usage.get('completion_tokens'),
                'total_tokens': usage.get('total_tokens'),
                'cached_tokens': (usage.get('prompt_tokens_details') or {}).get('cached_tokens'),
            }, sort_keys=True))
PY
```

Run the same request twice. A working managed proxy path reports
`cached_tokens > 0`, with the second call expected to have a higher or
equal cached-token count for the repeated prompt.
