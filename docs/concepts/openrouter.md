# OpenRouter prompt caching

> Status: VERIFIED. Reflects https://openrouter.ai/docs/features/prompt-caching
> as of 2026-08-28 (fetched copy in the 2026-08 research ledger).

## TL;DR

OpenRouter is a **translation layer**: it passes provider-native
caching markers through (Anthropic `cache_control`, OpenAI
`prompt_cache_breakpoint`, `prompt_cache_key`) and, since 2026,
**translates between marker styles when routing cross-provider**. It
uses provider sticky routing to maximize hits under both implicit
(OpenAI, DeepSeek, Gemini 2.5) and explicit (Anthropic) caching. The
critical harness behavior to know: **usage is opt-in** — send
`usage: {"include": true}` or you get no cache fields back at all.

## Mechanics

### Sticky routing

"When using caching (whether automatically in supported models, or via
the `cache_control` property), OpenRouter uses provider sticky routing
to maximize cache hits." No action required beyond stable prompts;
sticky routing is automatic.

### Cross-provider marker translation (2026 verified)

- A text block with Anthropic-style `cache_control` routed to a
  supporting OpenAI model becomes a `prompt_cache_breakpoint`.
- A block marked `prompt_cache_breakpoint` routed to Anthropic or
  Google becomes a default (5-minute) `cache_control`.
- **TTLs are NOT translated**: a `cache_control` ttl is dropped toward
  OpenAI, and request-level `prompt_cache_options` stays OpenAI-only.
  A 1h Anthropic breakpoint routed to OpenAI degrades to OpenAI's
  default retention.

Practical rule: mark blocks in your provider's native style and let
OpenRouter translate, but never rely on a TTL surviving a
cross-provider route.

### Anthropic passthrough details

- Per-block `cache_control` `{"type":"ephemeral"}` (5m) and
  `{"type":"ephemeral","ttl":"1h"}` (1h), max 4 breakpoints.
- **Top-level automatic `cache_control`** is supported on "the
  Anthropic, Google Vertex AI, and Azure providers, as well as Claude
  Platform on AWS" — but **not** on Bedrock InvokeModel/Converse; when
  a top-level field is present, OpenRouter routes only to supporting
  endpoints.

## Usage opt-in (the #1 verification footgun)

Cache accounting is only returned when the request asks for it:

```jsonc
{ "usage": { "include": true } }
```

Without it, `cached_tokens` / `cache_write_tokens` / `cache_discount`
are absent from the response — which looks identical to "caching
broken." [check_cache.py](../../tools/check_cache.py)
`--provider openrouter` injects this automatically and merges the
result back into the reported usage.

## Response shape

```jsonc
"usage": {
  "prompt_tokens": 12000,
  "prompt_tokens_details": { "cached_tokens": 11000 },
  "cache_write_tokens": 12000,
  "cache_discount": -0.12
}
```

`cache_discount` is negative on cache-write-heavy turns (Anthropic
charges a write premium) and positive on read-heavy turns — net it
across a session to measure true savings.

## Provider notes

- **Alibaba** requires explicit breakpoints: add
  `cache_control: {"type": "ephemeral"}` Anthropic-style; it is not
  automatic.
- **Batch** (`:batch` endpoints): `cache_control` works, but lines in a
  batch may process concurrently and in any order — a cache written by
  one line is not guaranteed visible to others. For reliable hits use
  `ttl: "1h"` breakpoints on the shared prefix.
- `prompt_cache_key` passes through to supporting providers.

## Harness notes

- Any harness that talks to OpenRouter inherits whatever markers its
  per-provider adapters emit — a harness broken on direct Anthropic is
  broken through OpenRouter too, plus the usage opt-in trap on top.
- Audits touching OpenRouter paths:
  [audits/opencode.md](../../audits/opencode.md) (OpenAI-compat
  detection), [audits/hermes-nous.md](../../audits/hermes-nous.md).

## References

- https://openrouter.ai/docs/features/prompt-caching

---

_Last verified against OpenRouter docs: 2026-08-28._
