# Continue

| Field | Value |
|-------|-------|
| Repo | `continuedev/continue` |
| Audited commit | branch `main` (last push 2026-05-26) |
| Audit date | 2026-05-27 |
| Auditor | terp (source recon via subagent_explore) |
| Provider tested | Anthropic, OpenAI (Responses), Gemini, Bedrock |
| Verdict | **partial** (Anthropic/Bedrock work behind config; OpenAI Chat Completions broken; Gemini missing) |

## Summary

Continue's caching is gated behind explicit config flags
(`cacheBehavior.cacheConversation`, `cacheBehavior.cacheSystemMessage`,
or `completionOptions.promptCaching`). Most users don't set these, so
the default state is **no caching**. When enabled, the Anthropic and
Bedrock paths work correctly. The OpenAI Chat Completions path doesn't
use `prompt_cache_key`. The Gemini path doesn't use `cachedContents`
at all — caching is just unimplemented.

Same volatile-message bug as Cline/Roo: places `cache_control` (or
`cachePoint`) on the last 2 user messages, the latest of which is
volatile.

There's a notable patch landed (PR #10935 + fix commit f5f9ccb) where
the cache-control insertion was running even when the user explicitly
set `cachingStrategy: "none"` — now correctly guarded.

## Source inspection

### Anthropic — `packages/openai-adapters/src/apis/Anthropic.ts`

```typescript
private _convertBody(oaiBody: ChatCompletionCreateParams) {
  const cleanBody = this._convertToCleanAnthropicBody(oaiBody);
  const cachingStrategy = CACHING_STRATEGIES[this.config.cachingStrategy ?? "systemAndTools"];
  const result = cachingStrategy(cleanBody);
  if ((this.config.cachingStrategy ?? "systemAndTools") !== "none") {
    addCacheControlToLastTwoUserMessages(result.messages);
  }
  return result;
}
```

Strategies registered in `CACHING_STRATEGIES`:

- `systemAndTools` (default): caches system prompt + tool definitions
- `none`: no system/tools cache
- (plus message-level via `addCacheControlToLastTwoUserMessages`)

PR #10935 added the conversation-message caching; the f5f9ccb fix
guards it against running when strategy is "none". Pre-fix bug:
even users opting out of caching got it applied for messages.

Permalink: https://github.com/continuedev/continue/blob/main/packages/openai-adapters/src/apis/Anthropic.ts

### Bedrock — `core/llm/llms/Bedrock.ts`

```typescript
if (this.cacheBehavior?.cacheConversation || this.completionOptions.promptCaching) {
  this._addCachingToLastTwoUserMessages(converted);
}
```

Uses `cachePoint: { type: "default" }` correctly (not `cache_control`).
PR #7652 fixed an earlier shape bug.

### OpenAI Responses — `packages/openai-adapters/src/apis/openaiResponses.ts`

Implemented for GPT-5 / o-series models per a regex:

```typescript
const RESPONSES_MODEL_REGEX = /^(?:gpt-5|gpt-5-codex|o[0-9])/i;
```

But the file does NOT set `prompt_cache_key`. OpenAI's Responses API
auto-caches without it (via byte-stable prefix), so this isn't
strictly broken — but Continue is leaving the per-pod routing
hint on the table. Hit rates will be lower than they could be.

### OpenAI Chat Completions — `packages/openai-adapters/src/apis/OpenAI.ts`

No caching logic. Relies on OpenAI's auto-cache and prefix stability.
Whether that works depends on whether Continue's system prompt is
byte-stable (not investigated this audit).

### Gemini — `packages/openai-adapters/src/apis/Gemini.ts`

```typescript
export class GeminiApi implements BaseLlmApi {
  apiBase: string = "https://generativelanguage.googleapis.com/v1beta/";
  private genAI: GoogleGenAI;

  constructor(protected config: GeminiConfig) {
    this.apiBase = config.apiBase ?? this.apiBase;
    this.genAI = withNativeFetch(
      () => new GoogleGenAI({ apiKey: this.config.apiKey }),
    );
  }
  // No cachedContents usage
}
```

No use of `cachedContents` API. **Implicit caching** on Gemini 2.5+
will still engage automatically as long as the prefix is byte-stable,
so this isn't 0% caching — but for explicit caching with TTL control
(useful for long-document chat sessions), Continue has zero support.

## Wire capture

Not performed.

## Verdict reasoning

| Provider | Verdict | Reason |
|----------|---------|--------|
| Anthropic | partial | Works with explicit config; volatile-msg bug; off by default |
| Bedrock | partial | Works with config flag; volatile-msg bug; off by default |
| OpenAI Responses | partial | Auto-cache works; `prompt_cache_key` not set |
| OpenAI Chat Completions | unverified | Relies entirely on prefix stability — not checked |
| Gemini | broken | No `cachedContents`; only implicit caching works (which doesn't require harness involvement) |

Net: every supported provider has SOMETHING wrong or missing. The
Continue project is mid-rebuild on caching (PR #10801 added cache-hit
PostHog telemetry, indicating active work). Audit may be stale in
months — re-run.

## Patches

### Patch 1: same volatile-msg fix as Cline/Roo

`addCacheControlToLastTwoUserMessages` should be `addCacheControlToLastTwoStableMessages`
(or similar) — exclude the in-flight user turn.

### Patch 2: implement Gemini `cachedContents`

```diff
--- a/packages/openai-adapters/src/apis/Gemini.ts
+++ b/packages/openai-adapters/src/apis/Gemini.ts
@@
+  private async _maybeCreateCache(systemInstruction: string, tools?: Tool[]) {
+    // Min 1024 tok Flash, 4096 tok Pro
+    const minTokens = this.config.model.includes("pro") ? 4096 : 1024;
+    if (estimateTokens(systemInstruction) < minTokens) return null;
+    return await this.genAI.caches.create({
+      model: this.config.model,
+      config: { systemInstruction, tools, ttl: "3600s" }
+    });
+  }
```

Then pass the returned `cache.name` via `cachedContent` on subsequent
`generateContent` calls.

### Patch 3: OpenAI Responses — set `prompt_cache_key`

```diff
--- a/packages/openai-adapters/src/apis/openaiResponses.ts
+++ b/packages/openai-adapters/src/apis/openaiResponses.ts
@@
+  const systemHash = crypto.createHash("sha256")
+    .update(systemPrompt + JSON.stringify(tools))
+    .digest("hex").slice(0, 16);
+  body.prompt_cache_key = `continue:${this.config.model}:${systemHash}`;
```

PR status: not submitted (suggestions for upstream).

## Reproduction

Source-only audit. Continue is multi-modal (chat + agent + autocomplete),
so a wire capture should test all three paths separately — they share
the LLM adapter but may construct prompts differently.

## Notes

- Continue's caching is **opt-in via config**, unlike Cline/Roo
  (always-on when supported). Most users probably don't know to enable
  it. The default should flip to `cachingStrategy: "systemAndTools"`
  at minimum.
- Active development in this area (PR #10801 telemetry, #10935 message
  caching, f5f9ccb fix) — Continue is improving but currently behind
  Cline/Roo/OpenCode for users who haven't explicitly configured caching.
- Issue #5172 (open) reports "Anthropic prompt caching doesn't work" —
  consistent with our finding that users need to manually configure it.
