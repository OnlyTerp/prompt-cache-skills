# Cline

| Field | Value |
|-------|-------|
| Repo | `cline/cline` |
| Audited commit | `65e9727c` (cross-checked against `03ab2968`) |
| Audit date | 2026-05-27 |
| Auditor | terp (source recon via subagent_explore) |
| Provider tested | Anthropic, Bedrock, OpenAI native, OpenRouter, Vertex |
| Verdict | **partial** (working on most; broken on OpenAI native; cache-thrash on Anthropic) |

## Summary

Cline sets `cache_control` correctly on the Anthropic, OpenRouter, and
Vertex providers — 3 breakpoints (system + last 2 user messages),
ephemeral 5min TTL. Bedrock has the `cachePoint` interface defined but
the implementation is gated behind a flag and incomplete. OpenAI native
provider sends NO caching hints at all: no `prompt_cache_key`, no
prefix-stability work — it only *reads* `cached_tokens` from responses.

The Anthropic provider has a subtler issue: marking the LAST TWO USER
MESSAGES (one of which is the volatile current turn) is partial
cache-thrash. The current user message changes every turn by
definition, so that breakpoint pays the 1.25x write premium every turn
for zero reads. Half the breakpoint budget is being burned. See
gotcha #1 in [`../docs/gotchas.md`](../docs/gotchas.md).

There's also a documented timestamp-in-system-prompt issue (PR #1168)
that breaks the system-prompt cache if the timestamp is recomputed per
request.

## Source inspection

### Anthropic — `src/core/api/providers/anthropic.ts`

System prompt cached correctly:

```typescript
system: [
  {
    text: systemPrompt,
    type: "text",
    cache_control: { type: "ephemeral" },
  },
],
```

Last 2 user messages cached (in `src/core/api/transform/anthropic-format.ts`):

```typescript
if (supportCache && (index === lastUserMsgIndex || index === secondLastMsgUserIndex)) {
  return addCacheControl(anthropicMsg)
}
```

**Bug:** The last user message changes every turn. Caching it = paying
write premium for zero reads. The correct pattern is to cache the
last STABLE turn (the previous assistant message OR the last tool_result),
not the current user input.

Tools are NOT cached separately — they ride along with the system prompt
cache, which works as long as both stay byte-stable.

Permalink: https://github.com/cline/cline/blob/65e9727c/src/core/api/providers/anthropic.ts

### Bedrock — `src/core/api/providers/bedrock.ts`

`CachePointContentBlock` interface defined but usage gated behind
`awsBedrockUsePromptCache` flag. Implementation incomplete. PR #2034
attempted to land this; merge state unclear.

### OpenAI native — `src/core/api/providers/openai-native.ts`

**Reads** cache stats:

```typescript
const cacheReadTokens = usage?.prompt_tokens_details?.cached_tokens || 0
const cacheWriteTokens = 0  // ← always 0
```

**Doesn't enable caching:** no `prompt_cache_key` set on the Responses
API call, no work to verify prefix stability. Open issue #554 ("OpenAI
Prompt Caching appears not enabled?") tracks user-side confusion. PR
#1156 attempted to fix this for OpenAI-compatible providers but was
closed without merging.

### OpenRouter — `src/core/api/transform/openrouter-stream.ts`

Correctly detects Anthropic / MiniMax via model ID prefix and applies
`cache_control` to system + last 2 user messages. Same pattern as the
direct Anthropic path (and same volatile-message bug).

### Vertex — `src/core/api/providers/vertex.ts`

Correct, conditioned on `model.info.supportsPromptCache`. PR #2240
(Feb 2026) fixed missing cache_control on user messages.

### System prompt timestamp — PR #1168

Reviewer flagged: "if the time is being calculated every time the user
sends a request, it invalidates Anthropic's cache." Merged anyway. If
the timestamp is regenerated per request the system-prompt cache hits
zero.

## Wire capture

Not performed. Recommend: route Cline via mitmproxy on port 8090, run
two identical small tasks ("list files in this repo") back-to-back,
inspect `cache_read_input_tokens` on turn 2 — should be > 0 for the
system prompt and tools, and roughly equal to `cache_creation_input_tokens`
from turn 1 (proves system+tools caching works) but the LAST 2 USER
breakpoints will show fresh `cache_creation` every turn (proves the
volatile-message bug).

## Verdict reasoning

**Partial.** Per-provider breakdown:

| Provider | Verdict | Reason |
|----------|---------|--------|
| Anthropic | partial | System cache works; user-msg breakpoints thrash (gotcha #1) |
| OpenRouter (Anthropic) | partial | Same as direct Anthropic |
| Vertex (Anthropic) | partial | Same |
| Bedrock | unverified | Implementation incomplete, gated by flag |
| OpenAI native | broken | No `prompt_cache_key`, no prefix stabilization |

## Patches

### Patch 1 (highest value): fix user-message breakpoint thrash

Replace the "last 2 user messages" pattern with "last STABLE
assistant/tool_result turn":

```diff
--- a/src/core/api/transform/anthropic-format.ts
+++ b/src/core/api/transform/anthropic-format.ts
@@
-  const userMsgIndices = clineMessages.reduce((acc, msg, index) => {
-    if (msg.role === "user") acc.push(index)
-    return acc
-  }, [] as number[])
-  const lastUserMsgIndex = userMsgIndices.at(-1)
-  const secondLastMsgUserIndex = userMsgIndices.at(-2)
+  // Cache the LAST STABLE message (not the current user turn, which
+  // changes every request and would force cache-write on every call).
+  // The last assistant/tool_result is stable across the current turn's
+  // request → response cycle.
+  const lastStableIdx = clineMessages.length >= 2 ? clineMessages.length - 2 : -1
@@
-    if (supportCache && (index === lastUserMsgIndex || index === secondLastMsgUserIndex)) {
+    if (supportCache && index === lastStableIdx) {
       return addCacheControl(anthropicMsg)
     }
```

This frees one of the 4 breakpoints (could be used for tools as a
separate breakpoint, currently bundled with system).

### Patch 2: OpenAI native — add stable `prompt_cache_key`

```diff
--- a/src/core/api/providers/openai-native.ts
+++ b/src/core/api/providers/openai-native.ts
@@
-  const response = await client.chat.completions.create({
+  const taskId = this.options.taskId || this.options.ulid
+  const response = await client.chat.completions.create({
     model: modelId,
     messages: openAiMessages,
+    prompt_cache_key: taskId,  // stable per-task; routes to same pod
     ...
   })
```

(Use the task ID, NEVER a per-request UUID — see gotcha #9b.)

### Patch 3: pin the system-prompt timestamp

Compute once at task start, pass through; never recompute per-request.

PR status: not submitted (proposed here for upstream).

## Reproduction

Source-only audit. Wire capture pending — see methodology in
`docs/verification.md`.

## Notes

- Cline has the most user-facing impact of any harness in this audit
  (~most-downloaded Anthropic-targeted OSS agent). Even fixing patch 1
  alone moves a meaningful absolute dollar amount industry-wide.
- Issue #414 (discussion) asks for 1h TTL; not yet implemented. Worth
  a follow-on patch behind a config flag.
