# Validation Contract — Repo Modernization (Aug 2026 wave)

Scope: bring prompt-cache-skills up to current (Aug 2026) provider APIs and
harness state; fix portability; refresh evidence; keep CI green.

## VAL- assertions

- VAL-BASE-01: `./.venv/Scripts/python.exe -m pytest tests/ -q` exits 0 (34+ tests)  [executable]
- VAL-BASE-02: `python tools/check_docs_consistency.py` exits 0                      [executable]
- VAL-BASE-03: `python -m py_compile tools/*.py` exits 0                             [executable]
- VAL-BASE-04: every count claim in README/scorecard matches reality after the wave  [executable via check_docs_consistency.py]
- VAL-TEST-01: pytest suite passes on Windows AND macOS semantics (no open-handle unlink; pathlib-safe paths) [executable on Windows here; macOS by CI]
- VAL-TOOL-01: `check_cache.py` supports deepseek-style top-level `prompt_cache_hit_tokens` AND nested `prompt_tokens_details.cached_tokens` — unit-tested with synthetic responses, 0 live calls [executable]
- VAL-TOOL-02: `check_cache.py --provider openrouter` path exists + unit-tested [executable]
- VAL-TOOL-03: `check_cache.py --sleep` mode used for TTL probe guidance documented [executable: grep docs]
- VAL-DOCS-01: `docs/concepts/*.md` carry "Last verified: 2026-08-XX" stamps only where re-verified this wave; stale claims marked [executable: grep stamps + reviewer]
- VAL-DOCS-02: gotchas #10/#11 Gemini minimums match current model line (2.5/3.x) with source URLs [judgment: reviewer reads diff + cited URLs]
- VAL-DOCS-03: README "What you actually save" table + headline findings updated to current harness state, no stale May-2026 claims presented as current [judgment]
- VAL-SKILL-01: every skill whose target bug is now FIXED upstream is either updated (with new permalink + status) or marked FIXED-UPSTREAM with evidence link [executable: grep status field + reviewer]
- VAL-SKILL-02: new skills added for confirmed still-open bugs follow `skills/_TEMPLATE/SKILL.md` frontmatter (name/target_harness/target_files/target_commit/estimated_savings) [executable: grep frontmatter]
- VAL-SKILL-03: `skills/README.md` index table matches actual skills/ directory (count + names) [executable: check_docs_consistency.py extension]
- VAL-SAFE-01: no API keys/tokens in any new file (gitleaks pattern grep) [executable: grep]
- VAL-SAFE-02: no fabricated wire captures — any new "verified" claim cites a URL or is labeled UNVERIFIED/source-recon [judgment: reviewer]
- VAL-CI-01: `.github/workflows/ci.yml` valid YAML, jobs reference files that exist [executable: python yaml parse]

## features.json (informal mapping)

| Feature | VAL- IDs |
|---|---|
| Green baseline incl. Windows | VAL-BASE-01..03, VAL-TEST-01 |
| check_cache.py provider coverage update | VAL-TOOL-01, VAL-TOOL-02 |
| Concept docs refresh | VAL-DOCS-01, VAL-DOCS-02 |
| README/scorecard refresh | VAL-DOCS-03, VAL-BASE-04 |
| Skill status refresh + new skills | VAL-SKILL-01..03 |
| Safety | VAL-SAFE-01, VAL-SAFE-02 |
| CI sanity | VAL-CI-01 |

## expect(n)

- pytest: expect ≥34 assertions passing (baseline 34; new tests may raise it)
- check_docs_consistency.py: expect exit 0 after any README/scorecard edit
- Every new skill dir: expect exactly 1 SKILL.md with the 5 required frontmatter keys

## Done definition

All executable VAL- rows evidenced in the final report with real exit codes.
Judgment rows carry a named reviewer artifact. Verdict: DONE / GATE-FAIL /
BLOCKED (with unblock). No PASS with zero checks.

## Out of scope this wave

- Pushing to GitHub (needs Rob's explicit GO — machine hard rule).
- Live wire captures against metered providers (quota law — static/unit tests only).
- Upstream PRs to harnesses (Phase D; separate decision).
