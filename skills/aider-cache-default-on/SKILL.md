---
name: aider-cache-default-on
description: Aider's --cache-prompts is off by default. Flip it on for supported models.
target_harness: Aider
target_repo: Aider-AI/aider
target_files:
  - aider/args.py
target_commit: 3ec8ec5a
estimated_savings: 90% input discount for every user who didn't know to set the flag
---

# Aider: default --cache-prompts to on for supported models

## Target

`aider/args.py` in `Aider-AI/aider`. The `--cache-prompts` flag is
defined here with `default=False`.

## Symptom

Aider implements the canonical 4-breakpoint Anthropic caching pattern
correctly, but `--cache-prompts` is off by default. Users have to
know to set it (in CLI args, `.aider.conf.yml`, or env var) to get
any cache benefit. The result is that a well-implemented caching path
goes unused by most users.

## Fix

Flip the default to True, with a per-model gate so it only activates
for models that support caching:

```diff
--- a/aider/args.py
+++ b/aider/args.py
@@
-    group.add_argument(
-        "--cache-prompts",
-        action=argparse.BooleanOptionalAction,
-        default=False,
-        help="Enable caching of prompts (default: False)",
-    )
+    group.add_argument(
+        "--cache-prompts",
+        action=argparse.BooleanOptionalAction,
+        default=True,
+        help="Enable caching of prompts on models that support it. "
+             "90%% input-token discount on cache hits. Pays for itself "
+             "after ~3 reads. Disable with --no-cache-prompts.",
+    )
```

The existing per-model `cache_control: true|false` gate in
`aider/models.py` already prevents this from being sent to unsupporting
models, so flipping the default is safe — it's just opt-out instead of
opt-in.

Add a CHANGELOG note.

## Verify

1. Run `aider --model claude-3-7-sonnet-20250219` with NO mention of
   `--cache-prompts` on the command line and no entry in
   `.aider.conf.yml`.
2. Capture wire.
3. Request body should contain `cache_control: {"type": "ephemeral"}`
   on the 4 breakpoint locations (system, repo-map, files, current).
4. Confirm 2nd-turn `usage.cache_read_input_tokens > 0`.

## Background

Defaults matter. The 1.25x cache-write premium is real but small, and
it pays back after the second cache hit — which any multi-turn agent
session clears trivially. A caching system that requires opt-in is a
caching system most users won't use.

Cline / Roo / OpenCode all default-on caching. Aider being default-off
is an anomaly more than a deliberate design choice.

Full audit: [audits/aider.md](../../audits/aider.md).
