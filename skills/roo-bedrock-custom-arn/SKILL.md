---
name: roo-bedrock-custom-arn
description: Roo Code's Bedrock provider silently disables caching for custom ARNs. Populate cachableFields to fix.
target_harness: Roo Code
target_repo: RooCodeInc/Roo-Code
target_files:
  - src/api/providers/bedrock.ts
target_commit: main @ v3.54.0
estimated_savings: Enables Bedrock prompt caching for custom ARN setups (currently 0%)
---

# Roo Code: Bedrock custom ARN caching (#11983)

## Target

`src/api/providers/bedrock.ts` → `guessModelInfoFromId()` in
`RooCodeInc/Roo-Code`.

Tracked upstream as issue #11983; PR #11984 proposes a fix but
status uncertain at audit time.

## Symptom

When a user configures Bedrock with a custom ARN instead of one of
Roo's hardcoded model IDs, `guessModelInfoFromId()` returns
`{ supportsPromptCache: true }` but omits `cachableFields`. Downstream
the Bedrock provider checks for `cachableFields` and skips caching
entirely when empty. Net effect: silent 0% cache hit on custom ARNs.

Users hit this when:
- Routing through a Bedrock-hosted Claude model with non-standard ARN
- Using cross-region inference profiles
- Provisioned throughput ARNs

## Fix

```diff
--- a/src/api/providers/bedrock.ts
+++ b/src/api/providers/bedrock.ts
@@ guessModelInfoFromId(modelId: string)
   if (/* claude pattern match */) {
-    return { supportsPromptCache: true }
+    return {
+      supportsPromptCache: true,
+      cachableFields: ["system", "messages", "tools"],
+    }
   }
```

Apply this to every branch in `guessModelInfoFromId()` that returns
`supportsPromptCache: true` without populating `cachableFields`.

If `PR #11984` is already merged at apply time, verify the fix
matches this shape and skip the diff.

## Verify

1. Configure Roo with a custom Claude ARN (any ARN not in the
   declared model list).
2. Enable prompt caching in Roo settings.
3. Capture wire via mitmproxy.
4. Inspect outbound Bedrock Converse API request body:
   - **Before fix**: no `cachePoint` markers anywhere in the request
   - **After fix**: `cachePoint: { type: "default" }` blocks on system
     and last stable message
5. Inspect response `usage`:
   - `cacheWriteInputTokenCount > 0` on cold turn
   - `cacheReadInputTokenCount > 0` on warm turn

## Background

Bedrock's Converse API uses a different field name (`cachePoint`)
than direct Anthropic (`cache_control`). Roo handles the translation
correctly for declared models but the custom-ARN detection path is
incomplete.

See [docs/concepts/bedrock.md](../../docs/concepts/bedrock.md).
Full audit: [audits/roo-code.md](../../audits/roo-code.md).
