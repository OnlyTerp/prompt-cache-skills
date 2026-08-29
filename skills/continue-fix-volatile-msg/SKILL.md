---
name: continue-fix-volatile-msg
description: Ladder-aware Continue Anthropic caching — verify the rolling ladder on the wire, then enable it by default and add TTL coverage.
target_harness: Continue
target_repo: continuedev/continue
target_files:
  - packages/openai-adapters/src/apis/Anthropic.ts
  - core/llm/llms/Bedrock.ts
target_commit: main (AnthropicUtils.ts addCacheControlToLastTwoUserMessages verified 2026-08-28)
estimated_savings: avoids a harmful "fix"; default-on + TTL are the real wins
---

# Continue: the "volatile message" is a rolling ladder — verify, don't rip out

> **REANALYZED 2026-08-28.** The previous version of this skill
> renamed `addCacheControlToLastTwoUserMessages` to a "last stable
> message" variant. Direct source recon shows Continue ships the same
> documented rolling read/write ladder as Cline/Roo (the helper name
> persists in `packages/openai-adapters/src/apis/AnthropicUtils.ts`).
> Applying the old diff would remove a working cache write point.

## Target

`packages/openai-adapters/src/apis/AnthropicUtils.ts` (helper) and its
callers in the Anthropic adapter; `core/llm/llms/Bedrock.ts`
(`_addCachingToLastTwoUserMessages`, `cachePoint` shape) for the
Bedrock path.

## What Continue actually does

Same two-breakpoint ladder as Cline/Roo: current user turn = write
point, previous user turn = read point. See
[cline-fix-volatile-msg](../cline-fix-volatile-msg/SKILL.md) for the
full explanation and the 3-turn wire test. Continue's distinct problem
is not the ladder — it's that caching is **gated behind config and
off by default**, so most users get nothing at all, and no TTL
extension exists for long sessions.

## Step 1 — verify the ladder on the wire (before any change)

Same 3-turn capture as the Cline skill. Continue gates the whole
caching path behind `cacheBehavior` config — if the capture shows
zero cache fields in the request at all, fix the config first (next
step) and re-capture before judging the ladder.

## Step 2 — default-on (the actual money fix)

Continue's `cacheBehavior` config defaults leave Anthropic caching
off for most installs. See
[continue-enable-defaults](../continue-enable-defaults/SKILL.md) —
that skill remains the primary win for this harness. The ladder
should be verified *after* defaults are on, never instead.

## Step 3 — Bedrock path: verify the cachePoint translation

Continue's Bedrock adapter re-implements caching with `cachePoint`
(not `cache_control` — gotcha 12). Two checks before trusting it:

1. The `cachePoint` placement mirrors the ladder (write point on the
   current turn, read point on the previous) — same 3-turn wire test
   through the Bedrock envelope, reading
   `cacheReadInputTokenCount`/`cacheWriteInputTokenCount`.
2. The Bedrock model ID in use actually supports cache points (gotcha
   13 — the AWS support matrix drifts; verify, don't assume).

## Verify (whole skill)

After default-on: request bodies contain `cache_control` on the
ladder positions; 3-turn capture shows the write@N → read@N+1
pattern; Bedrock capture shows the same through `cachePoint`.

## Background

- [docs/gotchas.md](../../docs/gotchas.md) #12 (cachePoint), #17
  (relay field-stripping), #18 (the ladder test).
- Full audit: [audits/continue.md](../../audits/continue.md).
