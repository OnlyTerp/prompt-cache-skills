# Hermes / Nous Agent

| Field | Value |
|-------|-------|
| Repo | `NousResearch/hermes-agent` |
| Audited commit | `cea87d9139044870752aafdcdf9ca253049ae175` |
| Audit date | `2026-05-27` |
| Auditor | `terp` |
| Provider tested | xAI Responses API on local config; source also covers Anthropic/OpenRouter/Nous/Qwen paths |
| Model tested | `grok-4.3` via `provider: xai-oauth` |
| Verdict | **working** |

## Summary

Hermes is one of the stronger cache implementations in this audit round. Source
inspection shows explicit Anthropic `cache_control` injection, provider-aware
layout selection for native Anthropic vs OpenRouter/Nous envelope-style routes,
Qwen Portal support, and xAI Responses cache routing. A redacted mitm capture of
local `hermes -z` traffic confirmed that the xAI `/v1/responses` request carries
both the body-level `prompt_cache_key` and the `x-grok-conv-id` header. The
second captured xAI call reported `input_tokens_details.cached_tokens: 1792`.

One nuance: the attempted `--resume <session_id>` one-shot minted a new Hermes
session id rather than reusing the prior cache key, so this capture confirms
provider-side cache use but not same-session key reuse through the `-z --resume`
path.

## Source inspection

### Anthropic breakpoints

`agent/prompt_caching.py` implements a single `system_and_3` strategy. It deep
copies the OpenAI-shape message list, marks the system message if present, then
marks the last three non-system messages for a total of at most four Anthropic
breakpoints.

```text
file: agent/prompt_caching.py
lines: 49-79
commit: cea87d9139044870752aafdcdf9ca253049ae175
```

Relevant behavior:

```python
marker = _build_marker(cache_ttl)
if messages[0].get("role") == "system":
    _apply_cache_marker(messages[0], marker, native_anthropic=native_anthropic)
    breakpoints_used += 1
remaining = 4 - breakpoints_used
non_sys = [i for i in range(len(messages)) if messages[i].get("role") != "system"]
for idx in non_sys[-remaining:]:
    _apply_cache_marker(messages[idx], marker, native_anthropic=native_anthropic)
```

`_build_marker()` emits `{"type": "ephemeral"}` by default and adds `ttl:
"1h"` when configured. Tests in `tests/run_agent/test_run_agent.py` verify the
TTL defaults to `5m`, accepts `1h`, and falls back for invalid values.

### Provider policy

`agent.agent_runtime_helpers.anthropic_prompt_cache_policy()` decides when to
inject markers and which layout to use.

```text
file: agent/agent_runtime_helpers.py
lines: 1128-1230
commit: cea87d9139044870752aafdcdf9ca253049ae175
```

Confirmed source branches:

- native Anthropic Messages API returns `(True, True)`;
- OpenRouter Claude and Nous Portal Claude return `(True, False)`;
- Nous Portal Qwen returns `(True, False)`;
- third-party Anthropic-compatible Claude routes return `(True, True)`;
- MiniMax Anthropic-compatible routes are explicitly opted in;
- Alibaba/Qwen-family OpenAI-wire routes are explicitly opted in.

### xAI Responses cache key

Hermes' Responses API transport sends xAI cache routing through two paths:
`extra_body.prompt_cache_key` and `extra_headers.x-grok-conv-id`.

```text
file: agent/transports/codex.py
lines: 183-206
commit: cea87d9139044870752aafdcdf9ca253049ae175
```

The same file sends `prompt_cache_key = session_id` for non-GitHub, non-xAI
Responses API calls, and adds ChatGPT/Codex backend session headers when that
backend is selected.

### Qwen Portal cache marker

`run_agent.py` normalizes Qwen Portal messages to list-of-parts and injects an
Anthropic-style `cache_control` marker on the system message.

```text
file: run_agent.py
lines: 3683-3714
commit: cea87d9139044870752aafdcdf9ca253049ae175
```

## Wire capture

Captured with:

```bash
mitmdump -q -p 8090 -s /tmp/prompt_cache_mitm_summary.py
HTTPS_PROXY=http://127.0.0.1:8090 \
HTTP_PROXY=http://127.0.0.1:8090 \
ALL_PROXY=http://127.0.0.1:8090 \
SSL_CERT_FILE=$HOME/.mitmproxy/mitmproxy-ca-cert.pem \
REQUESTS_CA_BUNDLE=$HOME/.mitmproxy/mitmproxy-ca-cert.pem \
hermes -z "Reply with exactly: OK"
```

The capture summary was redacted before inspection; no raw auth headers or full
prompt text are committed.

### Captured xAI request highlights

```jsonc
{
  "host": "api.x.ai",
  "path": "/v1/responses",
  "request": {
    "model": "grok-4.3",
    "instructions": "<text len=24521>",
    "input": [{ "role": "user", "content": "<text len=22>" }],
    "tools": ["<19 tools summarized>"],
    "prompt_cache_key": "20260527_230345_87f9a0"
  },
  "request_headers": {
    "x-grok-conv-id": "20260527_230345_87f9a0"
  },
  "status_code": 200
}
```

A second captured call showed the same request shape with a fresh one-shot
session id and provider-reported cache use:

```jsonc
{
  "host": "api.x.ai",
  "path": "/v1/responses",
  "request": {
    "model": "grok-4.3",
    "instructions": "<text len=24521>",
    "prompt_cache_key": "20260527_230535_32b7a1"
  },
  "request_headers": {
    "x-grok-conv-id": "20260527_230535_32b7a1"
  },
  "response_usage": {
    "stream_usage_tail": [
      { "input_tokens_details": { "cached_tokens": 1792 } }
    ]
  }
}
```

### Computed hit rate

Not computed from this capture because the streamed xAI usage tail exposed
`cached_tokens` but not the total prompt token denominator in the redacted
summary. The qualitative cache signal is positive: `cached_tokens > 0` on the
second captured call.

## Verdict reasoning

**Working.** Hermes has provider-specific source support for Anthropic,
OpenRouter/Nous, Qwen Portal, and xAI Responses. Live xAI traffic confirmed both
cache-routing fields and a non-zero cached-token response.

The main limitation observed is operational, not a provider-cache bug: `hermes
-z --resume <session_id>` did not reuse the prior one-shot cache key in this
capture. Interactive/resumed-session behavior should be re-tested separately if
someone wants a numeric same-session hit-rate report.

## Patch

None for this repo. No new skill added.

## Reproduction

```bash
mitmdump -q -p 8090 -s /tmp/prompt_cache_mitm_summary.py
HTTPS_PROXY=http://127.0.0.1:8090 \
HTTP_PROXY=http://127.0.0.1:8090 \
ALL_PROXY=http://127.0.0.1:8090 \
SSL_CERT_FILE=$HOME/.mitmproxy/mitmproxy-ca-cert.pem \
REQUESTS_CA_BUNDLE=$HOME/.mitmproxy/mitmproxy-ca-cert.pem \
hermes -z "Reply with exactly: OK"
```

Inspect `/v1/responses` for `prompt_cache_key`, `x-grok-conv-id`, and streamed
usage containing `input_tokens_details.cached_tokens`.
