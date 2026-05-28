---
name: opencode-detect-openai-compat
description: OpenCode's caching detection misses OpenAI-compatible proxies routing to Anthropic/Bedrock. Broaden the predicate.
target_harness: OpenCode
target_repo: sst/opencode
target_files:
  - packages/opencode/src/provider/transform.ts
target_commit: dev branch @ a9ef5a0f
estimated_savings: 0 → ~90% hit rate for users on LiteLLM/Bifrost/MiMo routing to Claude
---

# OpenCode: detect OpenAI-compatible Anthropic proxies (#25984, #26460)

## Target

`packages/opencode/src/provider/transform.ts` → `applyCaching()` in
`sst/opencode`.

Open issues: #25984 (Bifrost/LiteLLM → Bedrock), #26460 (Xiaomi MiMo).

## Symptom

When the user routes Anthropic-shaped models through an
OpenAI-compatible proxy (LiteLLM, Bifrost, or any
`@ai-sdk/openai-compatible` adapter), OpenCode falls through to the
OpenAI caching path and sets `promptCacheKey` (OpenAI shape). The
proxy forwards this verbatim to the Anthropic backend, which ignores
it. Result: 0% cache hit rate on what is otherwise the canonical
"long agent loop on Claude" use case.

Affected routes:
- LiteLLM proxy → Bedrock Anthropic
- Bifrost → Bedrock Anthropic
- Xiaomi MiMo (Anthropic-shaped, marketed as OpenAI-compatible)
- Any custom `@ai-sdk/openai-compatible` endpoint with Claude backend

## Fix

Broaden the detection predicate so OpenAI-compatible adapters with
Anthropic-shaped models get Anthropic-style caching:

```diff
--- a/packages/opencode/src/provider/transform.ts
+++ b/packages/opencode/src/provider/transform.ts
@@ function applyCaching(msgs, model)
   if (
     model.providerID === "anthropic" ||
     model.api.id.includes("anthropic") ||
     model.api.id.includes("claude") ||
-    model.api.npm === "@ai-sdk/anthropic"
+    model.api.npm === "@ai-sdk/anthropic" ||
+    model.api.npm === "@ai-sdk/google-vertex/anthropic" ||
+    // OpenAI-compatible proxies routing to Anthropic-shaped backends
+    (model.api.npm === "@ai-sdk/openai-compatible" &&
+     (model.api.id.toLowerCase().includes("claude") ||
+      model.api.id.toLowerCase().includes("anthropic") ||
+      model.api.id.toLowerCase().includes("mimo"))) ||
+    // MiniMax and other Anthropic-shaped non-Anthropic models
+    model.api.id.startsWith("minimax/")
   ) {
     // Apply Anthropic-style cache_control on message blocks
   }
```

Optionally factor the predicate into a named helper
(`isAnthropicShapedRoute(model)`) so the same check can be reused
elsewhere in OpenCode.

## Verify

1. Configure OpenCode with a LiteLLM endpoint pointing at a Bedrock
   Claude model:
   ```yaml
   provider:
     openai-compatible:
       baseURL: http://localhost:4000/v1
       models:
         - claude-3-5-sonnet-bedrock
   ```
2. Run two identical prompts.
3. Capture wire to the LiteLLM endpoint.
4. **Before fix**: request body contains `prompt_cache_key`, no
   `cache_control` markers; response `cache_read_input_tokens` always 0.
5. **After fix**: request body has `cache_control` on system + last
   stable message; response shows `cache_read_input_tokens > 0` on
   turn 2.

## Background

This is a routing-layer detection bug, not a caching-logic bug. The
caching CODE is fine; it just never runs for these models because the
predicate didn't anticipate proxy-shaped routes.

Related skills:
- [opencode-bedrock-doc-blocks](../opencode-bedrock-doc-blocks/SKILL.md)
  (#17300) for the DocumentBlock case
- [opencode-mistral-cache-key](../opencode-mistral-cache-key/SKILL.md)
  (#27556) for Mistral support

Full audit: [audits/opencode.md](../../audits/opencode.md).
