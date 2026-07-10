---
name: openai-gpt56-agent-loop-cache
description: Add cost-aware GPT-5.6 prompt-cache breakpoints, stable partitions, retry guards, and cache-write telemetry to a Responses agent loop.
target_harness: custom OpenAI Responses API agent harness
target_repo: any
target_files:
  - Responses request builder
  - agent history manager
  - streamed usage parser
target_commit: pattern skill; inspect the current harness before applying
estimated_savings: workload-dependent; avoids speculative 1.25x cache writes and improves reusable-prefix hits
---

# Build a cost-aware GPT-5.6 agent cache loop

## Target

Apply this skill to an agent harness that:

- calls OpenAI Responses with GPT-5.6 or a later family;
- maintains multi-turn tool history;
- controls `prompt_cache_key`;
- can preserve exact input-item ordering.

Do not apply it blindly to an OpenAI-compatible proxy. Confirm the upstream
accepts `prompt_cache_options` and content-block
`prompt_cache_breakpoint`.

## Symptom

One or more of these is true:

- every request uses a random cache key;
- all workers share one overloaded cache key;
- implicit caching writes every one-shot worker's unique task/history;
- tool definitions change order between turns;
- usage logs ignore `cache_write_tokens`;
- an empty-turn retry runs again after provider usage was already reported;
- a broad HTTP 400 fallback hides malformed breakpoint placement.

On GPT-5.6+, cache writes cost 1.25x uncached input. A poor cache plan can cost
more than no caching.

## Fix

### 1. Derive a stable, partitioned key

```python
def cache_key(model: str, instructions: str, role: str, shard: int) -> str:
    digest = hashlib.sha256(instructions.encode("utf-8")).hexdigest()[:16]
    return f"agent:{model}:{digest}:{role}:s{shard}"
```

- Include the upstream model.
- Normalize role to `orchestrator`, `worker`, or `direct`.
- Map workers deterministically across enough shards to keep each key near
  15 requests/minute.
- Set the same stable value in any backend cache-scope header used by the
  harness.

### 2. Add one stable root breakpoint

Place the breakpoint after stable instructions/tool definitions and before the
task-specific content:

```json
{
  "type": "input_text",
  "text": "<stable-root-boundary>",
  "prompt_cache_breakpoint": {
    "mode": "explicit"
  }
}
```

Use an existing stable content block when the harness exposes one. If a marker
is required, keep it short and constant.

### 3. Make the mode continuation-aware

```python
mode = "implicit" if has_prior_assistant_or_tool_output else "explicit"

request["prompt_cache_options"] = {
    "mode": mode,
    "ttl": "30m",
}
```

- First turn: root-only explicit write.
- Continued turn: explicit root plus implicit latest-message breakpoint.

This avoids a speculative rolling write for a worker that never receives a
second turn.

### 4. Freeze cache-sensitive prefixes

- Canonicalize and freeze tool definitions.
- Keep instructions byte-identical.
- Put timestamps/session personalization after the stable root.
- Compact tool output before its first cache write.
- Never rewrite already-sent compacted history.

### 5. Add a narrow compatibility fallback

Retry once without GPT-5.6 cache fields only when HTTP 400 identifies
`prompt_cache_options` or `prompt_cache_breakpoint` as an unknown/unsupported
parameter.

Do not fallback on generic `invalid_request_error`, illegal placement, auth,
quota, or transport failures.

### 6. Prevent paid empty-turn retries

Do not automatically regenerate after:

- a generation-start event;
- any output item;
- non-zero input/output/cache-read/cache-write usage.

A pre-stream unsupported-parameter fallback is allowed once.

### 7. Parse cache economics

Read:

```python
details = usage.get("input_tokens_details") or {}
cached = int(details.get("cached_tokens") or 0)
written = int(details.get("cache_write_tokens") or 0)
```

Track per model/role/shard:

- input tokens;
- cached tokens;
- cache-write tokens;
- token hit ratio;
- request hit ratio;
- request rate per key.

## Verify

### Offline invariants

1. Same model/instructions/role/shard produces the same key.
2. Orchestrator and worker keys differ.
3. Worker shard mapping is deterministic and bounded.
4. First-turn request uses `mode: explicit`.
5. Continuation request uses `mode: implicit`.
6. Exactly one root breakpoint is attached.
7. GPT-5.5 receives none of the GPT-5.6 fields.
8. Usage-only empty output is not retried.
9. Unsupported-field 400 retries once; unrelated 400 does not.
10. Tool schemas and old history remain byte-identical across repeated builds.

### Wire verification

Capture at least:

1. one first worker turn;
2. two continuation turns with the same cache key;
3. one different worker in the same shard;
4. one worker in another shard.

Confirm:

```text
warm.cached_tokens > 0
cache_write_tokens is logged
continuation cache reads amortize prior writes
requests/key stays near the intended rate
```

Do not claim savings until the live usage fields confirm them.

## Background

- [OpenAI prompt caching](../../docs/concepts/openai.md)
- [Context compaction before caching](../../docs/concepts/context-compaction.md)
- [Gotchas 17-24](../../docs/gotchas.md#17-gpt-56-cache-writes-are-not-free)
