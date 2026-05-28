# OpenCode

| Field | Value |
|-------|-------|
| Repo | `sst/opencode` |
| Audited commit | `a9ef5a0fae7d390ed59ac7da087911deddd68bb9` (branch `dev`) |
| Audit date | 2026-05-27 |
| Auditor | terp (source recon via subagent_explore) |
| Provider tested | Anthropic, OpenAI, OpenRouter, Bedrock, Vertex (Anthropic), OpenAI-compatible, Mistral |
| Verdict | **working** (Anthropic/OpenRouter/Vertex); **partial** (Bedrock); **broken** (OpenAI-compatible proxies, Mistral) |

## Summary

OpenCode has the most sophisticated caching implementation in this
audit. It splits the system prompt into two messages — one stable
(provider prompt + global AGENTS.md + tools), one dynamic (env info +
project AGENTS.md + user.system) — so the stable side can be cached
independently of the per-project drift. Both halves get their own
`cache_control` breakpoint, plus two more on the last two non-system
messages. That's 4 breakpoints, exactly Anthropic's max.

The OpenAI-compatible adapter is a problem: when routing OpenAI-shaped
requests through proxies like LiteLLM/Bifrost to Anthropic/Bedrock
backends, OpenCode sends `promptCacheKey` (OpenAI-shape) instead of
`cache_control` on message blocks (Anthropic-shape). The proxy passes
the OpenAI-shape field, which the Anthropic backend ignores. Result:
0% cache hit on these routes. Same root cause kills Mistral caching.

1h TTL is supported behind `OPENCODE_EXPERIMENTAL_CACHE_1H_TTL=1`.

## Source inspection

### Anthropic — `packages/opencode/src/provider/transform.ts`

`applyCaching()` function structure:

```typescript
function applyCaching(msgs: ModelMessage[], model: Provider.Model): ModelMessage[] {
  // Apply to first 2 system messages
  const systemMsgs = msgs.filter(m => m.role === "system").slice(0, 2)
  systemMsgs.forEach(msg => {
    msg.providerOptions = {
      anthropic: { cacheControl: { type: "ephemeral" } },
      openrouter: { cacheControl: { type: "ephemeral" } },
      bedrock: { cachePoint: { type: "default" } },
    }
  })
  // Apply to last 2 non-system messages
  const nonSystemMsgs = msgs.filter(m => m.role !== "system").slice(-2)
  nonSystemMsgs.forEach(msg => {
    msg.providerOptions = { /* same */ }
  })
}
```

4 breakpoints used:

1. System block 1 (static): provider prompt + global AGENTS.md (~17k
   tokens total including tools). Reused across all repos.
2. System block 2 (dynamic): env info + project AGENTS.md +
   user.system. Repo-specific.
3. Second-to-last non-system message (stable assistant turn).
4. Last non-system message (current user turn — also a volatile-thrash
   case like Cline, but less impactful because the larger static
   prefix dominates).

### System-prompt split — `packages/opencode/src/session/llm.ts`

PR #14203 introduced this. Before the split, OpenCode merged
provider prompt + env + AGENTS.md into one string, so the dynamic
parts (env info, working dir) invalidated the whole system cache
on every session. PR #20109 further fixed `user.system` to stay in
the dynamic half rather than getting merged into the static half.

### Tools

Cached as part of the static system prefix (block 1). Tool definitions
total ~12k tokens and are byte-stable across sessions, so this is the
biggest single source of cache savings.

### 1h TTL beta

Supported, gated:

- `OPENCODE_EXPERIMENTAL_CACHE_1H_TTL=1`
- Plus `OPENCODE_EXPERIMENTAL_CACHE_STABILIZATION=1` for related
  cache-life work (freezes date, caches instruction-file reads for
  process lifetime).

### OpenAI — `ProviderTransform.options()`

Auto-sets `promptCacheKey` on every Responses API request. Key source
not verified at this audit; recommend confirming it's stable per
session (not per-request UUID).

### OpenRouter

