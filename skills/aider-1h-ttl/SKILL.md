---
name: aider-1h-ttl
description: Aider uses 5min TTL by default and works around long pauses with keepalive pings. Wire up the 1h TTL beta instead.
target_harness: Aider
target_repo: Aider-AI/aider
target_files:
  - aider/coders/chat_chunks.py
  - aider/sendchat.py
  - aider/args.py
target_commit: 3ec8ec5a
estimated_savings: Eliminates --cache-keepalive-pings billing waste; preserves cache across multi-hour thinking pauses
---

# Aider: enable Anthropic 1-hour cache TTL

## Target

`aider/coders/chat_chunks.py`, `aider/sendchat.py`, `aider/args.py` in
`Aider-AI/aider`.

## Symptom

Aider uses the 5-minute default cache TTL. For chat-style sessions
where the user reads code, thinks for 10 minutes, then types — common
flow — the cache expires between turns. The current workaround is
`--cache-keepalive-pings N` which sends a trivial request every 5
minutes to refresh the cache, but you pay for those pings.

Anthropic's `extended-cache-ttl-2025-04-11` beta extends the TTL to
1 hour for a 2x write premium (vs 1.25x for 5min). Break-even is ~4
reads, which any active chat session clears.

## Fix (three parts)

### Part A — accept the flag

```diff
--- a/aider/args.py
+++ b/aider/args.py
@@
+    group.add_argument(
+        "--extended-cache-ttl",
+        action=argparse.BooleanOptionalAction,
+        default=False,
+        help="Use Anthropic's 1-hour cache TTL (beta). "
+             "Costs 2x to write vs 1.25x for default 5min, "
+             "but preserves cache across long thinking pauses. "
+             "Pays for itself after ~4 cache reads.",
+    )
```

### Part B — thread it through the message builder

```diff
--- a/aider/coders/chat_chunks.py
+++ b/aider/coders/chat_chunks.py
@@
-    def add_cache_control(self, msg):
-        msg["cache_control"] = {"type": "ephemeral"}
+    def add_cache_control(self, msg, extended_ttl: bool = False):
+        if extended_ttl:
+            msg["cache_control"] = {"type": "ephemeral", "ttl": "1h"}
+        else:
+            msg["cache_control"] = {"type": "ephemeral"}
@@
-    def add_cache_control_headers(self):
+    def add_cache_control_headers(self, extended_ttl: bool = False):
         for chunk in self.cacheable_chunks():
             last = chunk[-1]
-            self.add_cache_control(last)
+            self.add_cache_control(last, extended_ttl=extended_ttl)
```

### Part C — set the beta header when active

```diff
--- a/aider/sendchat.py
+++ b/aider/sendchat.py
@@
-def send_completion(model_name, messages, ...):
+def send_completion(model_name, messages, *, extended_cache_ttl=False, ...):
@@
     extra_headers = {}
+    if extended_cache_ttl:
+        extra_headers["anthropic-beta"] = "extended-cache-ttl-2025-04-11"
     kwargs = {
         "model": model_name,
         "messages": messages,
+        "extra_headers": extra_headers,
         ...
     }
     return litellm.completion(**kwargs)
```

Wire `args.extended_cache_ttl` from the Coder constructor through
`format_messages()` and `send_completion()`.

## Verify

1. Run with `--cache-prompts --extended-cache-ttl --no-stream`.
2. Capture wire.
3. Request headers should include
   `anthropic-beta: extended-cache-ttl-2025-04-11`.
4. Request body cache_control blocks should be
   `{"type": "ephemeral", "ttl": "1h"}`.
5. Wait 6 minutes. Send another prompt.
6. Response `usage.cache_read_input_tokens` should still cover the
   prefix — proof the cache survived the >5min gap.

## Background

The 1h TTL beta exists for exactly this use case: human-in-the-loop
sessions with long thinking gaps. Trade-off: 2x write cost vs 1.25x.
Worth it whenever the session has ≥4 turns within the hour.

Aider users who already use `--cache-keepalive-pings 5` are paying
for both: keepalive pings AND repeated cache writes. The 1h TTL
beats this on both fronts.

See [docs/concepts/anthropic.md](../../docs/concepts/anthropic.md) §
"TTL" and "Pricing".

Full audit: [audits/aider.md](../../audits/aider.md).
