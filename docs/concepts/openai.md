# OpenAI prompt caching

> Status: VERIFIED. Numbers reflect https://platform.openai.com/docs/guides/prompt-caching
> as of 2026-08-28 (fetched copy in the 2026-08 research ledger).

## TL;DR

OpenAI prompt caching has **two mechanisms** as of GPT-5.6:

1. **Automatic prefix caching** (always on): if your prompt prefix is
   ≥1024 tokens (GPT-5.6+) or ≥2048 (older models) and byte-identical
   to a recent call, you get cached-token pricing on the matching
   prefix. Implicit breakpoints are "spaced at regular, model-dependent
   intervals" of 48 tokens.
2. **Explicit breakpoints** (NEW, GPT-5.6 and later only): mark blocks
   with `prompt_cache_breakpoint` and control retention with
   `prompt_cache_options.ttl` (`30m` — the only supported value, and
   the default) or `prompt_cache_retention` (`in_memory` / `24h`).

You cannot:

- Cache across orgs (cache key includes org).
- Use explicit breakpoints on models older than GPT-5.6.

You can:

- Structure the prefix to stay byte-stable (still the highest-leverage knob).
- Route deterministically with `prompt_cache_key` (Chat Completions AND
  Responses API — it's no longer Responses-only).
- Set `prompt_cache_options.mode` to `implicit` (default: automatic
  breakpoint on latest message + explicit ones) or `explicit` (only
  explicit breakpoints used).

## Mechanics

### Minimum prefix size

1,024 tokens for GPT-5.6 and later; 2,048 for older models. Tokens in
OpenAI-provided hidden system content don't count toward the minimum.

### Cache key

`(model, org_id, prefix bytes)`. Prefix is matched left-to-right by
content hash, in 128-token increments past the minimum floor.

### TTL (2026 verified)

- **`prompt_cache_options.ttl`** (GPT-5.6+): only supported value is
  `30m`, also the default. "A cached prefix remains eligible for reuse
  for 30 minutes after its most recent write or reuse, though OpenAI
  may retain it longer."
- **`prompt_cache_retention`** (earlier models): `in_memory` ("typically
  remain active for around 5 to 10 minutes of inactivity, up to one
  hour") or `24h` ("typically keeps entries available for around 30
  minutes and can retain them for up to 24 hours"). ZDR orgs default
  to `in_memory`; others default to `24h`.

### Routing

OpenAI routes requests with the same prefix to the same backend pod to
hit the local cache. Routing is org-scoped, so high-volume orgs get
better hit rates than low-volume ones.

## Pricing

| Operation | GPT-5.6+ | Older models |
|-----------|----------|--------------|
| Cache hit (`cached_tokens`) | 0.1x | 0.5x (most models; some 0.25-0.75x) |
| Cache write | 1.25x (NEW — GPT-5.6+ bills a write premium) | none (no write charge) |
| Cache miss | 1.0x | 1.0x |
| Output | base output price | base output price |

**2026 change:** GPT-5.6 and later bill cache WRITES at 1.25x —
"Writing a prefix once and fully reusing it once costs 1.35× its
ordinary [input cost]." The old "no write premium" claim is now only
true for pre-5.6 models. Break-even on GPT-5.6 is ~2 reads of a
written prefix.

Price rows (per 1M, short context — input / cached / cache write /
output): gpt-5.6-sol $2.00/$0.20/$2.50/$10.00; gpt-5.6-terra
$1.00/$0.10/$1.25/$6.00; gpt-5.6-luna $0.10/$0.01/$0.125/$0.60.
Sol promotional pricing runs at least through November 21, 2026.

## Request shape (2026)

```jsonc
{
  "model": "gpt-5.6-sol",
  "prompt_cache_key": "shared-workflow-v1",
  "prompt_cache_options": { "mode": "implicit", "ttl": "30m" },
  "messages": [...]
}
```

`prompt_cache_key` now works on BOTH Chat Completions and Responses
API. Explicit breakpoint marker (GPT-5.6+, content blocks):

```jsonc
{ "type": "text", "text": "...",
  "prompt_cache_breakpoint": { "mode": "explicit" } }
```

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
explicit breakpoint markers (unnecessary with stable prefixes).

### When the field doesn't exist (pre-5.6 Chat Completions)

Very old models ignore `prompt_cache_key` on Chat Completions.
Auto-prefix caching still works, but you have no routing control.
Stick to byte-stable prefixes.

### Structured-outputs stability caveat

Documented on the current page: when the JSON schema changes between
requests, cached prefixes that embed the serialized schema (or
tool-selection logic derived from it) are invalidated. Keep schema
definitions byte-stable across a session; treat schema edits as cache
busting.

## GPT-5.6 cache efficiency discipline (2026 guidance)

From the official guide: at most **one explicit breakpoint per
request**, placed at the boundary between the most stable and most
volatile prompt section (typically after the system prompt, before the
chat history). "Automatically inserted implicit breakpoints are
disabled when using explicit breakpoints." With `mode: explicit`, only
explicit breakpoints are used.

`prompt_cache_options.mode`:
- `implicit` (default): automatic breakpoint on the latest message +
  any explicit breakpoints. If only the automatic one is set, it
  behaves as a normal automatic breakpoint.
- `explicit`: only explicit breakpoints are used — no automatic
  writes. This is how you opt OUT of write premiums on chat history
  while keeping a system-prompt breakpoint.

`prompt_cache_options.ttl`: `30m` only (the default).

## References

- https://platform.openai.com/docs/guides/prompt-caching
- https://openai.com/index/api-prompt-caching/ (announcement)
- Responses API reference (`prompt_cache_key`):
  https://platform.openai.com/docs/api-reference/responses/create

---

_Last verified: 2026-08-28 (2026-08 research ledger). Pre-5.6 claims
(1024-token minimum, byte-identity rule, 5-10min idle TTL,
`prompt_cache_key` Responses API) carried from the 2026-05-27
verification against live ChatGPT Codex backend traffic. GPT-5.6+
claims (explicit breakpoints, 1.25x write premium, 0.1x hit discount,
`prompt_cache_options`, Chat Completions `prompt_cache_key`) verified
against the fetched 2026-08 prompt-caching guide._