Per PR #16850, uses content-level `cache_control: ephemeral` with
`ttl: "1h"` when the 1h flag is enabled. Top-level `prompt_cache_ttl`
on OpenRouter is silently ignored (issue #16848), so content-level
placement matters.

### Bedrock — partial

Message-level `cachePoint: { type: "default" }` works for normal text
messages. Fails on `DocumentBlock`-containing messages (issue #17300):
the cachePoint lands on content with no cacheable text, producing a
"nothing available to cache" error.

### OpenAI-compatible (LiteLLM, Bifrost, etc.) — broken

Detection logic in `applyCaching()`:

```typescript
if (
  model.providerID === "anthropic" ||
  model.api.id.includes("anthropic") ||
  model.api.id.includes("claude") ||
  model.api.npm === "@ai-sdk/anthropic"
) {
  // Apply Anthropic-style caching
}
```

Doesn't catch `@ai-sdk/openai-compatible` providers routing to
Anthropic-backed endpoints. Result: those routes get OpenAI-shape
`promptCacheKey` (which Anthropic ignores) instead of `cache_control`
on blocks (which Anthropic uses). Issues #25984 (Bedrock via Bifrost),
#26460 (Xiaomi MiMo).

### Vertex (Anthropic) — working

PR #20266 added explicit detection
(`model.api.npm === "@ai-sdk/google-vertex/anthropic"`). Cache write
tokens extracted from `metadata.vertex.cacheCreationInputTokens` for
accurate stats.

### Mistral — missing

Mistral's documented prompt caching (10% pricing on cached tokens) is
not wired through. Issue #27556.

## Wire capture

Not performed. Recommended targets: Anthropic direct (verify all 4
breakpoints fire) and OpenAI-compatible→Bedrock (confirm the broken
state to motivate the upstream fix).

## Verdict reasoning

| Provider | Verdict | Reason |
|----------|---------|--------|
| Anthropic | working | Full 4-breakpoint pattern with system split; PR #20109 fixed user.system handling |
| OpenRouter | working | Content-level `cache_control` correctly applied; 1h TTL via flag |
| Vertex (Anthropic) | working | PR #20266 explicit support |
| Bedrock | partial | Works for text; DocumentBlock case broken (#17300) |
| OpenAI native | working | `promptCacheKey` auto-set (verify stability) |
| OpenAI-compatible → Anthropic | broken | Wrong cache shape sent; #25984, #26460 |
| Mistral | missing | No `prompt_cache_key`; #27556 |

## Patches

### Patch 1: fix OpenAI-compatible → Anthropic detection (#25984, #26460)

```diff
--- a/packages/opencode/src/provider/transform.ts
+++ b/packages/opencode/src/provider/transform.ts
@@ function applyCaching(...)
   if (
     model.providerID === "anthropic" ||
     model.api.id.includes("anthropic") ||
     model.api.id.includes("claude") ||
-    model.api.npm === "@ai-sdk/anthropic"
+    model.api.npm === "@ai-sdk/anthropic" ||
+    // OpenAI-compatible proxies (LiteLLM, Bifrost, etc.) routing to Anthropic
+    (model.api.npm === "@ai-sdk/openai-compatible" &&
+     (model.api.id.includes("claude") || model.api.id.includes("anthropic"))) ||
+    // MiniMax, Xiaomi MiMo, etc. are Anthropic-shaped
+    model.api.id.startsWith("minimax/") ||
+    model.api.id.includes("mimo")
   ) {
     // Apply Anthropic-style caching
   }
```

### Patch 2: Mistral support (#27556)

```diff
--- a/packages/opencode/src/provider/transform.ts
+++ b/packages/opencode/src/provider/transform.ts
@@ ProviderTransform.options()
+  if (model.providerID === "mistral") {
+    result["prompt_cache_key"] = input.sessionID
+  }
```

### Patch 3: Bedrock DocumentBlock guard (#17300)

Detect messages containing `DocumentBlock` and skip placing
`cachePoint` on them; fall through to the next-most-stable
non-document message.

PR status: not submitted (suggestions for upstream).

## Reproduction

Source-only audit. To verify on wire:

```bash
# Test Anthropic 4-breakpoint pattern
HTTPS_PROXY=http://127.0.0.1:8090 OPENCODE_EXPERIMENTAL_CACHE_1H_TTL=1 \
  opencode "list files in this directory"
# Run twice; inspect captures for system split + 4 cache_control markers
```

## Notes

- OpenCode's system split is a pattern other harnesses should adopt
  (Cline, Roo). It's the cleanest way to keep tools+global-config in a
  long-lived cache while per-repo context can drift independently.
- The detection logic is the recurring weakness here. Cline/Roo have
  similar fragility (string-matching model IDs). A canonical
  "this-route-is-Anthropic-shaped" predicate would fix multiple bugs.
- Active PR/issue activity around caching — repo is being maintained.
