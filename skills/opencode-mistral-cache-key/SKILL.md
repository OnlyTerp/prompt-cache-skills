---
name: opencode-mistral-cache-key
description: OpenCode doesn't set prompt_cache_key for Mistral models, missing the documented 10% cached-token discount.
target_harness: OpenCode
target_repo: sst/opencode
target_files:
  - packages/opencode/src/provider/transform.ts
target_commit: dev branch @ a9ef5a0f
estimated_savings: 90% input discount on Mistral cached tokens (currently 0%)
---

# OpenCode: enable Mistral prompt caching (#27556)

## Target

`packages/opencode/src/provider/transform.ts` →
`ProviderTransform.options()` in `sst/opencode`.

Open feature request: #27556.

## Symptom

Mistral's API supports prompt caching with a 10% pricing on cached
tokens (similar to OpenAI's Responses API). The mechanism is a
`prompt_cache_key` field on the request that Mistral uses as a
routing hint, plus prefix stability.

OpenCode does not set `prompt_cache_key` for Mistral models. Even
though Mistral supports caching server-side, OpenCode-routed Mistral
calls never hit the cache.

## Fix

Add Mistral to the providers that get an auto-set `prompt_cache_key`:

```diff
--- a/packages/opencode/src/provider/transform.ts
+++ b/packages/opencode/src/provider/transform.ts
@@ ProviderTransform.options(input, model)
   // OpenAI Responses
   if (/* model uses OpenAI responses */) {
     result["promptCacheKey"] = stableHashFor(input);
   }
+
+  // Mistral
+  if (model.providerID === "mistral" ||
+      model.api.npm === "@ai-sdk/mistral") {
+    result["prompt_cache_key"] = stableHashFor(input);
+  }
```

Where `stableHashFor(input)` returns a stable per-session hash —
typically the session ID, or a sha256 of the system prompt if no
session ID is available. NEVER use a per-request UUID (see
`docs/gotchas.md` #9b).

## Verify

1. Configure OpenCode with `mistral-large-latest` or similar.
2. Send two identical prompts.
3. Capture wire to Mistral.
4. **Before fix**: request body has no `prompt_cache_key` field.
5. **After fix**: `prompt_cache_key` field present and identical
   across both requests.
6. Inspect response usage for cached-token indicators (Mistral
   reports these similarly to OpenAI).

## Background

The Responses-API-style `prompt_cache_key` pattern is industry
standard for explicit cache routing — Mistral, OpenAI, and several
other providers all use the same field name. OpenCode wires it for
OpenAI but missed Mistral.

See [`docs/concepts/openai.md`](../../docs/concepts/openai.md)
"The `prompt_cache_key` trick" — same pattern applies to Mistral.

Full audit: [`audits/opencode.md`](../../audits/opencode.md).
