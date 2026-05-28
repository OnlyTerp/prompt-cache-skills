# PROGRESS

> Single source of truth for what's done and what's next. Executing
> agent: update this file as you go (commit alongside the work it
> describes). See `EXECUTION_PLAN.md` for the full plan and ground rules.

## Phase 1 — Reference docs

- [ ] `docs/concepts/anthropic.md` — verify all numbers + stamp date
- [ ] `docs/concepts/openai.md` — verify all numbers + stamp date
- [ ] `docs/concepts/gemini.md` — verify minimums (Pro/Flash) + stamp date
- [ ] `docs/concepts/bedrock.md` — verify model support matrix + stamp date
- [ ] `docs/concepts/vertex.md` — verify region availability + stamp date
- [ ] `docs/gotchas.md` — read through, add anything missing
- [ ] `docs/verification.md` — read through, add anything missing
- [ ] `docs/providers/README.md` — re-check links return 200

## Phase 2 — Tooling

- [ ] `tools/check_cache.py` — smoke test against Anthropic with a hand-built body
- [ ] `tools/check_cache.py` — smoke test against OpenAI
- [ ] `tools/check_cache.py` — smoke test against Gemini
- [ ] `tools/check_cache.py` — add `--provider bedrock` (boto3)
- [ ] `tools/check_cache.py` — add `--provider vertex` (google-genai)
- [ ] `tools/replay_harness.md` — read through, refine if mitmproxy setup steps differ on contributor's box

## Phase 3 — Harness audits

Priority order:

- [ ] `harnesses/claude-code.md`
- [ ] `harnesses/cline.md`
- [ ] `harnesses/roo-code.md`
- [ ] `harnesses/aider.md` (both Anthropic + OpenAI)
- [ ] `harnesses/opencode.md`
- [ ] `harnesses/codex-cli.md`
- [ ] `harnesses/continue.md`
- [ ] `harnesses/crush.md`
- [ ] `harnesses/goose.md`
- [ ] `harnesses/aichat.md`
- [ ] `harnesses/gptme.md`
- [ ] `harnesses/avante-nvim.md`
- [ ] `harnesses/kilo-code.md`

## Phase 4 — Headline artifact

- [ ] `docs/scorecard.md` — fill in once ≥6 harnesses audited
- [ ] README → add scorecard summary table near the top

## Phase 5 — Upstream PRs

Track per-harness PRs in the audit file's "Patch" section. Summary
here:

| Harness | PR | Status |
|---------|-----|--------|
| _none yet_ | | |

## Notes for the executor

- Always re-verify upstream provider docs at audit time; numbers in
  `docs/concepts/*` may drift between when this scaffold was written
  and when you're auditing.
- Stamp the date at the bottom of each concept doc once verified.
- When auditing a harness, commit the audit file + example req/report
  together. Don't batch multiple harnesses in one commit.
- If you discover a new harness worth auditing, add it as a stub via
  `harnesses/_TEMPLATE.md` and append it to Phase 3 above.
