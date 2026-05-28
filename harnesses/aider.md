# Aider

| Field | Value |
|-------|-------|
| Repo | `Aider-AI/aider` |
| Audited commit | `3ec8ec5a7d695b08a6c24fe6c0c235c8f87df9af` |
| Audit date | 2026-05-27 |
| Auditor | terp (source recon via subagent_explore) |
| Provider tested | Anthropic, OpenAI |
| Verdict | **working** (Anthropic, with flag); **automatic** (OpenAI) |

## Summary

Aider's Anthropic caching is solid. With `--cache-prompts` enabled
(off by default), it sets 4 explicit `cache_control: ephemeral`
breakpoints — system prompt, repo-map, read-only files, chat files —
exactly the canonical placement for an agent loop with long static
context. The repo-map serialization bug that historically broke
caching (issue #1874) is fixed; tie-breaking sort by filename now
keeps the prefix byte-stable across calls when the repo is unchanged.

OpenAI side is automatic — Aider doesn't try to manage `prompt_cache_key`
and lets OpenAI's prefix caching do its thing. No timestamp pollution
in the system prompt, so prefix stability is preserved.

Two real gaps:

1. **1h TTL beta not used.** Aider's chat-style flow can have long
   gaps (read code, think, type prompt), often >5min, which expires
   the cache. There's a workaround (`--cache-keepalive-pings N`) but
   it's billing-inefficient compared to the 1h TTL.
2. **User-message content not cached** (issue #3548). Only assistant
   messages between user turns get `cache_control`, leaving large
   repo-context-bearing user messages re-billed every turn.

## Source inspection

### --cache-prompts flag → API call

Trace:

1. `aider/args.py`: `--cache-prompts` arg parsed, defaults to `False`.
2. `aider/coders/base_coder.py`: `self.cache_prompts = cache_prompts`.
3. `aider/coders/base_coder.py` → `format_messages()`:

   ```python
   def format_messages(self):
       chunks = self.format_chat_chunks()
       if self.cache_prompts and self.main_model.cache_control:
           chunks.add_cache_control_headers()
       return chunks.all_messages()
   ```

4. `aider/coders/chat_chunks.py` → `add_cache_control_headers()` adds
   `cache_control: {"type": "ephemeral"}` to the last message of 4
   chunks: system, repo-map (or read-only files), chat files, current.
5. `aider/sendchat.py` → `litellm.completion(**kwargs)` sends.

### Breakpoint placement

4 breakpoints, exactly Anthropic's max:

1. System prompt (or examples block if present)
2. Read-only files (or repo-map if no read-only files)
3. Chat files
4. Current message

Coverage of the entire stable prefix. This is closer to the documented
"correct" agent-loop layout than any other harness in this audit
(Cline uses 3 with a thrash bug, OpenCode uses 4 with system split,
Aider uses 4 with content-type split).

### Per-model cache support

`aider/models.py` carries a `cache_control: true|false` field per
model. Aider only sends `cache_control` to models that explicitly
declare support. Avoids 400s on models that reject the field.

### TTL

5 minutes default (`{"type": "ephemeral"}`, no `ttl` field). No use of
the `anthropic-beta: extended-cache-ttl-2025-04-11` header. Aider's
keepalive workaround is `--cache-keepalive-pings N`, which sends a
trivial request every 5 minutes to refresh — works but wasteful.

### Repo-map determinism — fixed

Issue #1874 was a real bug: items with identical rank were sorted
non-deterministically (Python dict iteration order pre-3.7-style, or
heap tie-break randomness), causing the repo-map text to differ across
calls even when no files had changed. Fix landed: tie-break by
filename. `aider/repomap.py` line ~422.

### OpenAI

No explicit caching logic. Maintainer (Paul Gauthier) statement in
issue #1958: "OpenAI's prompt caching is transparent and automatic,
aider couldn't even turn it off, as far as I know."

Verified by inspection: system prompt construction does not inject
date/time/session ID. Prefix stability preserved.

### Vertex AI

Issue #2961: header `prompt-caching-2024-07-31` rejected by Vertex AI
for some Claude models. Workaround documented (custom model settings
with `cache_control: true` override). Not auto-handled.

## Wire capture

Not performed. The audit relies on source inspection + Aider's
documented caching docs (https://aider.chat/docs/usage/caching.html)
which describe the same behavior. A wire capture would confirm hit
rates but wouldn't change the verdict for Anthropic.

## Verdict reasoning

**Working.** Aider implements the canonical 4-breakpoint pattern,
keeps the repo-map deterministic, and respects per-model support
flags. Gaps are 1h TTL adoption and user-message caching (issue
#3548) — both quality-of-life improvements, not correctness bugs.

For OpenAI: **automatic** is the right verdict. Aider does nothing
explicit and doesn't need to.

## Patches

### Patch 1 (small UX win): adopt 1h TTL beta behind config flag

```diff
--- a/aider/coders/chat_chunks.py
+++ b/aider/coders/chat_chunks.py
@@
-    def add_cache_control(self, msg):
-        msg["cache_control"] = {"type": "ephemeral"}
+    def add_cache_control(self, msg, ttl_1h: bool = False):
+        if ttl_1h:
+            msg["cache_control"] = {"type": "ephemeral", "ttl": "1h"}
+        else:
+            msg["cache_control"] = {"type": "ephemeral"}
```

Plus thread an `--extended-cache-ttl` flag through args.py, and add
the `anthropic-beta: extended-cache-ttl-2025-04-11` header when active.
Worthwhile for chat-style sessions with long thinking gaps; avoids the
keepalive ping waste.

### Patch 2 (issue #3548): cache user-msg content too

The current pattern caches up to and including the assistant turn
after each user message, but not the user message containing repo
context itself. For sessions where the same `/add` set persists, the
user message containing those file contents could carry its own
breakpoint.

This consumes a breakpoint, so it'd need a strategy: either replace
one of the existing 4, or only apply when files are pinned.

PR status: not submitted (suggestions for upstream).

## Reproduction

Source-only audit. To verify on wire:

```bash
HTTPS_PROXY=http://127.0.0.1:8090 \
  aider --cache-prompts --no-stream --model claude-3-7-sonnet-20250219
# enter any small prompt twice in a row
# inspect captured requests: cache_control should appear on 4 blocks
# inspect responses: turn-2 cache_read_input_tokens should be large
```

## Notes

- Aider explicitly exposes `--no-stream` to surface cache stats in the
  UI. Cache implementation works with `--stream` too, just not visible.
- `--cache-prompts` is OFF by default — users have to opt in. Worth
  flipping the default for supported models; for the median user, 90%
  discount on cache reads is a clear win.
- Open issue #4676 likely a UX/visibility issue, not a real cache failure.
