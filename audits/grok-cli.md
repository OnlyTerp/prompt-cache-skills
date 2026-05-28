# Grok CLI

| Field | Value |
|-------|-------|
| Repo | closed-source binary distribution |
| Audited commit | local binary `grok 0.2.3 (14d81fd87) [stable]` |
| Audit date | `2026-05-27` |
| Auditor | `terp` |
| Provider tested | xAI/Grok managed backend |
| Model tested | default Grok Build CLI model |
| Verdict | **unverified (model call not captured)** |

## Summary

Grok CLI is a closed-source binary. A single-turn run through the CLI succeeded
and returned `OK`, but the model request did not appear in the mitmproxy capture:
only update-check traffic to `x.ai/cli/stable` was visible. That makes prompt
cache behavior unverified from this workstation capture.

This audit should not inherit Hermes' xAI result. Hermes uses xAI's public
Responses API and was captured sending `prompt_cache_key` plus `x-grok-conv-id`.
Grok CLI appears to use a different transport or proxy bypass for the model call.

## Source inspection

No source code was available in the local install. The local binary reports:

```text
grok 0.2.3 (14d81fd87) [stable]
```

The CLI exposes a non-interactive single-turn mode:

```text
Usage: grok [OPTIONS] [COMMAND]
-p, --single <PROMPT>        Single-turn prompt. Prints the response to stdout and exits
--output-format <FORMAT>     plain | json | streaming-json
--model <MODEL>              Model ID to use
--reasoning-effort <EFFORT>  Reasoning effort for reasoning models
```

No local source file or config surface was found that exposes `prompt_cache_key`,
`x-grok-conv-id`, or provider usage counters.

## Wire capture

Captured with:

```bash
mitmdump -q -p 8090 -s /tmp/prompt_cache_mitm_summary.py
HTTPS_PROXY=http://127.0.0.1:8090 \
HTTP_PROXY=http://127.0.0.1:8090 \
ALL_PROXY=http://127.0.0.1:8090 \
SSL_CERT_FILE=$HOME/.mitmproxy/mitmproxy-ca-cert.pem \
REQUESTS_CA_BUNDLE=$HOME/.mitmproxy/mitmproxy-ca-cert.pem \
grok -p "Reply with exactly: OK" --output-format json
```

The command returned:

```json
{
  "text": "OK",
  "stopReason": "EndTurn",
  "sessionId": "019e6c8c-e75b-7422-8e97-4304b4a8ba7b",
  "requestId": "161b4c0f-640b-4411-9378-d4840624359a"
}
```

### Captured request highlights

Only update-check requests appeared in the redacted mitm summary:

```jsonc
{ "host": "x.ai", "method": "GET", "path": "/cli/stable", "status_code": 200 }
{ "host": "x.ai", "method": "GET", "path": "/cli/stable", "status_code": 200 }
```

No `api.x.ai`, `/v1/responses`, protobuf, websocket, or usage-bearing model call
was captured by the HTTP proxy.

### Computed hit rate

Not computed. The model transport bypassed or was invisible to this mitmproxy
configuration.

## Verdict reasoning

**Unverified.** The CLI can answer a prompt, but the relevant model call was not
captured, and there is no source evidence available locally. Re-audit with a
transport-aware capture method for the binary's actual model channel before
publishing a working/broken cache verdict.

## Patch

None. No public source path or verified patchable bug.

## Reproduction

Use the command above and inspect whether the model call appears. If a future
version honors `HTTPS_PROXY` for the model channel, check for xAI cache-routing
surfaces: body-level `prompt_cache_key`, `x-grok-conv-id`, and
`input_tokens_details.cached_tokens` in streamed usage.
