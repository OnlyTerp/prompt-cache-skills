# Verification

How to confirm that prompt caching is actually working, rather than
hoping it is.

## The one rule

A harness "supports caching" if and only if, on the second identical
agent turn, the response `usage` object shows cached-token fields
greater than zero. Anything else — config flags set, `cache_control`
present in the request, maintainer claims, README boasts — is necessary
but not sufficient.

## Per-provider fields to check

### Anthropic

```jsonc
"usage": {
  "input_tokens": 23,                  // non-cached input
  "cache_creation_input_tokens": 1842, // wrote to cache this turn
  "cache_read_input_tokens": 0,        // read from cache this turn
  "output_tokens": 412
}
```

First turn after a cold start: `cache_creation > 0`, `cache_read = 0`.
Second turn (within 5min): `cache_creation = 0`, `cache_read > 0`.

If you see `cache_creation > 0` on every turn, your breakpoint is on
volatile content. Fix the placement.

### OpenAI

```jsonc
"usage": {
  "input_tokens": 10000,
  "output_tokens": 500,
  "input_tokens_details": {
    "cached_tokens": 8000,
    "cache_write_tokens": 1000
  }
}
```

`cached_tokens` is the count served from cache. GPT-5.6+
`cache_write_tokens` is the count written at the cache-write rate. Both are
subsets of input tokens:

```text
hit rate = cached_tokens / input_tokens
```

### Gemini

```jsonc
"usageMetadata": {
  "promptTokenCount": 38500,
  "cachedContentTokenCount": 32100,
  "candidatesTokenCount": 420
}
```

`cachedContentTokenCount` covers both implicit and explicit cache hits.

### Bedrock (Anthropic models)

Mirrors Anthropic's shape but inside the Bedrock response envelope. Look
for `cacheReadInputTokenCount` / `cacheWriteInputTokenCount` (note the
camelCase difference).

### Vertex AI

For Anthropic models on Vertex: identical to direct Anthropic.
For Gemini on Vertex: identical to Gemini direct.

## Methodology: how we audit a harness

We require captured evidence, not log scraping. Steps:

1. **Capture the wire.** Start mitmdump on a known port:

   ```bash
   mitmdump -p 8090 -w /tmp/harness-capture.flow
   ```

2. **Point the harness at the proxy.** Set `HTTPS_PROXY=http://127.0.0.1:8090`
   (or the harness's own provider-URL override) and configure it to trust
   the mitmproxy CA. For providers that pin certs, use the harness's
   provider-URL override if available.

3. **Run two identical turns.** A single prompt, then the same prompt
   again. The exact same conversation history if it's an agent loop.

4. **Extract the second-turn response.** From `mitmdump`, find the second
   call and dump its body:

   ```bash
   mitmproxy --rfile /tmp/harness-capture.flow
   # or programmatically extract via mitmproxy.io
   ```

5. **Check the `usage` block** as described above.

6. **Record the result** in the harness's audit file:
   - First-turn request body (relevant headers + `cache_control` fields)
   - First-turn response `usage`
   - Second-turn response `usage`
   - Hit rate computation
   - Commit SHA of the harness at capture time

## If a shim or gateway is in the path

A shim can make caching work, break it, or make a default install look
like it caches when only the shim is doing the work. Classify the request
path before grading the harness.

Check for obvious routing/config signals:

- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_CUSTOM_HEADERS`
- `ENABLE_PROMPT_CACHING_1H`
- `CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST`
- `HTTP_PROXY` / `HTTPS_PROXY`
- custom gateway, proxy, or enterprise-config logs

Then inspect whether the shim preserves or injects provider cache fields:

- Anthropic: `cache_control`, `cache_creation_input_tokens`,
  `cache_read_input_tokens`
- OpenAI Responses: `prompt_cache_key`,
  `prompt_cache_options`, content-block `prompt_cache_breakpoint`,
  `input_tokens_details.cached_tokens`,
  `input_tokens_details.cache_write_tokens`
- Gemini: `cachedContents`, `cachedContentTokenCount`

Non-zero cache counters prove caching in the observed request path. They
do **not** prove stock/default product behavior if a shim, gateway, or
environment override is active. Grade it as:

- **default verified** — clean stock app, no shim/config override, non-zero
  cache counters.
- **configured verified** — shim/gateway/env present and non-zero cache
  counters.
- **unverified** — no cache counters or request bodies, even if cache
  flags appear in config.

Also check for shim-induced regressions: volatile timestamps in the
cached prefix, rotating `prompt_cache_key`, dropped provider usage fields,
or request-shape conversion that loses `cache_control` / `cachedContents`.

## When the harness uses streaming SSE

The final event in an SSE stream from Anthropic is
`event: message_delta` with `usage` containing the cache fields. Don't
look at the `message_start` event — it has placeholder values.

For OpenAI Chat Completions streaming, set
`stream_options: {"include_usage": true}`. Native Responses streams report
usage in the completed response event.

## Anti-evidence

Things that DO NOT count as verification:

- The harness's own logs saying "cached prefix detected".
- A maintainer's comment in source saying `# enable caching here`.
- The presence of `cache_control` in the request body without a
  corresponding cache hit in a later response.
- A blog post.
- Reduced latency (real but not specific to caching — could be other
  factors).

## Reproducibility template

Each harness audit file ends with a `## Reproduction` section in this
shape:

```markdown
## Reproduction

- Harness: cline @ abc1234 (2026-05-27)
- Provider: Anthropic claude-3-7-sonnet-20250219
- Capture: see `examples/cline-2026-05-27.flow`
- Turn 1 usage: input=12104, cache_creation=11890, cache_read=0
- Turn 2 usage: input=18, cache_creation=0, cache_read=11890
- Hit rate (turn 2): 99.85%
- Verdict: working as intended
```

If you can't reproduce, the audit is `unverified`. No vibe-grading.
