## What this PR does

<!-- One-line summary. -->

## Type

- [ ] New skill (drop-in fix for a harness)
- [ ] New harness audit
- [ ] Audit correction (existing audit is wrong or stale)
- [ ] Docs / reference (concepts, gotchas, verification)
- [ ] Tooling (`tools/`)

## Evidence

For new skills and audits, this section is required.

- Harness commit SHA examined: `<sha>`
- Target file(s):
- Symptom — what's broken before this PR (cite line:column):
- Fix — what changes (diff already in the PR):
- Verification — captured `usage` block before and after applying:

  ```jsonc
  // before:
  "usage": { ... }
  // after:
  "usage": { ... }
  ```

- Captured request body in `examples/<slug>-req.json` (sanitized).
- `tools/check_cache.py` output in `examples/<slug>-report.json`.

PRs without verification evidence will be closed without merge. See
[`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Checklist

- [ ] Title is in the form `skill: <slug>` or `audit: <harness>` or
      `docs: <area>`.
- [ ] One change per PR — no batched skills.
- [ ] `gitleaks dir .` is clean for any new files.
- [ ] Markdown renders correctly (preview the PR diff).
- [ ] Linked issues / upstream tracker entries in description.

## Affected harnesses / providers

<!-- e.g. Cline + Anthropic; Zoo Code + Bedrock; Continue + Gemini -->
