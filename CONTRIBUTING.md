# Contributing

## Submitting a harness audit

PRs must include:

1. The audit file at `audits/<slug>.md` filled in per the template.
2. A captured request body at `examples/<slug>-req.json` (sanitized of
   secrets and PII).
3. The `check_cache.py` report output at `examples/<slug>-report.json`.
4. The harness's commit SHA at audit time, in the audit file's front
   matter.

PRs without reproducible evidence will be closed. We do not grade on
vibes.

## Adding a new harness

1. Copy `audits/_TEMPLATE.md` to `audits/<slug>.md`.
2. Add the slug to `docs/scorecard.md` (or whichever index file exists).
3. Follow the audit methodology in `docs/verification.md`.

## Doc edits

Doc PRs should cite the provider's official documentation page (with a
permalink to the dated version, when possible). Speculation is fine
inline but must be labeled "unverified."

## Re-audits

Harnesses change. If you re-audit, append (don't overwrite) a new
dated section to the existing file:

```markdown
## 2026-08-15 re-audit

| Field | Value |
|-------|-------|
| Audited commit | <new SHA> |
| ...
```

Keep the previous audit visible so we have a history.

## Style

- Terse. Technical. No marketing voice.
- No emoji unless quoting source.
- Sentence-case headings.
- Code blocks for everything verbatim from source/wire.
- Permalinks > URLs.

## Code

- `tools/` is Python 3 with stdlib only. Don't add deps.
- Shell scripts use `bash` and `set -euo pipefail`.
- All scripts must be runnable from any cwd.

## License

By contributing you agree audit content is released under CC-BY-4.0 and
code under MIT (the repo's existing licenses).
