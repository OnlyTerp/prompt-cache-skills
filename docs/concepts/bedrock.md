# AWS Bedrock prompt caching

> Status: SCAFFOLD. Verify against
> https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html

## TL;DR

Bedrock supports prompt caching as a pass-through of the underlying
model provider's caching, with a Bedrock-specific request shape. As of
writing this primarily means Anthropic models (Claude 3.5+, Claude 3.7,
Claude 4.x families) — Bedrock's wrapper translates `cachePoint` fields
into Anthropic's caching at the boundary.

The key difference vs direct Anthropic: **field name is `cachePoint`,
not `cache_control`.** Harnesses that hardcode `cache_control` and
route through Bedrock silently do not cache.

## Mechanics

### Request shape (Converse API)

```jsonc
{
  "modelId": "anthropic.claude-3-7-sonnet-20250219-v1:0",
  "system": [
    { "text": "You are an agent..." },
    { "cachePoint": { "type": "default" } }
  ],
  "messages": [...],
  "toolConfig": {
    "tools": [
      { "toolSpec": {...} },
      { "cachePoint": { "type": "default" } }
    ]
  }
}
```

`cachePoint` is a sibling content block, not an attribute on a text
block (unlike direct Anthropic). It marks the prefix-up-to-here for
caching.

### InvokeModel API (raw passthrough)

If you use `InvokeModel` with the raw Anthropic body, you can use
`cache_control` as on the direct Anthropic API. The translation only
happens in the Converse API.

### Breakpoint limits

Same as direct Anthropic: 4 breakpoints per request.

### TTL

5 minutes default. 1-hour extended TTL is being rolled out per region
and model; verify availability before assuming.

## Pricing

Inherits Anthropic's caching pricing (1.25x write, 0.1x read for 5min).
Add Bedrock's own per-region uplift on top of base model pricing — check
the Bedrock pricing page for current numbers per model and region.

## Response shape

Converse API returns cache token counts in the `usage` block of the
response:

```jsonc
"usage": {
  "inputTokens": 23,
  "outputTokens": 412,
  "totalTokens": 435,
  "cacheReadInputTokenCount": 11890,
  "cacheWriteInputTokenCount": 0
}
```

Note the camelCase + `Count` suffix — different from direct Anthropic's
snake_case `cache_read_input_tokens`. Harnesses parsing the response
need to handle both shapes.

## Model support

Cache point support is model-specific on Bedrock. As of writing:

- claude-3-5-sonnet-20241022: supported
- claude-3-7-sonnet-20250219: supported
- claude-3-5-haiku: supported
- claude-3-opus: NOT supported (verify)
- Older Claude 3: NOT supported

Check `bedrock.list_foundation_models()` and inspect each model's
`responseStreamingSupported` / capability flags, or consult the AWS
support matrix.

## Anti-patterns specific to Bedrock

### Anti-pattern: assuming Anthropic SDK's field works

Bedrock's Converse API will silently accept `cache_control` (the field
just gets ignored as an unknown attribute) and return no cache hits.
There's no error to alert you.

### Anti-pattern: cross-region cache expectations

Caches are region-scoped. Routing requests across regions for failover
gives you a cold cache on the failover region.

## References

- https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html

---

_Last verified: 2026-05-28 (scaffold content; model support matrix
and 1h TTL regional availability need provider-side verification)._
