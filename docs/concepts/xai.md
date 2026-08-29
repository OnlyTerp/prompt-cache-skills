# xAI (Grok) prompt caching

> Status: VERIFIED. Numbers reflect xAI's documented behavior as of
> 2026-08-28. Sources: https://docs.x.ai/developers/advanced-api-usage/prompt-caching
> (+ /how-it-works, /maximizing-cache-hits, /usage-and-pricing,
> /best-practices) and https://docs.x.ai/developers/pricing.

## TL;DR

xAI caching is **automatic on every Grok language model**. The single
highest-leverage thing a harness can do is set the routing header
**`x-grok-conv-id`** (Chat Completions) or the body field
**`prompt_cache_key`** (Responses API) — both pin a conversation to one
server, and "cache entries are stored per-server." Cache hits bill at a
steep discount (grok-4.6: $0.50/M vs $2.00/M input — **75% off**).

## Mechanics

### Automatic, prefix-based, no breakpoints

"The xAI API performs prompt caching **automatically**." Matching runs
from the start of the `messages` array; the matched portion is the
prefix and is served from cache. There is no breakpoint API to place.

### Routing is the whole game

- Chat Completions: `x-grok-conv-id` HTTP header — "routes requests
  with the same conversation ID to the same server. Since cache
  entries are stored per-server, this maximizes your cache hit rate."
- Responses API: `prompt_cache_key` body field — "functions identically
  to setting `x-grok-conv-id`."

Use a stable per-conversation identifier. A per-request random value is
worse than omitting the header (it routes every turn to a fresh server).

### TTL

No fixed TTL is documented: "Cache entries can be evicted at any time
due to server load or restarts." The conv-id routing is the retention
mechanism. Any specific TTL number is UNVERIFIED — treat xAI as
opportunistic and verify on wire.

## Request shape (Chat Completions)

```http
POST /v1/chat/completions
x-grok-conv-id: conv-8f3a
```

No body changes required. For Responses API, add
`"prompt_cache_key": "conv-8f3a"` to the body.

## Response shape

```jsonc
// Chat Completions
"usage": { "prompt_tokens": 12000,
           "prompt_tokens_details": { "cached_tokens": 11000,
                                      "text_tokens": 1000 } }
// Responses API
"usage": { "input_tokens": 12000,
           "input_tokens_details": { "cached_tokens": 11000 } }
```

Hit semantics (documented): `0` = miss, `> 0` = hit, equal to
`prompt_tokens` = full hit.

## Pricing (per 1M tokens, input / cached input)

| Model | <200k context | ≥200k (long context) |
|-------|---------------|----------------------|
| grok-4.6 | $2.00 / $0.50 | $4.00 / $1.00 |
| grok-4.5 | $2.00 / $0.30 | $4.00 / $0.60 |
| grok-4.3 | $1.25 / $0.20 | $2.50 / $0.40 |
| grok-build-0.1 | $1.00 / $0.20 | $2.00 / $0.40 |

Long-context thresholds apply to total prompt tokens including cached.
Batch (20% off) applies to cached tokens; priority-tier 2x applies
after cache discounts.

## What does NOT cache

- Nothing user-controllable beyond routing.
- Across servers (unless conv-id/prompt_cache_key pins routing).
- Across models.

## Harness notes

- [check_cache.py](../../tools/check_cache.py) `--provider xai` sends
  the `x-grok-conv-id` header on both replay requests.
- Harness audits that observed `prompt_cache_key` + `x-grok-conv-id` on
  real traffic: [audits/hermes-nous.md](../../audits/hermes-nous.md),
  [audits/grok-cli.md](../../audits/grok-cli.md).

## References

- Prompt caching: https://docs.x.ai/developers/advanced-api-usage/prompt-caching
- Maximizing hits: https://docs.x.ai/developers/advanced-api-usage/prompt-caching/maximizing-cache-hits
- Pricing: https://docs.x.ai/developers/pricing

---

_Last verified against xAI docs: 2026-08-28._
