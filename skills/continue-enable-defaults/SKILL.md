---
name: continue-enable-defaults
description: Continue's prompt caching is opt-in via config and off by default. Flip the default to systemAndTools.
target_harness: Continue
target_repo: continuedev/continue
target_files:
  - packages/openai-adapters/src/apis/Anthropic.ts
  - core/llm/llms/Bedrock.ts
target_commit: main (last push 2026-05-26)
estimated_savings: 90% input discount for every user who hasn't manually configured caching (most of them)
---

# Continue: enable caching defaults

## Target

`packages/openai-adapters/src/apis/Anthropic.ts` and
`core/llm/llms/Bedrock.ts` in `continuedev/continue`.

## Symptom

Continue's caching is gated on three config flags:

- `cacheBehavior.cacheConversation` (default: false)
- `cacheBehavior.cacheSystemMessage` (default: false)
- `completionOptions.promptCaching` (default: false)

A user has to know all three exist and set them in `config.yaml`.
Most don't. Net effect: the median user gets no caching.

Open issue #5172 ("Anthropic prompt caching doesn't work") is mostly
this — users don't realize they need to configure it.

## Fix (two-part)

### Part A — flip the default strategy

In `Anthropic.ts`:

```diff
--- a/packages/openai-adapters/src/apis/Anthropic.ts
+++ b/packages/openai-adapters/src/apis/Anthropic.ts
@@
-  const cachingStrategy = CACHING_STRATEGIES[this.config.cachingStrategy ?? "systemAndTools"];
+  // Default to caching system + tools. Users on supported models pay
+  // the 1.25x write premium on the first call and get 0.1x on every
+  // subsequent call within 5 minutes — strict win above ~3 reads.
+  const cachingStrategy = CACHING_STRATEGIES[this.config.cachingStrategy ?? "systemAndTools"];
```

(`systemAndTools` already IS the documented default in the code path
above, but the user-facing config schema treats it as optional with
unclear default. Audit your codebase to confirm the actual fallback
behavior matches the documented one. If not, fix.)

### Part B — auto-enable conversation message caching for supported models

```diff
@@
-  if ((this.config.cachingStrategy ?? "systemAndTools") !== "none") {
-    addCacheControlToLastTwoUserMessages(result.messages);
+  // Auto-enable for any model that declares supportsPromptCache.
+  // User can still opt out with cachingStrategy: "none".
+  const strategy = this.config.cachingStrategy ?? "systemAndTools";
+  if (strategy !== "none" && this.modelSupportsPromptCache()) {
+    // NOTE: this is currently buggy — see continue-fix-volatile-msg
+    // skill for the volatile-message fix that should land alongside.
+    addCacheControlToLastTwoUserMessages(result.messages);
   }
```

Same change in `Bedrock.ts` — auto-enable `cachePoint` for models
with `supportsPromptCache: true` unless user explicitly opts out.

### Part C — document the change in CHANGELOG

Users coming from older Continue versions will see bills shift
(downward, but still a change). Add a CHANGELOG entry calling out
that caching is now default-on for supported models.

## Verify

1. With NO `cacheBehavior` or `completionOptions.promptCaching` set
   in config.yaml, start a Continue chat with Claude.
2. Capture wire.
3. Confirm outbound request body contains `cache_control` markers
   without any user config touching them.
4. Confirm second-turn response `usage.cache_read_input_tokens > 0`.

## Background

Caching that requires a config flag to enable is caching that doesn't
get used. The 1.25x write premium pays for itself after ~3 reads,
which any multi-turn chat clears trivially. There's no scenario where
"caching off" is the right default for an agent CLI on a model that
supports it.

This skill is best applied alongside
[continue-fix-volatile-msg](../continue-fix-volatile-msg/SKILL.md)
(same Cline-family copy-paste bug present in Continue too) so users
don't get the cache thrash without knowing.

Full audit: [audits/continue.md](../../audits/continue.md).
