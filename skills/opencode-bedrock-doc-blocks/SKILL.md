---
name: opencode-bedrock-doc-blocks
description: OpenCode places cachePoint on Bedrock messages containing DocumentBlocks, which produces a "nothing available to cache" error.
target_harness: OpenCode
target_repo: sst/opencode
target_files:
  - packages/opencode/src/provider/transform.ts
target_commit: dev branch @ a9ef5a0f
estimated_savings: Restores Bedrock caching for sessions that include document attachments
---

# OpenCode: skip cachePoint on Bedrock DocumentBlock messages (#17300)

## Target

`packages/opencode/src/provider/transform.ts` → `applyCaching()` in
`sst/opencode`.

Open issue: #17300 — "Bedrock prompt caching error: nothing available
to cache".

## Symptom

`applyCaching()` places `cachePoint` markers on the last 2 non-system
messages. If either of those messages contains a `DocumentBlock`
(PDF/file attachment that Bedrock processes server-side), the
`cachePoint` lands on content that Bedrock considers non-cacheable,
producing an API error:

```
ValidationException: nothing available to cache
```

The error fails the entire request, not just the caching attempt.

## Fix

Add a DocumentBlock detector and skip `cachePoint` placement on
affected messages, falling through to the next-most-recent stable
non-document message:

```diff
--- a/packages/opencode/src/provider/transform.ts
+++ b/packages/opencode/src/provider/transform.ts
@@ function applyCaching(msgs, model)
+  function hasDocumentBlock(msg: ModelMessage): boolean {
+    if (!Array.isArray(msg.content)) return false;
+    return msg.content.some((b: any) =>
+      b?.type === "document" ||
+      b?.type === "file" ||
+      b?.documentBlock != null
+    );
+  }
+
+  function findLastStableNonDoc(msgs: ModelMessage[], skip: number): number {
+    for (let i = msgs.length - 1 - skip; i >= 0; i--) {
+      if (msgs[i].role !== "system" && !hasDocumentBlock(msgs[i])) {
+        return i;
+      }
+    }
+    return -1;
+  }
@@
-  // Apply to last 2 non-system messages
-  const nonSystemMsgs = msgs.filter(m => m.role !== "system").slice(-2)
-  nonSystemMsgs.forEach(msg => {
-    msg.providerOptions = { /* cachePoint etc. */ }
-  })
+  // For Bedrock, skip DocumentBlock-containing messages — they
+  // can't be cached and produce a hard error.
+  const isBedrock = model.providerID.includes("bedrock");
+  if (isBedrock) {
+    const lastStable = findLastStableNonDoc(msgs, 0);
+    const prevStable = findLastStableNonDoc(msgs, msgs.length - 1 - lastStable + 1);
+    [lastStable, prevStable].forEach(idx => {
+      if (idx < 0) return;
+      msgs[idx].providerOptions = { bedrock: { cachePoint: { type: "default" } } };
+    });
+  } else {
+    // Existing behavior for non-Bedrock providers
+    const nonSystemMsgs = msgs.filter(m => m.role !== "system").slice(-2);
+    nonSystemMsgs.forEach(msg => {
+      msg.providerOptions = { /* cachePoint etc. */ };
+    });
+  }
```

## Verify

1. Configure OpenCode with a Bedrock Claude model.
2. Attach a PDF or text document to a chat message.
3. Send a follow-up prompt referencing the document.
4. **Before fix**: Bedrock returns 400 ValidationException.
5. **After fix**: request succeeds; `cachePoint` lands on the most
   recent non-document message; response shows
   `cacheReadInputTokenCount > 0` on the second identical follow-up.

## Background

Bedrock's `cachePoint` requires that the prefix it caches contains
cacheable content. DocumentBlocks are processed server-side and
don't count toward the cacheable token budget — placing a
`cachePoint` on a message where the only content is a document
produces the "nothing to cache" error.

The fix is to detect document-containing messages and route the
breakpoint to the next-most-stable text-bearing message.

See [`docs/concepts/bedrock.md`](../../docs/concepts/bedrock.md).
Full audit: [`audits/opencode.md`](../../audits/opencode.md).
