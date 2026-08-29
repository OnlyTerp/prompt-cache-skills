# Anthropic prompt caching

> Status: VERIFIED. Numbers reflect Anthropic's documented behavior as of
> 2026-08-28 (full citation set in
> `C:\Users\User\prompt-cache-research-2026-08\prompt-caching-state-2026-08.md`).
> Verify against https://platform.claude.com/docs/en/build-with-claude/prompt-caching
> before citing in an audit.

## TL;DR

Anthropic prompt caching now has **two modes**:

1. **Automatic caching** (newer, simpler): pass a top-level
   `cache_control: {"type": "ephemeral"}` field on the request. Anthropic
   auto-places the breakpoint on the last cacheable block and moves it
   forward as the conversation grows. Best for multi-turn agent loops
   where you don't want to manage breakpoints by hand.
2. **Explicit breakpoints** (original API, finer control): set
   `cache_control: {"type": "ephemeral"}` directly on individual content
   blocks. Up to 4 breakpoints per request. Use when you have multiple
   logical cache layers (long static doc + tools + history) and want
   independent invalidation.

Without either, nothing is cached. There is no implicit prefix caching
on the Anthropic Messages API (unlike OpenAI).

## Mechanics

### Cache key

The cache key is `(model, prefix bytes up to the breakpoint)`. Any byte
change before or at the breakpoint invalidates the cache.

### Breakpoint placement

`cache_control` can be applied to:

- `system` blocks (top-level `system` is an array of content blocks)
- `tools` (any tool object, marks the cumulative tool list)
- `messages[*].content[*]` blocks (text, image, tool_use, tool_result)

The cache hierarchy is always: system → tools → messages, in that order.
A breakpoint in `messages` caches everything in system and tools up to
and including that point.

### Breakpoint limit

**4 `cache_control` markers per request.** Hard limit. Returns 400 if
exceeded. With automatic caching enabled, the auto breakpoint consumes
one of the 4 slots.

### The 20-block lookback window

Prefix matching looks back **~20 content blocks** from your cache
checkpoint. Put the breakpoint at the END of static content; anything
relevant more than ~20 blocks before the marker may fall outside the
lookup window. (Same rule on Bedrock.)

### TTL

- **5 minutes** (default ephemeral). Refreshed on every cache hit.
- **1 hour** (GA via beta header). Requires:
  - Header: `anthropic-beta: extended-cache-ttl-2025-04-11`
  - Block: `cache_control: {"type": "ephemeral", "ttl": "1h"}`

Both TTLs are sliding: each read resets the timer. A cache entry's
lifetime is measured from the START of the request that writes or
reads it.

### Mixed-TTL edge cases (2026-08 verified)

- Automatic + explicit breakpoint with the SAME TTL on the last block
  → automatic marker is a no-op.
- Different TTLs on the same last block → **400 error**.
- 4 explicit breakpoints already present + automatic enabled → **400
  error** (no slot left for the auto marker).
- Automatic caching is NOT available on the legacy Amazon Bedrock
  (Opus 4.6-and-earlier) integration — top-level `cache_control`
  there returns 400.

## Pricing

| Operation | Multiplier (vs base input price) |
|-----------|----------------------------------|
| Cache write (5min TTL) | 1.25x |
| Cache write (1h TTL) | 2.0x |
| Cache read / refresh | 0.1x |
| Uncached input | 1.0x |
| Output | base output price (unchanged) |

Break-even on a 5min cache: a written block pays for itself after roughly
2 reads. Above ~3 reads it's strictly cheaper than not caching.

For 1h: roughly 4 reads to break even.

### Actual prices (current Claude family, USD per MTok)

