---
name: cline-fix-volatile-msg
description: Stop Cline from burning a cache breakpoint on the volatile current user message every turn.
target_harness: Cline
target_repo: cline/cline
target_files:
  - src/core/api/transform/anthropic-format.ts
target_commit: 65e9727c (verify current at apply time)
estimated_savings: ~30% wasted cache write premium eliminated per turn
---

# Cline: fix volatile-message cache thrash

## Target

`src/core/api/transform/anthropic-format.ts` in `cline/cline`.

Permalink: https://github.com/cline/cline/blob/65e9727c/src/core/api/transform/anthropic-format.ts

## Symptom

Cline marks the LAST TWO USER MESSAGES with `cache_control: ephemeral`.
The last user message is the CURRENT user turn — it's different on
every request by definition. Caching content that changes every
request pays the 1.25x write premium on those tokens every turn for
zero cache reads. Net result: one of Cline's 3 breakpoints is burned
producing nothing.

You can confirm on the wire: in two consecutive identical-prompt
turns, the response `usage.cache_creation_input_tokens` stays > 0 on
turn 2 instead of dropping to ~0.

## Fix

Replace the "last 2 user messages" logic with "last STABLE message"
(typically the previous assistant turn or tool_result):

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
+  // Cache the LAST STABLE message — the message BEFORE the current
+  // user turn. The current user turn changes every request and would
+  // pay the 1.25x cache-write premium for zero subsequent reads.
+  // The previous turn (assistant message or tool_result) is stable
+  // across the request → response cycle.
+  const lastStableIdx = clineMessages.length >= 2
+    ? clineMessages.length - 2
+    : -1
@@
-    if (supportCache && (index === lastUserMsgIndex || index === secondLastMsgUserIndex)) {
+    if (supportCache && index === lastStableIdx) {
       return addCacheControl(anthropicMsg)
     }
```

This frees one breakpoint. Optionally use that freed breakpoint to
cache the tools array independently — see `audits/cline.md` for the
extended pattern.

## Verify

1. Start mitmproxy: `mitmdump -p 8090 -w /tmp/cline.flow`
2. Configure Cline to route through proxy (Settings → Anthropic Base URL → `http://127.0.0.1:8090`)
3. Run the same prompt twice in a row in the same Cline task ("list files in this repo")
4. Inspect the second-turn response `usage`:
   - **Before fix**: `cache_creation_input_tokens` > 0 every turn (bug)
   - **After fix**: `cache_creation_input_tokens` ≈ 0, `cache_read_input_tokens` covers system + tools + previous turn

Hit rate (turn 2): should be ≥80% of input tokens.

## Background

See [docs/gotchas.md](../../docs/gotchas.md) #1 ("Putting `cache_control`
on volatile content"). Anthropic caches the entire prefix up to and
including the marked block; marking a block that mutates per request
means the cache is invalidated every request.

Full audit: [audits/cline.md](../../audits/cline.md).
