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

- [x] `audits/claude-code.md` — inferred; closed source
- [x] `audits/cline.md` — partial; volatile-msg bug; OpenAI broken
- [x] `audits/roo-code.md` — partial; same Anthropic bug; Bedrock custom ARN gap
- [x] `audits/aider.md` — working with `--cache-prompts`; 1h TTL gap
- [x] `audits/opencode.md` — working on Anthropic; OpenAI-compatible→Anthropic broken
- [x] `audits/codex-cli.md` — working; reference implementation for OpenAI
- [x] `audits/continue.md` — partial; opt-in; Gemini missing
- [x] `audits/hermes-nous.md` — working; source + xAI wire evidence (`prompt_cache_key`, `x-grok-conv-id`, cached tokens)
- [x] `audits/codex-desktop.md` — working inferred; ChatGPT Codex backend cache-scope headers captured
- [x] `audits/devin-cli.md` — unverified; raw CLI captured as opaque Codeium/Devin Connect protobuf
- [x] `audits/windsurf-cascade.md` — unverified; closed desktop, no one-shot model capture
- [x] `audits/antigravity.md` — unverified; closed desktop, no model capture
- [x] `audits/grok-cli.md` — unverified; CLI answered but model call did not hit mitmproxy
- [ ] `audits/crush.md`
- [ ] `audits/goose.md`
- [ ] `audits/aichat.md`
- [ ] `audits/gptme.md`
- [ ] `audits/avante-nvim.md`
- [ ] `audits/kilo-code.md`

### Wire-capture re-validation (TODO for any of the above)

Source recon found bugs but didn't measure hit rates. Pending:
- [ ] Cline — confirm volatile-msg bug produces non-zero `cache_creation` every turn
- [ ] Claude Code — capture to confirm inferred breakpoint pattern
- [ ] Aider — verify 4-breakpoint placement and hit rate ≥80%

## Phase 4 — Headline artifact

- [x] `docs/scorecard.md` — 13 harnesses graded per-provider / managed-surface status
- [x] README → expanded 13-harness scorecard summary table added
- [x] Extended capture round — Hermes, Devin, Codex CLI backend, Grok CLI attempts recorded; closed desktop blockers documented

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
  `audits/_TEMPLATE.md` and append it to Phase 3 above.
