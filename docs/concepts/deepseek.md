# DeepSeek prompt caching

> Status: VERIFIED. Numbers reflect DeepSeek's documented behavior as of
> 2026-08-28. Sources: https://api-docs.deepseek.com/guides/kv_cache and
> https://api-docs.deepseek.com/quick_start/pricing (fetched copies in the
> 2026-08 research ledger).

## TL;DR

DeepSeek caching is **fully automatic and free to engage** — there is no
request field to set and no way to opt out. Disk-backed KV caching stores
prefix units server-side; you optimize by shaping prompt prefixes, not by
placing breakpoints. Cache hits are billed at a small fraction of the
miss price (deepseek-v4-flash: $0.007/M off-peak vs $0.22/M miss —
**97% off**; deepseek-v4-pro: $0.022/M vs $0.66/M).

## Mechanics

### Sliding Window Attention changes the matching rule (2026 verified)

Due to SWA (Sliding Window Attention), "the storage and matching of
cached prefixes differs from before. Each cached prefix is an
independent, complete unit. A subsequent request can only hit the cache
if it fully matches a cache prefix unit."

**Practical consequence:** partial-prefix hits are gone. A request
either fully matches a stored unit or gets zero credit for the shared
part. Keep conversation prefixes byte-stable end to end; a mid-prefix
edit orphans everything after it.

### Where cache units are written

"Each request will produce two cache prefix units at the end position
of the user input and the end position of the model output." You don't
choose the persistence points — every turn writes its boundaries.

### TTL / eviction

No configurable TTL. "Once the cache is no longer in use, it will be
automatically cleared, usually within a few hours to a few days." Cache
construction takes seconds. No guaranteed 100% hit rate — verify on
wire, don't assume.

## Request shape

Nothing to set. The OpenAI-format endpoint is `https://api.deepseek.com`
and there is also an **Anthropic-format endpoint**
(`https://api.deepseek.com/anthropic`) plus Responses API support on all
models — caching works the same on every wire format.

## Response shape

```jsonc
"usage": {
  "prompt_tokens": 12000,
  "prompt_cache_hit_tokens": 11000,
  "prompt_cache_miss_tokens": 1000,
  ...
}
```

Top-level fields (NOT nested in a details object):
`prompt_cache_hit_tokens` + `prompt_cache_miss_tokens`, which sum to
`prompt_tokens`.

## Pricing (per 1M tokens, off-peak / peak; peak = 01:00–04:00 and 06:00–10:00 UTC Mon–Fri)

| Model | Cache hit | Cache miss | Output |
|-------|-----------|------------|--------|
| deepseek-v4-flash (`DeepSeek-V4-Flash-0731`) | $0.007 / $0.014 | $0.22 / $0.44 | $0.66 / $1.32 |
| deepseek-v4-pro (`DeepSeek-V4-Pro-0813`) | $0.022 / $0.044 | $0.66 / $1.32 | $1.98 / $3.96 |
| deepseek-v4-flash-vision-exp | mirrors flash | | |

Context length: 1M. Off-peak rates are half of peak.

## What does NOT cache

- Nothing is user-controllable; there is no breakpoint API.
- Partial prefixes (SWA whole-unit matching) — see above.
- Cross-model: each model's cache is its own.

## Harness notes

- [check_cache.py](../../tools/check_cache.py) `--provider deepseek`
  reads the top-level hit/miss fields directly.
- Harnesses that send Anthropic-format requests can hit the
  `/anthropic` endpoint; `cache_control` blocks there are ignored for
  DeepSeek models — the disk cache does the work.

## References

- KV cache guide: https://api-docs.deepseek.com/guides/kv_cache
- Pricing: https://api-docs.deepseek.com/quick_start/pricing

---

_Last verified against DeepSeek docs: 2026-08-28._
