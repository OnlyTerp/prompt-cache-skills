# Google Gemini prompt caching

> Status: SCAFFOLD. Verify against
> https://ai.google.dev/gemini-api/docs/caching
> before citing.

## TL;DR

Gemini has **two** caching modes:

1. **Implicit caching** — automatic, free, on Gemini 2.5 series. No setup.
   Returns `cachedContentTokenCount` in `usageMetadata` when it engages.
2. **Explicit caching** — `cachedContents.create()` returns a named
   cache object you reference in subsequent requests. Has minimum sizes
   and an explicit TTL. Charged for storage duration.

Most use cases want implicit. Use explicit only when (a) you need
guaranteed cache hits across long gaps, or (b) you're on a model where
implicit isn't available.

## Implicit caching

### Model support

- Gemini 3.5 Flash: enabled by default
- Gemini 3 Pro Preview: enabled by default
- Gemini 2.5 Pro: enabled by default
- Gemini 2.5 Flash: enabled by default
- Older (1.x, 2.0) models: not supported

### Mechanics

Automatic. Google's infrastructure detects repeated prefixes and serves
them from a fast path. No API parameter to enable or disable.

### Minimums (verified 2026-05-27 against ai.google.dev docs)

| Model | Min tokens for implicit cache |
|-------|------------------------------|
| Gemini 3.5 Flash | 1024 |
| Gemini 3 Pro Preview | 4096 |
| Gemini 2.5 Flash | 1024 |
| Gemini 2.5 Pro | 4096 |

Below threshold, no caching, no API error, just no
`cachedContentTokenCount` in the response.

To increase the chance of an implicit cache hit, Google explicitly
recommends: (a) put large/common content at the start of the prompt,
(b) send requests with similar prefixes close together in time.

### Pricing

Implicit cache hits are **free** (no charge for the cached tokens).
You only pay for the uncached prefix and the output.

### Response shape

```jsonc
"usageMetadata": {
  "promptTokenCount": 38500,
  "cachedContentTokenCount": 32100,
  "candidatesTokenCount": 420,
  "totalTokenCount": 39020
}
```

## Explicit caching

### When to use

- You have a large static context (≥minimum size) you'll reuse many times.
- The reuse pattern has gaps >5min (implicit caches expire faster).
- You want predictable hit rates rather than best-effort.

### Mechanics

Two-step:

1. Create the cache:

   ```python
   cached = client.caches.create(
       model="models/gemini-2.5-pro",
       config={
           "contents": [...],
           "system_instruction": "...",
           "tools": [...],
           "ttl": "3600s",
           "display_name": "my-document-cache",
       }
   )
   # cached.name = "cachedContents/abc123"
   ```

2. Use the cache:

   ```python
   response = client.models.generate_content(
       model="models/gemini-2.5-pro",
       contents="What's section 3 about?",
       config={"cached_content": cached.name}
   )
   ```

### Minimums

Same as implicit caching minimums (see table above): 1024 tokens for
Flash variants, 4096 for Pro variants.

Below the minimum, `cachedContents.create()` returns a 400. Verify by
inspecting `cached.usage_metadata.total_token_count` after creation.

### TTL

Set explicitly via `ttl` (string like `"3600s"`) or `expire_time`
(absolute timestamp). Max TTL is 7 days; default is 1 hour.

You can update TTL via `caches.update()` without re-uploading the content.

### Pricing

- **Cached input tokens**: 0.25x the standard input price.
- **Storage**: per-hour-per-token charge while the cache exists.

The storage cost means an unused cache still costs money. Delete or set
short TTL on caches you don't expect to reuse.

### Response shape

Same as implicit: `usageMetadata.cachedContentTokenCount`.

## What does NOT cache

- Sub-minimum prefixes.
- Across projects/orgs.
- Cross-model (each model has its own cache space).
- Content modifications after cache creation (caches are immutable; to
  update content, create a new cache).

## SDK notes

- Python: `google.genai` SDK has `client.caches` namespace.
- Node.js: `@google/genai` has `ai.caches`.
- REST: `POST /v1beta/cachedContents` to create.

## Gotchas specific to Gemini

### System instruction is part of the cache

If you change `system_instruction` between cache creation and use, you
get an error (or silent miss, depending on SDK version). System
instruction is locked in at creation time.

### Tools are part of the cache

Same as system_instruction. Tool definitions baked in at creation.

### File API uploads

For caching large files (PDFs, video, etc.), upload via the Files API
first, then reference in `contents`. The file bytes are what get
cached, not the file reference.

## References

- https://ai.google.dev/gemini-api/docs/caching
- https://cloud.google.com/vertex-ai/generative-ai/docs/context-cache/context-cache-overview (Vertex variant)
- https://ai.google.dev/gemini-api/docs/caching?lang=python

---

_Last verified against Gemini docs: 2026-05-27. Min token counts for
3.5/3.0/2.5 Pro/Flash families verified against ai.google.dev/gemini-api/docs/caching.
Default explicit-cache TTL is 1 hour. Implicit caching has "no cost
saving guarantee" per Google — pricing benefit is best-effort._
