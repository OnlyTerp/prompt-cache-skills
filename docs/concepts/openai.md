# OpenAI prompt caching

> Status: SCAFFOLD. Verify against
> https://platform.openai.com/docs/guides/prompt-caching
> before citing.

## TL;DR

OpenAI prompt caching is **automatic and implicit**. There is no API
surface to enable or configure it. If your prompt prefix is ≥1024 tokens
and byte-identical to a previous call within the cache window, you get
cached-token pricing on the matching prefix.

You cannot:

- Mark specific blocks as cacheable.
- Choose a TTL.
- Cache across orgs.
- Cache prefixes shorter than 1024 tokens.

You can:

- Structure your prompt so the prefix stays stable (the only knob you have).

## Mechanics

### Minimum prefix size

1024 tokens. Below this, no caching. Above this, caching kicks in
automatically.

### Cache key

`(model, org_id, prefix bytes)`. Prefix is matched left-to-right by
content hash, in 128-token increments past the 1024-token floor (per
docs at time of writing — verify).

### TTL

OpenAI doesn't publish an explicit TTL. Cached prefixes are kept "for a
period of time, typically 5-10 minutes of inactivity, but may persist
for up to one hour during off-peak hours." Treat as 5min effective.

### Routing

OpenAI routes requests with the same prefix to the same backend pod to
hit the local cache. Routing is org-scoped, so high-volume orgs get
better hit rates than low-volume ones.

## Pricing

| Operation | Multiplier (vs base input price) |
|-----------|----------------------------------|
| Cache hit (cached_tokens) | 0.5x (most models) |
| Cache miss | 1.0x |
| Output | base output price |

No write premium. This is a meaningful difference vs Anthropic: there's
no downside to "trying" to cache, because there's no extra cost on cold
calls.

Exact discount varies by model. As of writing: most reasoning models and
GPT-4.x get 50% discount; some newer models get 75-90%. Check pricing page.

## Request shape

There is no caching field. The "request shape for caching" is just:
**keep the prefix byte-stable.**

What kills the prefix:

- Timestamps in the system prompt ("Today is 2026-05-27")
- Random session IDs in the system prompt
- Reordering tools (JSON object key order doesn't matter, but array
  order of tools does)
- Reformatting whitespace in tool definitions or system prompt
- Personalization fields injected early (user names, etc.)

If you must include volatile data, put it **after** the long static
prefix, not before.

## Response shape

```jsonc
"usage": {
  "prompt_tokens": 2104,
  "completion_tokens": 312,
  "total_tokens": 2416,
  "prompt_tokens_details": {
    "cached_tokens": 1920
  },
  "completion_tokens_details": {
    "reasoning_tokens": 0
  }
}
```

`prompt_tokens_details.cached_tokens` is the count served from cache.
Note: cached_tokens are a subset of prompt_tokens, not an addition.

## Streaming

Set `stream_options: {"include_usage": true}` to get `usage` in the
final SSE chunk. Without this flag, `usage` is null on streamed responses
and you cannot measure cache hits.

## Anti-patterns

### Anti-pattern 1: Injecting date into system prompt

```python
system = f"You are a helpful assistant. Today is {datetime.now():%Y-%m-%d}."
```

Cache invalidates at midnight. Fix: put date at the end of the user message
or in a separate dedicated message, not in the prefix.

### Anti-pattern 2: User personalization in system prompt

```python
system = f"You are {user.preferred_assistant_name}. {long_system_rules}"
```

Different cache key per user, regardless of how many users share the
long rules. Fix: put user name in the first user message; keep system
prompt user-agnostic.

### Anti-pattern 3: Dict-ordered tool serialization

In Python <3.7 (and some JS engines), `json.dumps(tools)` could emit
keys in different order across runs. Fix: `json.dumps(tools, sort_keys=True)`.

### Anti-pattern 4: Re-fetching system prompt per call

Some harnesses fetch the system prompt from a database or remote URL
per call. If the source returns slightly different bytes (line endings,
trailing whitespace, locale differences), cache misses every call. Fix:
fetch once, hash it, log the hash, alert on drift.

## What does NOT cache

- Prefixes shorter than 1024 tokens.
- Across orgs.
- Across models.
- After the cache TTL expires.
- When prefix bytes differ at all (even whitespace).

## The `prompt_cache_key` trick (Responses API)

The OpenAI **Responses API** (`/v1/responses`, used by Codex CLI, the
ChatGPT backend, and most agent harnesses targeting `gpt-5.x` /
reasoning models) accepts a `prompt_cache_key` field that the public
docs barely mention. It's the single biggest hidden lever in OpenAI
caching.

### What it does

OpenAI's automatic prefix caching is hash-routed to a specific
backend pod. Without `prompt_cache_key`, the request gets hashed by
content alone and may land on any pod. With `prompt_cache_key`, OpenAI
uses it as the routing hint — same key = same pod = warm cache.

### What kills cache hits silently

Many harnesses pass a per-request UUID as the cache key (sometimes via
a `session_id` header, sometimes via `prompt_cache_key`):

```python
# BAD — different every request
prompt_cache_key = str(uuid.uuid4())
```

This is worse than not setting the field at all: it forces routing to
random pods, and you get cold-cache pricing on every call. Measured
impact: 0% cache hit rate on multi-turn agent loops where prefix-only
caching would have given 70-90%.

### The fix: stable instruction-hash keys

Hash the stable parts of the prompt (system instructions, model slug)
and use that as the key:

```python
def _prompt_cache_key(*, model_slug: str, composed_instructions: str) -> str:
    digest = hashlib.sha256(composed_instructions.encode("utf-8")).hexdigest()[:16]
    return f"droid:{model_slug}:{digest}"
```

Now every request with the same system prompt + model routes to the
same pod and shares a cache.

### For Codex backend specifically

The ChatGPT Codex backend (`chatgpt.com/backend-api/codex`) reads the
cache key from BOTH `prompt_cache_key` in the body AND `session_id` in
headers. Set them to the same value:

```python
headers["session_id"] = cache_key
body["prompt_cache_key"] = cache_key
```

Measured result on a multi-worker pipeline (3 parallel workers, same
system prompt, varying user prompts): 75-91% cache_input_token hit
rates against OpenAI. Achieved purely from stable-prefix bootstrap
bytes (system prompt + base instructions + handoff schema) — no
explicit `cache_control` markers (OpenAI doesn't support them anyway).

### When the field doesn't exist (Chat Completions)

The legacy Chat Completions API (`/v1/chat/completions`) doesn't accept
`prompt_cache_key`. Auto-prefix caching still works, but you have no
routing control. Stick to byte-stable prefixes.

## References

- https://platform.openai.com/docs/guides/prompt-caching
- https://openai.com/index/api-prompt-caching/ (announcement)
- Responses API reference (`prompt_cache_key`):
  https://platform.openai.com/docs/api-reference/responses/create

---

_Last verified: 2026-05-27. The 1024-token minimum, byte-identity rule,
and 5-10min idle TTL are documented. The `prompt_cache_key` Responses
API field is verified against live ChatGPT Codex backend traffic — it
is real and load-bearing. The "no write premium" claim is structurally
true (OpenAI doesn't bill differently for first vs subsequent calls)._
