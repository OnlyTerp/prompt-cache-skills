# OpenAI prompt caching

> Verified against the official OpenAI prompt-caching and compaction
> documentation on 2026-07-10.

## Two caching generations

Do not treat all OpenAI models as having the same cache behavior.

### Models before GPT-5.6

- Prefix caching is automatic.
- Keep the prompt prefix byte-stable.
- `prompt_cache_key` improves routing locality on the Responses API.
- Cache writes have no separate write fee.
- `prompt_cache_retention` controls maximum retention on supported models.

### GPT-5.6 and later families

- `prompt_cache_key` is required for the more reliable implicit and explicit
  matching path.
- Cache writes cost **1.25x** the uncached input-token rate.
- Cache reads are reported in `cached_tokens`.
- Cache writes are reported in `cache_write_tokens`.
- `prompt_cache_options.ttl` has one supported value: `30m`.
- Explicit breakpoints are supported on Responses and Chat Completions content
  blocks.

This changes the optimization target. On GPT-5.6+, speculative cache writes can
cost more than leaving a one-shot prefix uncached.

## Stable prompt cache keys

Use a deterministic key based on stable routing dimensions:

```python
def prompt_cache_key(
    *,
    app: str,
    model: str,
    instructions: str,
    role: str,
    shard: int,
) -> str:
    digest = hashlib.sha256(instructions.encode("utf-8")).hexdigest()[:16]
    return f"{app}:{model}:{digest}:{role}:s{shard}"
```

Rules:

1. Always include the upstream model.
2. Keep orchestrator and worker traffic in different partitions.
3. Map workers to a small, deterministic shard set.
4. Never use a per-request UUID.
5. Do not let caller-provided headers overwrite the normalized role/shard.

OpenAI recommends keeping total traffic for each key near 15 requests per
minute. Above that, partition across more keys with a stable mapping.

## GPT-5.6 breakpoint mechanics

Set a request-wide policy:

```json
{
  "prompt_cache_key": "my-agent:gpt-5.6:abc123:worker:s2",
  "prompt_cache_options": {
    "mode": "explicit",
    "ttl": "30m"
  }
}
```

Add a breakpoint to a supported content block:

```json
{
  "type": "input_text",
  "text": "stable reusable content",
  "prompt_cache_breakpoint": {
    "mode": "explicit"
  }
}
```

Modes:

- `explicit`: only explicit breakpoints are read/written.
- `implicit`: OpenAI adds a breakpoint at the latest message and also uses
  explicit breakpoints.

Each request can create up to four new writes. In implicit mode, the automatic
latest-message write uses one slot.

## Cost-aware agent-loop strategy

A practical agent loop should distinguish one-shot tasks from continuations:

1. **First turn:** use `mode: explicit` with one stable root breakpoint after
   instructions/tool definitions.
2. **Continuation turn:** switch to `mode: implicit` only after prior assistant
   or tool output proves the conversation is being reused.
3. Keep the first root breakpoint stable.
4. Preserve append-only history after a breakpoint.

This avoids paying for a unique rolling-history write on every one-shot worker,
while long-running workers still cache their growing transcript.

This adaptive strategy is a harness pattern, not an OpenAI requirement. Verify
its economics on the target workload.

## Prefix stability

Cache matching remains exact-prefix matching. Stabilize:

- model id;
- instructions;
- tool schema contents and order;
- role markers;
- early messages;
- request transformations before each breakpoint.

Move volatile content after the stable root:

- timestamps;
- user/session personalization;
- task-specific instructions;
- random request ids;
- transient status text.

Canonicalize tool schemas once, then freeze them for the agent's lifetime. Do
not prune or reorder the tool list differently on every turn.

## Cache usage fields

Responses API:

```json
{
  "usage": {
    "input_tokens": 10000,
    "output_tokens": 500,
    "input_tokens_details": {
      "cached_tokens": 8000,
      "cache_write_tokens": 1000
    }
  }
}
```

Chat Completions uses `prompt_tokens`, `completion_tokens`, and
`prompt_tokens_details`.

For OpenAI-shaped usage, cached tokens are already included in input/prompt
tokens:

```python
token_hit_rate = cached_tokens / max(1, input_tokens)
```

Do not add `cached_tokens` to `input_tokens` in the denominator.

Track:

- token hit ratio;
- request hit ratio;
- write tokens;
- read tokens;
- requests per cache key;
- approximate amortization:

```python
amortized_token_equivalent = cached_tokens - 1.25 * cache_write_tokens
```

This is directional telemetry, not a dollar invoice.

## Compatibility fallback

Some OpenAI-compatible or managed backends may accept `prompt_cache_key` but
reject newer GPT-5.6 fields.

Safe fallback:

1. Send the breakpoint request.
2. Retry once only when HTTP 400 identifies
   `prompt_cache_options`/`prompt_cache_breakpoint` as an unknown or unsupported
   parameter.
3. Strip only the new cache fields.
4. Disable the unsupported feature for that model/process.
5. Do not fallback on generic validation errors.

Never retry because a breakpoint was placed illegally. Fix the payload instead.

## Retry accounting

An empty response is not necessarily free. If any of these happened, do not
automatically regenerate:

- `response.created` or another generation-start event arrived;
- a response/output item arrived;
- usage reports non-zero input, output, cache-read, or cache-write tokens.

Retrying a usage-only empty response can consume two or three full generations
while appearing to be a harmless reliability feature.

Compatibility fallback is different: a pre-stream 400 for an unsupported field
can be retried once with the field removed.

## Compaction

OpenAI supports:

- server-side compaction through
  `context_management: [{"type": "compaction", "compact_threshold": N}]`;
- standalone `POST /responses/compact`.

The returned compaction item is opaque machine state. Preserve it byte-for-byte
and pass it into the next Responses request. For stateless input-array chaining,
append response output items, including compaction items. After a compaction
item exists, old items before the latest compaction item can be dropped.

Do not enable server compaction through a Chat Completions bridge that discards
unknown output items. The next turn would lose the state the compaction item was
supposed to carry.

See [context compaction](context-compaction.md) for pre-cache local compaction
and lossless artifact spooling.

## References

- <https://developers.openai.com/api/docs/guides/prompt-caching>
- <https://developers.openai.com/api/docs/guides/compaction>
- <https://developers.openai.com/api/docs/guides/deployment-checklist>
- <https://developers.openai.com/cookbook/examples/prompt_caching_201>
- <https://developers.openai.com/api/reference/resources/responses/methods/create/>

---

_Last verified: 2026-07-10._
