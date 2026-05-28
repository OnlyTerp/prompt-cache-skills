# Anthropic prompt caching

> Status: SCAFFOLD. Numbers here reflect Anthropic's documented behavior
> as of the last edit (see footer). Verify against
> https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
> before citing in an audit.

## TL;DR

Anthropic prompt caching is **explicit and opt-in**. You mark content
blocks with `cache_control: {"type": "ephemeral"}` and Anthropic caches
the prefix-up-to-and-including that block. On a subsequent request with
the same prefix bytes, you pay 0.1x input price on the cached tokens.

Without `cache_control`, nothing is cached. There is no automatic prefix
caching on the Anthropic Messages API.

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
exceeded.

### TTL

- **5 minutes** (default ephemeral). Refreshed on every cache hit.
- **1 hour** (beta). Requires:
  - Header: `anthropic-beta: extended-cache-ttl-2025-04-11`
  - Block: `cache_control: {"type": "ephemeral", "ttl": "1h"}`

Both TTLs are sliding: each read resets the timer.

## Pricing

| Operation | Multiplier (vs base input price) |
|-----------|----------------------------------|
| Cache write (5min TTL) | 1.25x |
| Cache write (1h TTL) | 2.0x |
| Cache read | 0.1x |
| Uncached input | 1.0x |
| Output | base output price (unchanged) |

Break-even on a 5min cache: a written block pays for itself after roughly
2 reads. Above ~3 reads it's strictly cheaper than not caching.

For 1h: roughly 4 reads to break even.

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
  "output_tokens": 412
}
```

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

## References

- https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- https://www.anthropic.com/news/prompt-caching (announcement)
- 1h beta: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching#1-hour-cache-duration-beta

---

_Last verified against Anthropic docs: TODO (executor agent: stamp this when you check)_
