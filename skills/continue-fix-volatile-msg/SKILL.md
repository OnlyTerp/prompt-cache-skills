---
name: continue-fix-volatile-msg
description: Continue inherits the Cline-family volatile-message cache bug. Same fix shape.
target_harness: Continue
target_repo: continuedev/continue
target_files:
  - packages/openai-adapters/src/apis/Anthropic.ts
  - core/llm/llms/Bedrock.ts
target_commit: main (last push 2026-05-26)
estimated_savings: ~30% wasted cache write premium eliminated per turn
---

# Continue: fix volatile-message cache thrash

## Target

`packages/openai-adapters/src/apis/Anthropic.ts` and
`core/llm/llms/Bedrock.ts` in `continuedev/continue`. The relevant
function is `addCacheControlToLastTwoUserMessages` (Anthropic) and
`_addCachingToLastTwoUserMessages` (Bedrock).

## Symptom

Same as [`cline-fix-volatile-msg`](../cline-fix-volatile-msg/SKILL.md)
and [`roo-fix-volatile-msg`](../roo-fix-volatile-msg/SKILL.md):
Continue caches the last 2 USER messages, including the current
user turn which changes every request. Pays write premium for zero
reads on that breakpoint every turn.

## Fix

Rename and rewire the function to target stable messages (the
previous assistant turn) instead of user messages:

### Anthropic

```diff
--- a/packages/openai-adapters/src/apis/Anthropic.ts
+++ b/packages/openai-adapters/src/apis/Anthropic.ts
@@
-function addCacheControlToLastTwoUserMessages(messages: Message[]) {
-  const userIdxs = messages
-    .map((m, i) => (m.role === "user" ? i : -1))
-    .filter(i => i >= 0);
-  const lastTwo = userIdxs.slice(-2);
-  for (const idx of lastTwo) {
+function addCacheControlToLastStableMessage(messages: Message[]) {
+  // Cache the last STABLE message (not the volatile current user turn).
+  // Stable = the message before the user's in-flight request.
+  if (messages.length < 2) return;
+  const idx = messages.length - 2;
+  {
     const m = messages[idx];
     // ...existing logic to attach cache_control to last content block
   }
 }
```

Update the caller in `_convertBody()` to use the new name.

### Bedrock

Same shape in `core/llm/llms/Bedrock.ts` — replace the
`_addCachingToLastTwoUserMessages` body with the
`_addCachingToLastStableMessage` logic, using `cachePoint` instead of
`cache_control`.

## Verify

Same procedure as the Cline skill — see
[`cline-fix-volatile-msg/SKILL.md#verify`](../cline-fix-volatile-msg/SKILL.md).
Wire-level assertion is identical: turn-2
`cache_creation_input_tokens` should drop to ~0,
`cache_read_input_tokens` should cover the full prefix.

## Background

This is the third instance of the same copy-paste bug (Cline → Roo →
Continue). Apply this skill alongside
[`continue-enable-defaults`](../continue-enable-defaults/SKILL.md)
so users don't get the bug surfaced by the default-on change.

Full audit: [`audits/continue.md`](../../audits/continue.md).
