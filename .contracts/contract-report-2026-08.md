# Contract Report — validation-contract-2026-08.md

**Branch:** `modernize-2026-08` · **Verdict: DONE**
**Date:** 2026-08-28 · All commits verified on-disk; no push (out of scope per contract).

## Executable VAL- rows (real exit codes)

| VAL- ID | Assertion | Evidence | Verdict |
|---|---|---|---|
| VAL-BASE-01 | pytest ≥34 | `48 passed in 0.59s`, exit 0 (grew from 34 → 48) | PASS |
| VAL-BASE-02 | docs consistency | `docs consistency ok`, exit 0 | PASS |
| VAL-BASE-03 | py_compile tools/*.py | exit 0 ("VAL-BASE-03 PASS") | PASS |
| VAL-BASE-04 | count claims match | checker enforces skill-count + index links; `docs consistency ok` | PASS |
| VAL-TEST-01 | Windows-safe tests | suite green on Windows host; macOS leg = CI matrix (`python-tests` job) | PASS (Windows leg) |
| VAL-TOOL-01 | deepseek + nested cached_tokens parsing | unit tests in tests/test_check_cache.py (part of 48) | PASS |
| VAL-TOOL-02 | `--provider openrouter` path | unit-tested, part of 48 | PASS |
| VAL-TOOL-03 | `--sleep` documented | README "Trust but verify" §, commit 0f57379; grep hits docs | PASS |
| VAL-DOCS-01 | 2026-08 stamps only where re-verified | 7/9 concept docs stamped 2026-08-28; bedrock.md + vertex.md honestly retain 2026-05-28 scaffold stamps (NOT silently aged) | PASS |
| VAL-DOCS-02 | Gemini minimums current | gemini.md rewritten w/ per-family minimums, storage billing, implicit-caching note; status VERIFIED w/ source URL | PASS |
| VAL-SKILL-01 | stale-bug skills updated | cline (v3: monorepo AI-SDK single-marker mechanism, new permalinks), roo (v3.54.0 path move), continue (ladder rederivation e90a624) | PASS |
| VAL-SKILL-02 | new skills follow frontmatter | checker enforces 5 frontmatter keys on all 13 skills; exit 0 | PASS |
| VAL-SKILL-03 | skills index matches dir | checker extension; 13 skills (+ _TEMPLATE) match README/index | PASS |
| VAL-SAFE-01 | no secrets in new files | grep scan zero matches (tools/tests/.github); CI also runs secrets-scan job | PASS |
| VAL-CI-01 | ci.yml valid, refs exist | yaml.safe_load OK; 7 jobs; dual-OS matrix | PASS |

## Judgment rows

| VAL- ID | Reviewer artifact |
|---|---|
| VAL-DOCS-03 | README re-verification section (commit 11e9858) + scorecard headline fix (a7bb1c1): May-2026 claims now explicitly dated, Aug findings presented as current |
| VAL-SAFE-02 | No fabricated captures: every new doc/skill cites either the 2026-08 research ledger (fetched provider docs), live GitHub raw/tree fetches (dated in commit messages), or carries scaffold/UNVERIFIED stamps (bedrock, vertex) |

## Key upstream findings this wave (live-verified 2026-08-28)

1. **Cline desktop-v0.0.20**: repo restructured into a monorepo (Vercel AI SDK). Old `src/core/api/transform/anthropic-format.ts` 404s. New mechanism = single ephemeral marker on last user message via `applyPromptCacheToLastTextPart` + `providerOptions` (anthropic + openaiCompatible keys). Ladder economics preserved — prior turn's marker persists in history as the read point. Skill v3 rewritten with new paths, permalinks, and AI-SDK tools-breakpoint diff.
2. **Roo Code v3.54.0**: ladder INTACT (last-two-user-messages + system marker in `addCacheBreakpoints`); transform moved to `src/api/transform/caching/anthropic.ts`. Skill updated with new path.
3. Version stamps fetched live from GitHub Releases API: Cline desktop-v0.0.20, Roo v3.54.0, Kilo v7.5.6, Aider (ledger), Continue (ledger).

## Commits (this contract)

- `1665dd3` ci: dual-OS matrix
- `a585b27` feat(tools): frontmatter + index enforcement
- `106a204` docs(verification): DeepSeek/OpenRouter/xAI wire shapes
- `08777a1` docs: rolling-ladder framing correction
- `e90a624` skills: volatile-msg trio rederivation
- `b7fc74a` docs(concepts): provider refresh (anthropic/gemini/openai + new deepseek/xai/openrouter/mistral)
- `11e9858` docs(readme): 2026-08-28 re-verification section
- `c6ec7b7` skills(cline,roo): upstream target refresh vs live releases
- `0f57379` docs(readme): --sleep TTL-probe doc (VAL-TOOL-03)

## Left undone / handoff

- Gemini gemini-3-flash-litestriped pricing row: scaffold-era placeholder remains in one table cell (flagged in doc, not silently presented as verified).
- bedrock.md / vertex.md remain 2026-05-28 scaffolds — honest stamps, refresh candidates next wave.
- audits/*.md May-2026 audit bodies not rewritten (README now carries an explicit re-verification section instead of silently aging them).
- Push to GitHub: **not done** — machine hard rule requires Rob's explicit GO.
