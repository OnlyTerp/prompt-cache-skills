---
name: cline-pin-timestamp
description: Cline's system prompt includes a timestamp that may be recomputed per request, invalidating the system-prompt cache.
target_harness: Cline
target_repo: cline/cline
target_files:
  - src/core/prompts/system.ts
target_commit: 65e9727c (verify current at apply time)
estimated_savings: Restores system-prompt cache reads (large; system prompt is typically 5-15k tokens)
---

# Cline: pin the system-prompt timestamp

## Target

`src/core/prompts/system.ts` in `cline/cline`. PR #1168 added a
current-time field to the system prompt.

## Symptom

The system prompt includes the current time. If the time is computed
per-request (e.g. `new Date().toISOString()` evaluated at every call
site), then the system prompt bytes differ on every request, which
invalidates the system-prompt cache breakpoint. The cache write
premium gets paid every turn for zero reads, on what's usually the
largest single block in the prefix.

PR #1168 was merged despite a reviewer flagging exactly this:
> "Just be aware that if the time is being calculated every time the
> user sends a request, it invalidates Anthropic's cache."

Verify on the wire: if the system text changes between consecutive
calls in the same task, this bug is present.

## Fix

Compute the timestamp ONCE at task start, store it on the task, pass
through to every system prompt build:

```diff
--- a/src/core/prompts/system.ts
+++ b/src/core/prompts/system.ts
@@
-export const SYSTEM_PROMPT = (...args) => `
-  ...
-  Current time: ${new Date().toISOString()}
-  ...
-`
+export const SYSTEM_PROMPT = (args: SystemPromptArgs) => `
+  ...
+  Current time: ${args.taskStartedAt}
+  ...
+`
```

Then in the task initialization code:

```diff
+  this.taskStartedAt = new Date().toISOString()
```

And pass `this.taskStartedAt` everywhere `SYSTEM_PROMPT` is built.

If date awareness is critical for the agent and you want it to drift
during a long session, round to the nearest day or hour rather than
the second — that bounds the cache invalidation rate.

## Verify

1. Start mitmproxy.
2. Run a Cline task. Wait 10 seconds. Send a second prompt in the
   same task.
3. Diff the system prompt bytes between the two requests.
   - **Before fix**: bytes differ (timestamp incremented)
   - **After fix**: bytes identical
4. Confirm response `usage.cache_read_input_tokens` covers the system
   prompt on turn 2.

## Background

Anthropic caches the entire prefix UP TO AND INCLUDING the breakpoint.
A single byte change before or at the breakpoint invalidates
everything. Timestamps are the most common cache killer because they
look innocent and few people think to check.

OpenAI's automatic prefix caching has the same vulnerability — same
fix applies if Cline targets OpenAI as well.

See [docs/gotchas.md](../../docs/gotchas.md) #5 (byte-identity of
tool definitions, same principle for system prompts) and #7
(OpenAI byte-identical prefix requirement).

Full audit: [audits/cline.md](../../audits/cline.md).