| Model | Base input | 5m write | 1h write | Cache hit |
|-------|-----------|----------|----------|-----------|
| Fable 5 | $10.00 | $12.50 | $20.00 | $1.00 |
| Mythos 5 | $10.00 | $12.50 | $20.00 | $1.00 |
| Opus 5 | $5.00 | $6.25 | $10.00 | $0.50 |
| Opus 4.8/4.7/4.6/4.5 | $5.00 | $6.25 | $10.00 | $0.50 |
| Sonnet 5 | $2.00 | $2.50 | $4.00 | $0.20 |
| Sonnet 4.6 & 4.5 | $3.00 | $3.75 | $6.00 | $0.30 |
| Haiku 4.5 | $1.00 | $1.25 | $2.00 | $0.10 |

Opus 4.1/4 and Sonnet 4 are retired (except Bedrock / Google Cloud).
Multipliers stack with Batch API and data-residency modifiers.

(Verified against Anthropic pricing 2026-08-28. Older Sonnet/Haiku
not listed but follow the same 1.25x/2.0x/0.1x ratios.)

### Minimum cacheable length (per model, 2026-08 verified)

512 tokens (Opus 5, Fable 5, Mythos 5) · 1,024 (Opus 4.8, Sonnet 5/4.6/4.5)
· 2,048 (Mythos Preview, Opus 4.7) · 4,096 (Opus 4.6/4.5, Haiku 4.5).
Shorter prompts are silently NOT cached — no error is returned.

## Request shape

```jsonc
{
  "model": "claude-3-7-sonnet-20250219",
  "system": [
    { "type": "text", "text": "You are an agent...", "cache_control": {"type": "ephemeral"} }
  ],
  "tools": [
    { "name": "read_file", "description": "...", "input_schema": {...} },
    { "name": "write_file", "description": "...", "input_schema": {...},
      "cache_control": {"type": "ephemeral"} }
  ],
  "messages": [
    { "role": "user", "content": [
      { "type": "text", "text": "<long static context block>",
        "cache_control": {"type": "ephemeral"} }
    ]},
    { "role": "assistant", "content": "..." },
    { "role": "user", "content": "what's next" }
  ]
}
```

This example uses 3 of the 4 breakpoints. The fourth is reserved for
the most recent stable turn boundary.

## Response shape

```jsonc
"usage": {
  "input_tokens": 23,
  "cache_creation_input_tokens": 0,
  "cache_read_input_tokens": 11890,
  "cache_creation": {
    "ephemeral_5m_input_tokens": 0,
    "ephemeral_1h_input_tokens": 0
  },
  "output_tokens": 412
}
```

`cache_creation_input_tokens` equals the SUM of the two
`cache_creation` sub-fields. Use the sub-fields to attribute write
premium by TTL tier.

### Cache diagnostics (beta)

Anthropic offers a beta that compares consecutive requests and reports
exactly where the prompt prefix diverged — the fastest way to find
what's thrashing your cache. Beta header string not confirmed in
fetched docs (UNVERIFIED); check the current prompt-caching page.

### Interactions that invalidate the cache (2026-08 verified)

- `tool_choice` changes → invalidate.
- Image presence changes → invalidate.
- **Context editing** (`context-management-2025-06-27` beta):
  tool-result clearing invalidates prefixes at the cleared point (and
  re-writes cost cache-write premium); thinking-block clearing
  invalidates at the cleared point, but keeping thinking blocks
  preserves the cache.
- The memory tool (`memory_20250818`) makes no documented
  caching-interaction guarantees — treat as neutral, verify on wire.

See [`../verification.md`](../verification.md) for how to interpret.

## Streaming

Final SSE event is `message_delta` with `usage` populated. Earlier
events have placeholder usage values.

## Common patterns

### Agent loop (the 99% case)

4 breakpoints, placed at:

1. End of system prompt
2. End of tools array
3. End of the last assistant turn (the stable conversation prefix)
4. End of the current user turn (cache for retries within 5min)

### Long-document chat

2 breakpoints:

1. End of the document block (in messages[0])
2. End of the last assistant turn

### RAG with stable retrieved context

3 breakpoints:

1. End of system prompt
2. End of retrieved-context block
3. End of last assistant turn

## What does NOT cache

