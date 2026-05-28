# PROGRESS

> Single source of truth for what's done and what's next. Executing
> agent: update this file as you go (commit alongside the work it
> describes). See `EXECUTION_PLAN.md` for the full plan and ground rules.

## Phase 1 — Reference docs

- [x] `docs/concepts/anthropic.md` — verified 2026-05-27; pricing table added; worked example from shim
- [x] `docs/concepts/openai.md` — verified 2026-05-27; `prompt_cache_key` Responses API trick added
- [x] `docs/concepts/gemini.md` — verified 2026-05-27; 3.5/3.0/2.5 Pro/Flash min tokens corrected
- [ ] `docs/concepts/bedrock.md` — verify model support matrix + stamp date
- [ ] `docs/concepts/vertex.md` — verify region availability + stamp date
- [x] `docs/gotchas.md` — added #9b (UUID cache_key footgun)
- [x] `docs/verification.md` — initial pass complete
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

- [x] `harnesses/claude-code.md` — inferred; closed source
- [x] `harnesses/cline.md` — partial; volatile-msg bug; OpenAI broken
- [x] `harnesses/roo-code.md` — partial; same Anthropic bug; Bedrock custom ARN gap
- [x] `harnesses/aider.md` — working with `--cache-prompts`; 1h TTL gap
- [x] `harnesses/opencode.md` — working on Anthropic; OpenAI-compatible→Anthropic broken
- [x] `harnesses/codex-cli.md` — working; reference implementation for OpenAI
- [x] `harnesses/continue.md` — partial; opt-in; Gemini missing
- [ ] `harnesses/crush.md`
- [ ] `harnesses/goose.md`
- [ ] `harnesses/aichat.md`
- [ ] `harnesses/gptme.md`
- [ ] `harnesses/avante-nvim.md`
- [ ] `harnesses/kilo-code.md`

### Wire-capture re-validation (TODO for any of the above)

Source recon found bugs but didn't measure hit rates. Pending:
- [ ] Cline — confirm volatile-msg bug produces non-zero `cache_creation` every turn
- [ ] Claude Code — capture to confirm inferred breakpoint pattern
- [ ] Aider — verify 4-breakpoint placement and hit rate ≥80%

## Phase 4 — Headline artifact

- [x] `docs/scorecard.md` — 7 harnesses graded per-provider
- [x] README → scorecard summary table added

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
