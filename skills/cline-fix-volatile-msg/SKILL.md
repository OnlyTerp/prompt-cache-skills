---
name: cline-fix-volatile-msg
description: Ladder-aware Cline Anthropic caching — verify the rolling read/write ladder on the wire, then add the tools breakpoint and tune TTL.
target_harness: Cline
target_repo: cline/cline
target_files:
  - src/core/api/transform/anthropic-format.ts
target_commit: 65e9727c (byte-identical on main as of 2026-08-28)
estimated_savings: avoids a harmful "fix" + up to one free breakpoint on tools
---

# Cline: the "volatile message" is a rolling ladder — verify, don't rip out

> **REANALYZED 2026-08-28.** The previous version of this skill called
> Cline's last-two-user-messages pattern a copy-paste bug and replaced
> it with a single "last stable message" breakpoint. Direct source
> recon shows the pattern is a deliberate two-breakpoint rolling
> read/write ladder, documented in Cline's own comment. Applying the
> old diff would remove a working cache write point. This skill now
> verifies the ladder instead of "fixing" it, and lands the changes
> that actually save money.

## Target

`src/core/api/transform/anthropic-format.ts` in `cline/cline`.

Permalink: https://github.com/cline/cline/blob/65e9727c/src/core/api/transform/anthropic-format.ts

## What Cline actually does

```ts
// (Cline's comment, verbatim)
// The latest message will be the new user message, one before will be the
// assistant message from a previous request, and the user message before
// that will be a previously cached user message. So we need to mark the
// latest user message as ephemeral to cache it for the next request, and
// mark the second to last user message as ephemeral to let the server
// know the last message to retrieve from the cache for the current request.
```

Two breakpoints: the current user turn is a **write** point; the
previous user turn is the **read** point. Request N's write premium on
the current turn is recovered as request N+1's cache read. This is the
correct shape for an agent loop — do not replace it with a
"last stable message" breakpoint (equivalent coverage, one turn later,
and it breaks the write-ahead if message structure changes).

## Step 1 — verify the ladder on the wire (before any change)

1. `mitmdump -p 8090 -w /tmp/cline.flow`
2. Point Cline at the proxy (Settings → Anthropic Base URL → `http://127.0.0.1:8090`)
3. Run THREE consecutive turns in one task.
4. Read `usage` from each turn:

| turn | expected | meaning |
|------|----------|---------|
| 1 | `cache_creation > 0`, `cache_read = 0` | cold write |
| 2 | `cache_read ≈ turn-1 creation + system/tools`, `cache_creation ≈ delta` | ladder working |
| 3 | same shape as turn 2 | ladder stable |

- **Ladder holds** (write@N becomes read@N+1): leave the breakpoints
  alone. The savings come from Steps 2–3, not from touching this file.
- **Thrash** (`cache_creation > 0` every turn, `cache_read ≈ 0`
  throughout): only then is this a real volatile-content bug — see
  [docs/gotchas.md](../../docs/gotchas.md) #18 for the diagnosis.

## Step 2 — add the tools breakpoint (real, verifiable win)

Cline spends 2 of its 4 breakpoints on the message ladder and 1 on the
system prompt. Tool definitions are the single largest stable prefix in
an agent loop (often 5–15k tokens) and are currently NOT independently
breakpointed in the Anthropic transform. If tools are re-sent in every
request body (they are), they ride inside whichever prefix breakpoint
covers them — but a dedicated tools breakpoint protects the message
ladder from invalidating on tool-schema changes and keeps tool tokens
in the shortest possible read path.

```diff
--- a/src/core/api/transform/anthropic-format.ts
+++ b/src/core/api/transform/anthropic-format.ts
@@ (where the request is composed; pass tools through the transform)
-  // tools sent as-is
+  // Breakpoint the LAST tool definition: Anthropic caches everything
+  // up to and including the marked block, so marking the final tool
+  // covers the full tools array as its own cache layer.
+  const toolsWithBreakpoint = tools.length
+    ? tools.map((t, i) =>
+        i === tools.length - 1
+          ? { ...t, cache_control: { type: "ephemeral" } }
+          : t,
+      )
+    : tools
```

Verify: turn 2+ `cache_read_input_tokens` should now include the tool
token count even on a task where the system prompt changed.

## Step 3 — TTL: leave 5min for active loops, 1h only for idle-heavy use

- Active Cline sessions turn in seconds; 5min TTL refreshes on every
  hit. Do NOT blanket-extend to 1h — 1h writes cost a 2x premium
  (vs 1.25x for 5min) and pure-loss on an active loop.
- If users resume tasks after >5min gaps (lunch, review), offer an
  opt-in `extended-cache-ttl-2025-04-11` beta header +
  `cache_control: {type: "ephemeral", ttl: "1h"}` on the SYSTEM
  breakpoint only (largest stable prefix, least likely to thrash).
  Default: off.

## Verify (whole skill)

Re-run the Step 1 three-turn capture after landing Step 2:
`cache_read` grows by the tools token count, ladder shape unchanged,
no `cache_creation` on unchanged-prefix segments. Hit rate ≥85%.

## Background

- [docs/gotchas.md](../../docs/gotchas.md) #17 (relays can 200-accept
  and silently drop cache fields — relevant if you run Cline through a
  gateway) and #18 (the 3-turn ladder test).
- Full audit: [audits/cline.md](../../audits/cline.md).
