---
name: roo-fix-volatile-msg
description: Ladder-aware Roo Code Anthropic caching — verify the rolling read/write ladder on the wire, then close the real gaps (Vertex 4-block budget, MiniMax path).
target_harness: Roo Code
target_repo: RooCodeInc/Roo-Code
target_files:
  - src/api/transform/caching/anthropic.ts
  - src/api/providers/anthropic.ts
  - src/api/providers/anthropic-vertex.ts
  - src/api/providers/minimax.ts
target_commit: v3.54.0 (ladder verified live 2026-08-28; transform moved to src/api/transform/caching/)
estimated_savings: avoids a harmful "fix" + protects Vertex 4-block budget
---

# Roo Code: the "volatile message" is a rolling ladder — verify, don't rip out

> **REANALYZED 2026-08-28.** The previous version of this skill
> replaced Roo's last-two-user-messages marking with a single "last
> stable message" breakpoint. Direct source recon shows Roo (a Cline
> fork) carries the same documented rolling read/write ladder as
> Cline — the inline comment explains it verbatim. Applying the old
> diff would remove a working cache write point. Verify the ladder
> instead; the real Roo-specific wins are below.

## Target

`src/api/transform/caching/anthropic.ts` in `RooCodeInc/Roo-Code`
(moved there by v3.54.0 — the ladder function `addCacheBreakpoints`
lives in that file now; `src/api/providers/anthropic.ts` calls it).

Permalink: https://github.com/RooCodeInc/Roo-Code/blob/v3.54.0/src/api/transform/caching/anthropic.ts

## What Roo actually does

Same shape as Cline (see
[cline-fix-volatile-msg](../cline-fix-volatile-msg/SKILL.md) for the
full ladder explanation — Roo's inline comment documents it
verbatim): current user turn = write point, previous user turn = read
point, system prompt has its own breakpoint.

## Step 1 — verify the ladder on the wire (before any change)

Same 3-turn capture as the Cline skill. **Ladder holds** → leave the
breakpoints alone. **Thrash** → real bug, apply the Cline skill's
diagnosis. Do not skip this step on the strength of the source code
alone — the ladder only proves itself on the wire.

## Step 2 — Vertex: respect the 4-block budget explicitly

Roo's `anthropic-vertex.ts` documents Vertex-specific limits: max 4
`cache_control` blocks, text-only, user/assistant restrictions — and
implements an explicit strategy (system + last text block of each of
the last two user messages). If you patch message-level caching on
direct Anthropic, make sure the Vertex path still fits its own budget:

- System prompt: 1 block
- Last text block of second-to-last user message: 1
- Last text block of last user message: 1
- → 3 used, 1 spare. Any added breakpoint must not be a 4th on Vertex
  unless it replaces a message breakpoint.

## Step 3 — OpenAI-native lanes: the missing `prompt_cache_key`

Roo scans show **zero** `prompt_cache_key` usage across the codebase
(665 TS files checked, 2026-08-28). Its OpenAI-native handler relies
on automatic prefix matching only. That works for single-session use
but leaves multi-worker pod routing to chance — the same gap Cline
has. See [cline-openai-cache-key](../cline-openai-cache-key/SKILL.md)
for the hash-derivation pattern; the same fix applies to
`src/api/providers/openai-native.ts` (derive the key from system
prompt + model slug, NOT a per-session UUID).

## Step 4 — MiniMax / anthropic-compat providers inherit the ladder

Roo's `minimax.ts` handler (and any Anthropic-compatible provider
added later) re-implements `addCacheControl` with the same
last-two-user-messages shape. Any future provider handler copied from
it inherits the ladder — apply the same verify-don't-rip rule, and
check the compat endpoint actually honors `cache_control` (gotcha 17:
a 200 response proves nothing).

## Verify (whole skill)

3-turn capture on the direct Anthropic path unchanged in shape;
Vertex capture shows ≤4 blocks per request; OpenAI path shows stable
`prompt_cache_key` across turns and non-zero `cached_tokens` by turn 2.

## Background

- [docs/gotchas.md](../../docs/gotchas.md) #17, #18.
- Full audit: [audits/roo-code.md](../../audits/roo-code.md).
