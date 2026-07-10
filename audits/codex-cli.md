# OpenAI Codex CLI

| Field | Value |
|-------|-------|
| Repo | `openai/codex` |
| Audited commit | `6111791d0b3dd9de93e9cbea6614c85644523979` (default branch) |
| Audit date | 2026-05-27 |
| Auditor | terp (source recon, no live wire capture) |
| Provider tested | OpenAI Responses API (`/v1/responses`) |
| Model tested | n/a (source-only audit; verified by test suite) |
| Verdict | **working** |

## Summary

Codex CLI does prompt caching correctly. It uses a stable
`prompt_cache_key` derived from the session's `thread_id`, which is
constant for the lifetime of a session. Combined with a stable
`base_instructions` system prompt, this gives OpenAI everything it
needs to route subsequent calls to the same backend pod and serve
cached prefix tokens.

There is no `cache_control` to set on the Responses API (that's an
Anthropic-only concept); OpenAI's prefix caching is automatic, and
the only knobs are (a) keep the prefix byte-stable, (b) set
`prompt_cache_key` to a stable value. Codex does both.

## Source inspection

### `prompt_cache_key` is the session thread_id

`codex-rs/core/src/client.rs` line 752:

```rust
let prompt_cache_key = Some(self.state.thread_id.to_string());
```

`thread_id` is set once per session in `ModelClientState`
(line 170: `thread_id: ThreadId`) and never mutated. Every Responses
API call in the session uses the same key.

Permalink: https://github.com/openai/codex/blob/6111791d0b3dd9de93e9cbea6614c85644523979/codex-rs/core/src/client.rs#L752

### Stable instructions

The system prompt comes from `prompt.base_instructions.text`
(`client.rs:727`), defined in `client_common.rs` as a
`BaseInstructions` struct that is built once and reused. No timestamp
or per-request data is injected into it.

### Compaction preserves the key

When a long conversation is compacted (history summarized), Codex
explicitly reuses the same `prompt_cache_key` rather than minting a
new one. The test suite enforces this:

- `codex-rs/core/tests/suite/compact_remote.rs:750` —
  `remote_manual_compact_api_auth_omits_service_tier_and_reuses_prompt_cache_key`
- `codex-rs/core/tests/suite/compact_remote.rs:767` —
  `remote_manual_compact_chatgpt_auth_reuses_service_tier_and_prompt_cache_key`
- `codex-rs/core/tests/suite/prompt_caching.rs:484-487` — asserts
  `prompt_cache_key` doesn't change across overrides.
- `codex-rs/core/src/guardian/tests.rs:1413` — guardian sub-agent
  reuses the parent's cache key.

This is non-trivial: a naive compaction implementation would mint a
new thread/session ID when the conversation is rewritten, blowing the
cache. Codex explicitly doesn't.

### Startup prewarm

`codex-rs/core/src/session_startup_prewarm.rs:174` spawns a background
task at session start that pre-warms the WebSocket transport. This
isn't caching per se but it's an adjacent optimization: by the time
the user's first message arrives, the connection and routing are
already established.

### Sub-agent inheritance

When Codex spawns a sub-agent (Task tool), the parent's `thread_id`
is propagated via `X-Codex-Parent-Thread-Id` header
(`client.rs:624`, `client.rs:651`). Sub-agents share the parent's
cache key, so their startup prompt hits the warm cache from the
parent's session.

## Wire capture

Not performed. Codex's test suite includes assertions that the
request body actually contains `prompt_cache_key` with the expected
value (`compact_remote_parity.rs:890`, `client.rs:789`), which is
strong source evidence. A wire capture audit could confirm
`prompt_tokens_details.cached_tokens` ratios in production but
wouldn't change the verdict.

## Verdict reasoning

**Working.** Codex implements all three correctness criteria for
OpenAI prompt caching:

1. Stable `prompt_cache_key` per session (thread_id).
2. Stable `base_instructions` prefix (no timestamps, no per-request
   data).
3. Preserves cache key across compaction and into sub-agents.

This is the reference for "how to use OpenAI's Responses API caching
correctly." Other harnesses that send `prompt_cache_key = uuid()` or
embed timestamps in their system prompt should pattern-match against
this.

## Patch

None needed.

## Reproduction

Source-only audit. To verify on wire:

```bash
HTTPS_PROXY=http://127.0.0.1:8090 codex chat "list files"
# ...send the same prompt 2-3 more times...
mitmproxy --rfile /tmp/codex.flow
# inspect /v1/responses body: prompt_cache_key should be identical across calls
# inspect response usage: prompt_tokens_details.cached_tokens should grow
```

## Notes

- The session `thread_id` resets on `codex chat` invocation, so a
  brand-new session pays cold-cache cost on its first call. After
  that, all turns within the session hit warm cache.
- For multi-session reuse (e.g. multiple Codex invocations sharing a
  cache), you'd need to externally pin the thread_id — not currently
  exposed as a CLI flag.

## 2026-07-10 provider capability re-audit

This is a provider-doc re-audit, not a fresh source/wire audit of the current
Codex CLI build.

The original 2026-05-27 statement that OpenAI had no explicit breakpoint API is
now historical. GPT-5.6 and later model families support:

- `prompt_cache_options.mode` (`implicit` or `explicit`);
- content-block `prompt_cache_breakpoint`;
- a supported `30m` TTL value;
- `cache_write_tokens`;
- 1.25x cache-write billing.

The stable `thread_id`/`prompt_cache_key` behavior remains a correct foundation,
but a GPT-5.6 harness can now additionally control breakpoint placement. It
should also partition high-volume swarm traffic so one key stays near OpenAI's
approximately 15 requests/minute guidance.

Current Codex CLI breakpoint placement was not inspected in this update. Do not
claim that stock Codex uses the adaptive first-turn/continuation strategy without
a fresh source or wire capture.

Official references:

- <https://developers.openai.com/api/docs/guides/prompt-caching>
- <https://developers.openai.com/api/docs/guides/compaction>
