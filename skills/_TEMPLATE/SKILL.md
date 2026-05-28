---
name: <skill-slug>
description: One-line description of what this fix does and why it matters.
target_harness: <harness-name>
target_repo: <owner>/<repo>
target_files:
  - path/to/file.ts
target_commit: <SHA or branch as of audit>
estimated_savings: <e.g. "30-90% input discount on Anthropic" or "0 → 80% hit rate">
---

# <Skill title>

## Target

Which harness, which file, which lines. Cite a permalink to the
relevant code at the audit commit.

## Symptom

What's broken in the user's current setup. Be concrete:

- Which API call is wrong
- What field is missing/wrong/volatile
- What `usage` field comes back zero or wrong

## Fix

```diff
--- a/path/to/file.ts
+++ b/path/to/file.ts
@@
-  old line
+  new line
```

If the fix is multi-step or conditional, list the steps.

## Verify

After applying, the agent should:

1. Run `<command>` to exercise the code path.
2. Capture the wire (mitmproxy or harness debug log).
3. Confirm `<specific assertion>` — e.g.
   `usage.cache_read_input_tokens > 0` on the second turn.

If the assertion fails, the fix didn't land or there's a second
upstream issue. Stop and report.

## Background

Why this matters in 1-2 sentences. Link to:

- [docs/concepts/<provider>.md] for the API mechanics
- [docs/gotchas.md#N] for the underlying footgun
- [audits/<harness>.md] for the full audit
