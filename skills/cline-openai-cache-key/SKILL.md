---
name: cline-openai-cache-key
description: Cline OpenAI native provider sends no prompt_cache_key. Add a stable per-task key so cached_tokens stops being zero.
target_harness: Cline
target_repo: cline/cline
target_files:
  - src/core/api/providers/openai-native.ts
target_commit: 65e9727c (verify current at apply time)
estimated_savings: 50-90% input discount on OpenAI calls (currently 0%)
---

# Cline: add `prompt_cache_key` to OpenAI native provider

## Target

`src/core/api/providers/openai-native.ts` in `cline/cline`.

Permalink: https://github.com/cline/cline/blob/65e9727c/src/core/api/providers/openai-native.ts

## Symptom

Cline's OpenAI native provider only READS cache stats from responses,
it never enables caching:

```typescript
const cacheReadTokens = usage?.prompt_tokens_details?.cached_tokens || 0
const cacheWriteTokens = 0  // ← always 0
```

No `prompt_cache_key` set on the Responses API call, no work done to
verify prefix stability. OpenAI's automatic prefix caching may still
fire if the prefix happens to be byte-stable, but routing is random
across pods so hit rates are low and unpredictable.

Open issue #554 ("OpenAI Prompt Caching appears not enabled?") tracks
user-side confusion. PR #1156 attempted a partial fix but was closed
without merging.

## Fix

Set a stable `prompt_cache_key` derived from the task ID (or a hash of
the system instructions if no task ID is available). NEVER use a
per-request UUID — that's worse than no key.

```diff
--- a/src/core/api/providers/openai-native.ts
+++ b/src/core/api/providers/openai-native.ts
@@
-  const response = await client.responses.create({
+  // Stable cache key: same task = same pod = warm cache.
+  // NEVER use uuid() — random keys force random pod routing and
+  // kill cache hits.
+  const cacheKey = this.options.taskId
+    || this.options.ulid
+    || crypto.createHash("sha256")
+         .update(systemPrompt)
+         .digest("hex")
+         .slice(0, 16)
+
+  const response = await client.responses.create({
     model: modelId,
     input: messages,
+    prompt_cache_key: `cline:${modelId}:${cacheKey}`,
     ...
   })
```

If the harness uses the legacy Chat Completions endpoint
(`client.chat.completions.create`), `prompt_cache_key` isn't a valid
field there. In that case the only knob is prefix stability — make
sure the system prompt has no per-request timestamps, session IDs, or
randomized content.

## Verify

1. Start mitmproxy capture as before.
2. Configure Cline with an OpenAI model (`gpt-5.4`, `gpt-5-codex`, etc.).
3. Send two identical prompts in the same task.
4. Inspect captured requests:
   - `prompt_cache_key` field present and identical across both
   - System prompt bytes identical
5. Inspect responses:
   - Turn 2 `usage.prompt_tokens_details.cached_tokens` > 0
   - Ratio `cached_tokens / prompt_tokens` ≥ 0.5 on a steady-state turn

## Background

OpenAI's Responses API uses `prompt_cache_key` as a pod-routing hint.
Stable key = same pod = warm cache. Per-request UUIDs are the #1
silent killer of OpenAI cache hits.

See [docs/gotchas.md](../../docs/gotchas.md) #9b for the full
explanation, and [docs/concepts/openai.md](../../docs/concepts/openai.md)
"The `prompt_cache_key` trick".

Reference implementation: Codex CLI uses session `thread_id` as the
cache key and preserves it across compaction and sub-agents — see
[audits/codex-cli.md](../../audits/codex-cli.md).

Full audit: [audits/cline.md](../../audits/cline.md).
