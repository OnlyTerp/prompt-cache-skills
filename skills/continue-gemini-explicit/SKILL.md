---
name: continue-gemini-explicit
description: Continue's Gemini provider doesn't use the cachedContents API at all. Add explicit caching for sessions over the minimum token threshold.
target_harness: Continue
target_repo: continuedev/continue
target_files:
  - packages/openai-adapters/src/apis/Gemini.ts
target_commit: main (last push 2026-05-26)
estimated_savings: 75% input discount on Gemini Pro / 50% on Flash for sessions above the min-token threshold
---

# Continue: implement Gemini explicit caching

## Target

`packages/openai-adapters/src/apis/Gemini.ts` in `continuedev/continue`.

## Symptom

The Gemini provider class does not use the `cachedContents` API at
all. Gemini 2.5+ has implicit caching that fires automatically for
byte-stable prefixes (free, best-effort), but explicit `cachedContents`
gives guaranteed cost reduction (0.25x input price on Pro) and
controllable TTL. Continue leaves this entire mechanism unused.

Result: long-running Gemini sessions with the same system prompt +
tools (the exact use case caching is for) get only implicit-cache
luck, not the guaranteed 75% discount.

## Fix

Add a `_maybeCreateCache` helper and reuse the cached content across
calls within a session:

```diff
--- a/packages/openai-adapters/src/apis/Gemini.ts
+++ b/packages/openai-adapters/src/apis/Gemini.ts
@@
 export class GeminiApi implements BaseLlmApi {
   apiBase: string = "https://generativelanguage.googleapis.com/v1beta/";
   private genAI: GoogleGenAI;
+  private cacheName: string | null = null;
+  private cacheSystemHash: string | null = null;
@@
+  private estimateTokens(text: string): number {
+    // Conservative ~4 chars/token; fine for threshold gating
+    return Math.ceil(text.length / 4);
+  }
+
+  private async _maybeCreateCache(
+    systemInstruction: string,
+    tools?: any[],
+  ): Promise<string | null> {
+    if (!systemInstruction) return null;
+
+    // Min tokens: 4096 for Pro variants, 1024 for Flash
+    const isPro = this.config.model.toLowerCase().includes("pro");
+    const minTokens = isPro ? 4096 : 1024;
+    if (this.estimateTokens(systemInstruction) < minTokens) return null;
+
+    // Dedupe: only create a cache if system has changed
+    const hash = crypto.createHash("sha256")
+      .update(systemInstruction + JSON.stringify(tools ?? []))
+      .digest("hex").slice(0, 16);
+    if (this.cacheName && this.cacheSystemHash === hash) {
+      return this.cacheName;
+    }
+
+    try {
+      const cache = await this.genAI.caches.create({
+        model: `models/${this.config.model}`,
+        config: {
+          systemInstruction,
+          tools,
+          ttl: "3600s",  // 1 hour
+        },
+      });
+      this.cacheName = cache.name ?? null;
+      this.cacheSystemHash = hash;
+      return this.cacheName;
+    } catch (e) {
+      // Cache creation can fail (e.g. content under min). Fall back
+      // to implicit caching by returning null.
+      return null;
+    }
+  }
```

Then in the `generateContent` call path:

```diff
+    const cachedContent = await this._maybeCreateCache(
+      systemInstruction,
+      tools,
+    );
+
     const response = await this.genAI.models.generateContent({
       model: this.config.model,
       contents: messages,
+      config: cachedContent
+        ? { cachedContent }
+        : undefined,
     });
```

## Verify

1. Start a Continue chat with `gemini-2.5-pro` or `gemini-3-pro-preview`
   and a system prompt over 4096 tokens (or load a big AGENTS.md).
2. Capture wire.
3. First call: should see a `POST /v1beta/cachedContents` create call
   followed by a `generateContent` call referencing the cache name.
4. Second call: only `generateContent`, reusing the same
   `cachedContent` reference.
5. Inspect response `usageMetadata.cachedContentTokenCount` —
   should be > 0 on both calls.

## Background

Gemini has two caching paths: implicit (automatic, free, best-effort)
and explicit (`cachedContents` API, guaranteed discount, configurable
TTL, costs storage per hour). For agent loops with a stable large
system prompt, explicit is strictly better — you trade pennies of
storage for dollars of discount.

Minimums:
- Gemini 3.5 Flash / 2.5 Flash: 1024 tokens
- Gemini 3 Pro Preview / 2.5 Pro: 4096 tokens

Below threshold, `caches.create()` returns 400 — the fallback to
implicit (return null) handles this gracefully.

See [docs/concepts/gemini.md](../../docs/concepts/gemini.md).
Full audit: [audits/continue.md](../../audits/continue.md).
