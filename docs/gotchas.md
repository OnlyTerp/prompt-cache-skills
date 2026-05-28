# Gotchas

The non-obvious failure modes. Most "I turned on caching and nothing
happened" tickets resolve to one of these.

## Anthropic

### 1. Putting `cache_control` on volatile content

The cache key is the **content of the block plus everything before it**.
If you put a breakpoint on the last user message, and the last user message
changes every turn (which it does, by definition), you pay the 1.25x write
premium every single turn for zero reads. This is strictly worse than not
caching at all.

Correct placement, in order of stability:

1. System prompt (rarely changes)
2. Tool definitions (rarely change)
3. Long static context (docs, file dumps, examples) — early in messages
4. The *previous* assistant turn (stable once the turn is over)
5. Optionally: the current turn, if you expect a retry/continuation
   within 5 minutes

### 2. The 4-breakpoint limit

You get 4 `cache_control` markers per request, total, across system +
tools + messages. Each one marks "everything up to and including this
block." More breakpoints = finer-grained cache reuse but also more
overhead. The optimal layout for an agent loop is usually:

- 1 on system prompt
- 1 on tool definitions
- 1 on the last stable assistant turn
- 1 reserved (or on a long static context block, if present)

### 3. Forgetting the beta header for 1-hour TTL

Default TTL is 5 minutes. For 1-hour, you need:

```
anthropic-beta: extended-cache-ttl-2025-04-11
```

AND `cache_control: {"type": "ephemeral", "ttl": "1h"}`. Forgetting the
header silently downgrades to 5 minutes. Forgetting the `ttl` field with
the header set is a no-op.

The 1h cache costs 2x to write (vs 1.25x for 5min) and reads the same.
Worth it if your agent loop has gaps >5min (e.g., human-in-the-loop).

### 4. Tool-result placement

If you cache the assistant turn that contains a `tool_use` block, the
*next* turn's `tool_result` is what's hitting the cache, not the
`tool_use` itself. Get the boundary right or you cache one turn too
early/late.

### 5. Byte-identity of tool definitions

Reordering tools, reformatting JSON Schema, or even changing whitespace
in tool definitions invalidates the tools cache. If your harness
serializes tools differently between turns (e.g., dict iteration order
in older Python), you cache-miss every turn and never know why.

### 6. `cache_creation_input_tokens` vs `cache_read_input_tokens`

Response `usage` has both. To know if caching is working:

- `cache_creation_input_tokens > 0`: you paid the 1.25x write premium
  on N tokens
- `cache_read_input_tokens > 0`: you got the 0.1x read discount on N
  tokens

Hit rate = `cache_read / (cache_read + cache_creation + input_tokens)`.
On a steady-state agent loop you want this >0.8.

## OpenAI

### 7. Caching is automatic but byte-identical-prefix-only

There is no `cache_control`. You don't opt in. But:

- Prefix must be ≥1024 tokens.
- Prefix must be byte-identical across calls (same model, same
  org-scoped routing).
- Any change to the system prompt, tool definitions, or earliest message
  invalidates everything after it.

If your harness injects the current timestamp into the system prompt
("Today's date is 2026-05-27"), congratulations: you have a cache that
expires daily.

### 8. The cached_tokens field is on a different path

```python
response.usage.prompt_tokens_details.cached_tokens
```

Not `response.usage.cached_tokens`. Easy to miss; many "we don't get
cache hits" reports were just reading the wrong field.

### 9. No write premium, but also no API control

You can't extend TTL, can't mark specific blocks, can't choose a
breakpoint. If the prefix structure isn't stable, you're stuck.

## Gemini

### 10. Implicit vs explicit are different APIs

Implicit caching is free, automatic, on Gemini 2.5 series, no setup
required, returns `usage_metadata.cached_content_token_count`.

Explicit caching uses `cachedContents.create()` returning a
`cachedContent.name` you pass in subsequent requests. Has minimum sizes
(varies by model — 32k for 2.5 Pro, 4096 for 2.5 Flash as of writing).

You probably want implicit unless you have a specific reason.

### 11. Minimum-size cliff

Below the minimum, explicit caching silently doesn't engage. Verify with
`cachedContentTokenCount` in the response, not by trusting the SDK call
succeeding.

## Bedrock

### 12. `cachePoint` not `cache_control`

Anthropic-via-Bedrock uses a different field name and slightly different
shape than direct Anthropic. Harnesses that hardcode `cache_control` for
the Anthropic SDK and route through Bedrock will silently not cache.

### 13. Model availability

Not all models on Bedrock support cache points. Verify against the
current AWS support matrix; this drifts.

## All providers

### 14. Streaming responses still report usage

The final SSE event in a streamed completion includes the full `usage`
block. Don't assume "we stream, so we can't measure cache hits." You can.

### 15. Retry storms invalidate caches

If your harness retries failed calls by re-sending the same request with
a slightly different body (e.g., bumped `max_tokens`, added a request ID
in metadata), you may be cache-missing on retries when you think you're
hitting.

### 16. Multi-account / multi-org routing

OpenAI prefix caching is org-scoped. Running the same prompt across two
org IDs (e.g., personal + work) caches separately. Anthropic is
account-scoped similarly.
