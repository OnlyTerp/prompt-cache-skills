# Mistral prompt caching

> Status: VERIFIED. Reflects https://docs.mistral.ai/studio/conversations/advanced/prompt-caching
> as of 2026-08-28 — Mistral now ships first-party prompt-caching docs
> (previously absent; the May 2026 audit found none).

## TL;DR

Mistral prompt caching is **automatic prefix matching** with an
**opt-in routing field `prompt_cache_key`** that "increases the chance
of a cache hit, but doesn't guarantee one." Cached prompt tokens bill
at **10% of the standard input price**. No cache-write premium is
documented.

## Mechanics

- **Mechanism:** automatic; matching on request prefix. No breakpoint
  API.
- **Routing field:** `"prompt_cache_key"` on Chat Completions requests
  — "Use a stable application-level identifier, such as a conversation
  ID, session ID, or workflow ID. Don't include secrets, API keys, or
  sensitive user data in `prompt_cache_key`."
- **TTL / minimums / invalidation:** none documented — all UNVERIFIED.
  Treat as opportunistic; verify on wire.

## Request shape

```jsonc
{
  "model": "mistral-large-latest",
  "prompt_cache_key": "session-4f2a",
  "messages": [...]
}
```

## Billing mechanics

"The billable uncached input tokens are `prompt_tokens - cached_tokens`."

Worked example from the docs: 5 uncached input tokens at standard
price; 1008 cached input tokens at 10%.

## Response shape

`cached_tokens` appears in the prompt-token accounting
(`prompt_tokens_details`). There is no separate cache-write field —
absence of one is consistent with "no separate cache-write charge."

## Harness notes

- The existing skill
  [opencode-mistral-cache-key](../../skills/opencode-mistral-cache-key/SKILL.md)
  predates first-party docs; its `prompt_cache_key` guidance is now
  CONFIRMED by Mistral's documentation (2026-08-28).
- [check_cache.py](../../tools/check_cache.py) `--provider custom`
  covers Mistral-compatible relays reading
  `prompt_tokens_details.cached_tokens`.

## References

- https://docs.mistral.ai/studio/conversations/advanced/prompt-caching

---

_Last verified against Mistral docs: 2026-08-28._
