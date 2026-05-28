# OpenAI Codex Desktop

| Field | Value |
|-------|-------|
| Repo | closed-source desktop; shares `openai/codex` backend/app-server behavior where visible |
| Audited commit | Desktop build local logs from `2026-05-27`; CLI package `@openai/codex` `0.125.0`; source reference `openai/codex` audit at `6111791d0b3dd9de93e9cbea6614c85644523979` |
| Audit date | `2026-05-27` |
| Auditor | `terp` |
| Provider tested | ChatGPT Codex backend (`chatgpt.com/backend-api/codex/responses`) |
| Model tested | ChatGPT-account Codex backend; attempted `gpt-5.1-codex-mini` was rejected by account policy |
| Verdict | **working (inferred)** |

## Summary

Codex Desktop is closed source, but the local install and wire capture line up
with the open-source Codex CLI/app-server cache model: a stable thread id is used
as the cache scope, and backend requests carry that id as `session_id` and
`x-client-request-id`. A direct Linux Codex CLI `0.125.0` run reached the
ChatGPT Codex backend through mitmproxy and upgraded `/backend-api/codex/responses`
with both headers set to the same thread id.

This audit therefore inherits the stronger source evidence from
[`codex-cli.md`](codex-cli.md), but grades Desktop as **inferred** because the
Electron application itself is not published as source and the captured run ended
with a model/account-policy 400 before a successful token-usage block was
observed.

## Source inspection

### Open-source Codex cache behavior

The reference Codex CLI audit found that `openai/codex` sets
`prompt_cache_key = thread_id`, keeps `base_instructions` stable, and preserves
the key across compaction/sub-agents. See [`codex-cli.md`](codex-cli.md) for the
line-level source citations and test references.

### Local desktop evidence

Local Codex Desktop logs exist under `AppData/Local/Codex/Logs`. The desktop
logs include app-server routing and token usage events. A sampled local log
reported title-generation usage as:

```text
[ephemeral-generation] ephemeral_generation_token_usage cachedInputTokens=0
feature=thread_title inputTokens=26267 model=gpt-5.4-mini ...
```

That log line is useful for proving Desktop records cache counters, but it is a
thread-title generation event, not the main agent request, so it is not used as a
negative verdict.

The local Linux CLI package metadata reads:

```json
{
  "name": "@openai/codex",
  "version": "0.125.0",
  "repository": {
    "url": "git+https://github.com/openai/codex.git",
    "directory": "codex-cli"
  }
}
```

## Wire capture

Captured with the direct Linux Codex binary to avoid the WSL/Windows Node UNC
wrapper issue:

```bash
mitmdump -q -p 8090 -s /tmp/prompt_cache_mitm_summary.py
HTTPS_PROXY=http://127.0.0.1:8090 \
HTTP_PROXY=http://127.0.0.1:8090 \
ALL_PROXY=http://127.0.0.1:8090 \
SSL_CERT_FILE=$HOME/.mitmproxy/mitmproxy-ca-cert.pem \
REQUESTS_CA_BUNDLE=$HOME/.mitmproxy/mitmproxy-ca-cert.pem \
~/.local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex/codex \
  exec --skip-git-repo-check --sandbox read-only --model gpt-5.1-codex-mini --json \
  "Reply with exactly: OK"
```

### Captured request highlights

The run reached the ChatGPT Codex backend and upgraded a websocket/streaming
endpoint:

```jsonc
{
  "host": "chatgpt.com",
  "method": "GET",
  "path": "/backend-api/codex/responses",
  "status_code": 101,
  "request_headers": {
    "session_id": "019e6c8e-0a98-7850-8fea-026811f70443",
    "x-client-request-id": "019e6c8e-0a98-7850-8fea-026811f70443"
  }
}
```

The selected model then failed before a successful generation:

```json
{
  "status": 400,
  "error": {
    "type": "invalid_request_error",
    "message": "The 'gpt-5.1-codex-mini' model is not supported when using Codex with a ChatGPT account."
  }
}
```

### Computed hit rate

Not computed. The capture proves stable backend cache-scope headers on the wire,
but no successful usage block was captured for this model/account combination.

## Verdict reasoning

**Working (inferred).** The published Codex source and tests already prove the
OpenAI Responses API `prompt_cache_key` path. The local Desktop/CLI backend wire
shape additionally shows a stable thread id being sent as both `session_id` and
`x-client-request-id` to the ChatGPT Codex backend. Because Desktop itself is
closed and this capture ended on account-policy rejection, the grade is not as
strong as the CLI audit.

## Patch

None. No new skill added.

## Reproduction

Use the same mitm command above, but select a model accepted by the logged-in
ChatGPT account. Inspect `chatgpt.com/backend-api/codex/responses` for stable
`session_id` / `x-client-request-id` across turns and usage fields for cached
input tokens.
