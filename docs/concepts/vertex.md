# Google Vertex AI prompt caching

> Status: SCAFFOLD.

## TL;DR

Vertex hosts both Gemini and (selected) Anthropic models. Caching
behavior depends on which model family:

- **Gemini-on-Vertex**: same as direct Gemini API (implicit + explicit
  `cachedContents`). Vertex calls this "Context Caching."
- **Anthropic-on-Vertex**: same as direct Anthropic Messages API
  (explicit `cache_control` on content blocks).

The wire format differs from the consumer APIs (Vertex uses GCP-style
URLs and IAM auth), but the caching field shapes are the same as the
non-Vertex equivalents.

## Gemini on Vertex

Vertex's Context Caching API: `cachedContents` resource under
`projects/<P>/locations/<L>/cachedContents/`.

### Request shape

```jsonc
POST https://us-central1-aiplatform.googleapis.com/v1/projects/PROJECT/locations/us-central1/cachedContents

{
  "model": "projects/PROJECT/locations/us-central1/publishers/google/models/gemini-2.5-pro",
  "contents": [...],
  "ttl": "3600s"
}
```

Use the returned `name` in subsequent `generateContent` calls under the
`cachedContent` field.

### Minimums

Same as consumer Gemini: 4096 tokens for Pro, 1024 for Flash. Verify.

### Pricing

Vertex pricing for cached input is the same multiplier (0.25x) as
consumer Gemini, but the per-region base pricing differs. Storage
charged per-hour-per-token.

### Implicit caching on Vertex

Available on Gemini 2.5 series on Vertex as well. Same response
metadata (`cachedContentTokenCount`).

## Anthropic on Vertex

Vertex hosts Claude models in select regions (us-east5, europe-west1,
asia-southeast1 as of writing — verify). The API is Anthropic's
Messages API mounted under a Vertex URL:

```
POST https://<region>-aiplatform.googleapis.com/v1/projects/<P>/locations/<region>/publishers/anthropic/models/<model>:rawPredict
```

Body is **identical to direct Anthropic Messages**, including
`cache_control: {"type": "ephemeral"}`. No translation layer (unlike
Bedrock's Converse API).

### Caching on Anthropic-on-Vertex

Works the same as direct Anthropic:

- `cache_control` on content blocks
- 4 breakpoint limit
- 5min default TTL
- 1h beta TTL via `anthropic-beta` header
- Response `usage.cache_read_input_tokens` / `cache_creation_input_tokens`

## Anti-patterns specific to Vertex

### Anti-pattern: region/project-scoped caches

Caches don't cross regions OR projects. A multi-region deployment
caches independently in each region.

### Anti-pattern: streaming endpoint vs raw predict

For Anthropic on Vertex, `rawPredict` is non-streaming and
`streamRawPredict` is streaming. They share caches but the response
parsing differs (SSE in streaming).

### Anti-pattern: assuming consumer Gemini SDK works unchanged

The `google.genai` consumer SDK can target Vertex with `vertexai=True`,
but the `caches` API surface has small differences (resource naming,
auth). Test before relying on shared code paths.

## References

- https://cloud.google.com/vertex-ai/generative-ai/docs/context-cache/context-cache-overview
- https://cloud.google.com/vertex-ai/generative-ai/docs/partner-models/use-claude

---

_Last verified: TODO_
