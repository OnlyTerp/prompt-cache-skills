# Roo Code

> **Historical audit.** Roo Code is archived. Its own
> [archival disclaimer](https://github.com/RooCodeInc/Roo-Code#disclaimer)
> identifies [Zoo Code](https://github.com/Zoo-Code-Org/Zoo-Code) as
> the community successor. Names, repository coordinates, issue IDs,
> and findings below describe Roo Code v3.54.0 at the audit date.

| Field | Value |
|-------|-------|
| Repo | `RooCodeInc/Roo-Code` |
| Audited commit | branch `main` @ v3.54.0 (2026-05-15) |
| Audit date | 2026-05-27 |
| Auditor | terp (source recon via subagent_explore) |
| Provider tested | Anthropic, Bedrock, OpenRouter, OpenAI native |
| Verdict | **partial** (same Anthropic pattern as Cline; Bedrock custom-ARN gap) |

## Summary

Roo Code is a Cline fork and inherits Cline's caching architecture
with light refactoring (inlining helpers, removing the thinking-block
filter). Same canonical placement: `cache_control: ephemeral` on
system prompt + last 2 user messages. Same volatile-message bug as
Cline (see [`cline.md`](cline.md) and gotcha #1 in
[`../docs/gotchas.md`](../docs/gotchas.md)).

Bedrock has a Roo-specific gap: `guessModelInfoFromId()` doesn't
populate `cachableFields` for custom ARN models, so those silently
skip caching (issue #11983, PR #11984 pending). Cline doesn't have
this issue.

OpenRouter and OpenAI native paths work correctly. OpenAI uses
`prompt_cache_key` — improvement over Cline, which doesn't.

## Source inspection

### Anthropic — `src/api/providers/anthropic.ts`

```typescript
const cacheControl: CacheControlEphemeral = { type: "ephemeral" }
// ...
system: [{ text: systemPrompt, type: "text", cache_control: cacheControl }]
// ...
const userMsgIndices = sanitizedMessages.reduce(
  (acc, msg, index) => (msg.role === "user" ? [...acc, index] : acc),
  [] as number[],
)
const lastUserMsgIndex = userMsgIndices[userMsgIndices.length - 1] ?? -1
const secondLastMsgUserIndex = userMsgIndices[userMsgIndices.length - 2] ?? -1

messages: sanitizedMessages.map((message, index) => {
  if (index === lastUserMsgIndex || index === secondLastMsgUserIndex) {
    return {
      ...message,
      content: typeof message.content === "string"
        ? [{ type: "text", text: message.content, cache_control: cacheControl }]
        : message.content.map((block) => ({ ...block, cache_control: cacheControl }))
    }
  }
  return message
})
```

Same fundamental bug as Cline: marking the LAST user message
(volatile, changes every turn) burns a breakpoint for zero reads.

Permalink: https://github.com/RooCodeInc/Roo-Code/blob/main/src/api/providers/anthropic.ts

### Bedrock — `src/api/providers/bedrock.ts`

Uses `cachePoint: { type: "default" }` correctly. Caching gated on
`supportsPromptCache: true` per model, plus a `cachableFields` array
indicating which sections (`system`, `messages`, `tools`) to cache.

**Bug (issue #11983):** `guessModelInfoFromId()` returns
`{ supportsPromptCache: true }` for custom Claude ARN patterns but
omits `cachableFields`. With an empty cachableFields, the Bedrock
provider hits an early-exit guard and never places `cachePoint`
markers. Net effect: caching silently off for custom ARNs.

### OpenRouter — `src/api/providers/openrouter.ts`

Cleaner than Cline's path. Imports `addCacheBreakpoints` from a
provider-specific transform module (`transform/caching/anthropic`,
`transform/caching/gemini`) and dispatches based on
`OPEN_ROUTER_PROMPT_CACHING_MODELS` membership.

### OpenAI native — `src/api/providers/openai-native.ts`

**Notable improvement over Cline:** Roo sets `prompt_cache_key` (Cline
doesn't). Uses a deterministic hash of system prompt + first message
as the key, which is the correct pattern (gotcha #9b).

This is the one place Roo is unambiguously ahead of Cline.

## Diff vs Cline

| Aspect | Roo | Cline |
|--------|-----|-------|
| Anthropic cache logic | Inlined in `createMessage()` | Helper `addCacheControl()` in `anthropic-format.ts` |
| Thinking block handling | None | Filters thinking blocks before caching |
| Bedrock `cachePoint` | Correct, but custom ARN gap | Correct |
| OpenAI `prompt_cache_key` | **Set (deterministic hash)** | **Not set** |
| Breakpoint pattern | system + last 2 user | Same |
| Volatile-msg bug | Present | Present |

## Wire capture

Not performed. Same methodology as Cline applies.

## Verdict reasoning

**Partial.** Per-provider:

| Provider | Verdict | Reason |
|----------|---------|--------|
| Anthropic | partial | Same volatile-msg bug as Cline |
| Bedrock | partial | Works for declared models; custom ARN gap (#11983) |
| OpenRouter | working | Delegates correctly |
| OpenAI native | working | `prompt_cache_key` set with stable hash |

Net: Roo is roughly tied with Cline overall — better on OpenAI, worse
on Bedrock for custom ARNs.

## Patches

### Patch 1: same as Cline — fix volatile-msg breakpoint

See [`cline.md`](cline.md) "Patch 1". The same diff (mutatis mutandis
for the inline-vs-helper structure) applies.

### Patch 2: Bedrock custom ARN cachableFields (#11983)

```diff
--- a/src/api/providers/bedrock.ts
+++ b/src/api/providers/bedrock.ts
@@ guessModelInfoFromId(...)
   if (/* matches claude pattern */) {
-    return { supportsPromptCache: true }
+    return {
+      supportsPromptCache: true,
+      cachableFields: ["system", "messages", "tools"]
+    }
   }
```

PR #11984 already proposes a version of this fix. Verify it doesn't
also need to populate `cachableFields` on the manual-config branch.

PR status: not submitted (Patch 1); #11984 already open (Patch 2).

## Reproduction

Source-only audit. To verify Bedrock #11983 specifically:

```bash
# Use a custom Bedrock ARN (not one of the declared model IDs)
HTTPS_PROXY=http://127.0.0.1:8090 \
  # configure Roo with awsCustomArn set to a Claude ARN
# Run two identical prompts
# Inspect: cachePoint should appear in request body — won't, due to bug
```

## Notes

- Roo's lead on OpenAI caching is worth highlighting in Cline upstream:
  the deterministic-hash `prompt_cache_key` approach is portable and
  works for any Cline-family harness.
- The thinking-block filter Cline has but Roo removed: worth checking
  whether Roo's lack of filter causes issues when extended thinking
  is on. Not investigated this audit.
