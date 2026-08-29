---
name: cline-fix-volatile-msg
description: Ladder-aware Cline Anthropic caching — verify the rolling read/write ladder on the wire, then add the tools breakpoint and tune TTL. Updated for the 2026-08 AI-SDK monorepo.
target_harness: Cline
target_repo: cline/cline
target_files:
  - sdk/packages/llms/src/providers/routing/anthropic-compatible.ts
  - sdk/packages/llms/src/providers/ai-sdk.ts
target_commit: desktop-v0.0.20 (monorepo restructure; old src/core/api path 404s)
estimated_savings: avoids a harmful "fix" + up to one free breakpoint on tools
---

# Cline: the "volatile message" is a rolling ladder — verify, don't rip out

> **REANALYZED 2026-08-28 (twice).** v1 of this skill called Cline's
> last-two-user-messages pattern a copy-paste bug. v2 verified the
> pattern is a deliberate two-breakpoint rolling read/write ladder
> (documented in Cline's own comment in
> `src/core/api/transform/anthropic-format.ts`). v3 (this version):
> **upstream restructured into a monorepo** (desktop-v0.0.20, Vercel
> AI SDK). The old transform path is gone. The new mechanism is a
> SINGLE marker on the last user message — same ladder economics,
> fewer markers. The ladder verification methodology below still
> applies verbatim; the file paths and wire shape changed.

## Target

`sdk/packages/llms/src/providers/routing/anthropic-compatible.ts` and
`sdk/packages/llms/src/providers/ai-sdk.ts` in `cline/cline`
(desktop-v0.0.20 monorepo, Vercel AI SDK path).

Permalinks:
- https://github.com/cline/cline/blob/desktop-v0.0.20/sdk/packages/llms/src/providers/routing/anthropic-compatible.ts
- https://github.com/cline/cline/blob/desktop-v0.0.20/sdk/packages/llms/src/providers/ai-sdk.ts

## What Cline actually does (desktop-v0.0.20, AI-SDK path)

The old two-marker ladder lives on only in the git history — the old
`src/core/api/transform/anthropic-format.ts` 404s. The new stack goes
through Vercel AI SDK `streamText`, and cache marking happens in
`buildAiSdkRequestMessages` (ai-sdk.ts, ~line 402-420):

```ts
if (!shouldApplyPromptCache(request, context)) {
    return aiMessages;
}
// ... includeAnthropic = isAnthropicCompatibleModel(...)
for (let i = aiMessages.length - 1; i >= 0; i--) {
    if (aiMessages[i]?.role === "user") {
        applyPromptCacheToLastTextPart(
            aiMessages[i],
            request.providerId,
            includeAnthropic,
        );
        break;                       // <-- ONE marker, last user msg
    }
}
```

`applyPromptCacheToLastTextPart` (anthropic-compatible.ts ~line 110)
attaches `providerOptions` carrying `cache_control: {type:"ephemeral"}`
to the last text part of the last user message — for BOTH the
`anthropic` key (real Anthropic wire) and the `openaiCompatible` key
(OpenAI-compatible relays), via `createPromptCacheProviderOptions`.

Economics: the marker on the last user message is the **write** point;
the previous request's marker — which became stable history — is the
**read** point. One marker per request still produces the same
write@N → read@N+1 ladder as the old two-marker shape, because the
previous turn's marker is retained in the message history. The
`includeAnthropic=false` branch also pads multipart content with a
whitespace text part so `cache_control` stays on a content part instead
of collapsing to message metadata (Anthropic rejects whitespace-only
blocks; relay shapes differ — see the comment at ~line 131).

Gate: `shouldApplyPromptCache` → `resolvePromptCacheRoute` — applies
when the route matcher is `anthropic-compatible`, or via legacy
`promptCacheStrategy: "anthropic-automatic"` provider metadata (Qwen
ids preserved as an opt-in custom-provider behavior, routed to the
OpenAI-compatible cache_control shape).

This is the correct shape for an agent loop — do not replace it with a
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

Cline spends its single message marker on the last user turn and (in
the old shape) one on the system prompt. Tool definitions are the
single largest stable prefix in an agent loop (often 5–15k tokens) and
are NOT independently breakpointed in the new AI-SDK path either. If
tools are re-sent in every request body (they are), they ride inside
whichever prefix breakpoint covers them — but a dedicated tools
breakpoint protects the message ladder from invalidating on
tool-schema changes and keeps tool tokens in the shortest possible
read path.

In the monorepo, tools flow through `buildProviderModelTools` →
`toAiSdkModelToolSet` (ai-sdk.ts ~line 340-379) into `streamText`. The
Vercel AI SDK `@ai-sdk/anthropic` adapter honors per-tool cache control
via the tool's provider options:

```diff
--- a/sdk/packages/llms/src/providers/ai-sdk.ts
+++ b/sdk/packages/llms/src/providers/ai-sdk.ts
@@ toAiSdkModelToolSet (or buildProviderModelTools, where tool objects are finalized)
-  const entries = Object.entries(modelTools).flatMap(([name, adapter]) =>
-    adapter ? [[name, adapter.tool] as const] : [],
-  );
+  // Breakpoint the LAST tool: Anthropic caches everything up to and
+  // including the marked block, so marking the final tool covers the
+  // full tools array as its own cache layer.
+  const names = Object.keys(modelTools).filter((n) => modelTools[n]);
+  const last = names[names.length - 1];
+  const entries = Object.entries(modelTools).flatMap(([name, adapter]) => {
+    if (!adapter) return [];
+    const tool = name === last
+      ? { ...adapter.tool, providerOptions: { anthropic: { cacheControl: { type: "ephemeral" } } } }
+      : adapter.tool;
+    return [[name, tool] as const];
+  });
```

Note: the AI-SDK shape only carries this to the real Anthropic wire
(providerOptions key `anthropic`). OpenAI-compatible relays in the new
path ignore tool-level cache markers — same as before, tools there
still ride the message prefix. Verify on the wire (Step 1 capture) and
only keep the change if `cache_read` on turn 2+ grows by the tools
token count.

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