- The output tokens (you always pay output rate).
- Anything after your last breakpoint.
- Across model versions (e.g., switching `claude-3-7-sonnet` to
  `claude-sonnet-4` invalidates).
- Across accounts/orgs.

## SDK notes

- Python SDK (`anthropic`): `cache_control` is a normal dict field on
  any content block. No special wrapper.
- TypeScript SDK: same.
- Bedrock: see [`bedrock.md`](bedrock.md) — different field name.
- Vertex: see [`vertex.md`](vertex.md).

## Worked example: a production agent shim

The pattern below is from a production proxy (`claude_byok.py`) that
fronts Anthropic OAuth-token inference for an agent CLI. It's been
running steady-state for months and hits ~85-90% cache reads on typical
loops. It uses 3 of the 4 breakpoints (the fourth is intentionally
reserved for future use).

### Required beta header

OAuth-bearer inference needs `oauth-2025-04-20`. Add the caching beta
alongside it:

```
anthropic-beta: oauth-2025-04-20,fine-grained-tool-streaming-2025-05-14,interleaved-thinking-2025-05-14,prompt-caching-2024-07-31
```

(`prompt-caching-2024-07-31` is no longer strictly required on current
Anthropic; the beta graduated. Sending it is a harmless no-op for
backward compatibility.)

### Breakpoint 1 — last system block

System prompt is built as an array of text blocks (preamble + the
user's actual system prompt). Tag the LAST one:

```python
blocks = [
    {"type": "text", "text": CLAUDE_CODE_SYSTEM_PREAMBLE},
    {"type": "text", "text": devin_system_prompt},
]
blocks[-1] = {**blocks[-1], "cache_control": {"type": "ephemeral"}}
```

### Breakpoint 2 — last tool

Tools are an array; mark the last:

```python
out[-1] = {**out[-1], "cache_control": {"type": "ephemeral"}}
```

Anthropic caches the ENTIRE tools array up through the marker, so one
breakpoint on the last tool = whole tools array cached.

### Breakpoint 3 — last block of last message

After building the messages array, find the last message, get its last
content block, and tag it:

```python
last = sanitized[-1]
content = last.get("content")
if isinstance(content, list) and content:
    tail = content[-1]
    if isinstance(tail, dict) and "cache_control" not in tail:
        content[-1] = {**tail, "cache_control": {"type": "ephemeral"}}
```

This caches the whole conversation history. On the next turn, the new
user message is uncached (small) but everything before it is a cache read.

### Why not all 4 breakpoints?

The 4th is reserved for cases where you want a "split" between long
static context (e.g., a giant pasted file) and conversation history.
For pure agent loops without long static blocks, 3 is the sweet spot —
extra breakpoints have no upside and cost a few extra bytes per request.

### Sanitize empty content blocks BEFORE tagging

Anthropic rejects empty text blocks with "content blocks must be
non-empty". If you build messages by translating from another format
(e.g., OpenAI), you can end up with empty blocks. Strip those FIRST,
then add `cache_control` to whatever is genuinely the last block.

### Measured behavior

Response usage on a steady-state turn:

```jsonc
"usage": {
  "input_tokens": 23,
  "cache_creation_input_tokens": 0,
  "cache_read_input_tokens": 11890,
  "output_tokens": 412
}
```

Hit rate = 11890 / (23 + 0 + 11890) = 99.8%.

On the very first turn after a cold start (or after >5min idle), the
shape inverts: `cache_creation_input_tokens > 0`, `cache_read = 0`. This
is the 1.25x write premium being paid; it's expected and pays for itself
on turn 2.

## References

- https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- https://www.anthropic.com/news/prompt-caching (announcement)
- Context editing: https://platform.claude.com/docs/en/build-with-claude/context-editing

---

_Last verified against Anthropic docs: 2026-08-28 (research lane,
23-source cited ledger). Pricing multipliers (1.25x/2x write, 0.1x
read), the 4-breakpoint limit, automatic top-level `cache_control`,
the 20-block lookback, and mixed-TTL 400 edge cases are verified
against the live docs._
