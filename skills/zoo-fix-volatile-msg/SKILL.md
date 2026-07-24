---
name: zoo-fix-volatile-msg
description: Zoo Code inherits the Cline-family volatile-message cache bug. Same fix shape, inline location.
target_harness: Zoo Code
target_repo: Zoo-Code-Org/Zoo-Code
target_files:
  - src/api/providers/anthropic.ts
target_commit: main @ 2634d5c (2026-07-24; verify current at apply time)
estimated_savings: ~30% wasted cache write premium eliminated per turn
---

# Zoo Code: fix volatile-message cache thrash

## Target

`src/api/providers/anthropic.ts` in `Zoo-Code-Org/Zoo-Code`.

Permalink: https://github.com/Zoo-Code-Org/Zoo-Code/blob/main/src/api/providers/anthropic.ts

Zoo Code is the community successor to the archived Roo Code fork. It
retains the inlined Cline-family helper and the same bug in a slightly
different code location.

## Symptom

Same as [cline-fix-volatile-msg](../cline-fix-volatile-msg/SKILL.md):

```typescript
const userMsgIndices = sanitizedMessages.reduce(
  (acc, msg, index) => (msg.role === "user" ? [...acc, index] : acc),
  [] as number[],
)
const lastUserMsgIndex = userMsgIndices[userMsgIndices.length - 1] ?? -1
const secondLastMsgUserIndex = userMsgIndices[userMsgIndices.length - 2] ?? -1

messages: sanitizedMessages.map((message, index) => {
  if (index === lastUserMsgIndex || index === secondLastMsgUserIndex) {
    return { /* adds cache_control */ }
  }
  return message
})
```

`lastUserMsgIndex` is the current user turn. Marking it caches
nothing and pays write premium every turn.

## Fix

```diff
--- a/src/api/providers/anthropic.ts
+++ b/src/api/providers/anthropic.ts
@@
-  const userMsgIndices = sanitizedMessages.reduce(
-    (acc, msg, index) => (msg.role === "user" ? [...acc, index] : acc),
-    [] as number[],
-  )
-  const lastUserMsgIndex = userMsgIndices[userMsgIndices.length - 1] ?? -1
-  const secondLastMsgUserIndex = userMsgIndices[userMsgIndices.length - 2] ?? -1
+  // Cache the LAST STABLE message — the turn BEFORE the current user
+  // input. The current user turn changes every request and forces
+  // cache writes for zero subsequent reads.
+  const lastStableIdx = sanitizedMessages.length >= 2
+    ? sanitizedMessages.length - 2
+    : -1
@@
   messages: sanitizedMessages.map((message, index) => {
-    if (index === lastUserMsgIndex || index === secondLastMsgUserIndex) {
+    if (index === lastStableIdx) {
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

## Verify

Same as Cline's verify procedure — see
[cline-fix-volatile-msg/SKILL.md#verify](../cline-fix-volatile-msg/SKILL.md).
Settings path differs but the wire-level assertion is identical.

## Background

See the parent skill for the full reasoning. Full audit:
historical [Roo Code audit](../../audits/roo-code.md).
