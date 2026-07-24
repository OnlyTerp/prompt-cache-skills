# EXECUTION_PLAN.md

> Living plan for what's done and what's next on `prompt-cache-skills`.
> See [`PROGRESS.md`](PROGRESS.md) for the granular checklist.

## What this repo is (one line)

Drop-in prompt-caching fixes that any AI agent can read and apply on
its own. Skills, not benchmarks; audits are the proof, not the product.

## Done

- Concept docs verified against live provider docs (Anthropic, OpenAI,
  Gemini) on 2026-05-27 with shim-derived worked examples folded in.
- 13 completed harness audits: the default Claude Desktop Code baseline
  verified from clean Mac cache counters, source-recon audits for Codex
  CLI, Aider, OpenCode, Roo Code (now archived and succeeded by Zoo
  Code), Cline, and Continue, plus extended
  source/wire/local-install audits for Hermes/Nous, Codex Desktop,
  Devin CLI, Windsurf/Cascade, Antigravity, and Grok CLI. Six more
  `audits/` files are queued stubs, not completed audits.
- 13 atomic skills covering the highest-impact fixes across Cline, Zoo Code,
  Continue, OpenCode, Aider. All in [`skills/`](skills/).
- `tools/check_cache.py` — zero-dep wire-verification tool.
- Top-level `AGENTS.md` so an agent dropped into this repo knows what
  to do without prompting.

## Next (in priority order)

### Phase A — proof-out

- [ ] Wire-capture validation of at least 2 skills (recommend
      `cline-fix-volatile-msg` and `cline-openai-cache-key` — highest
      user count, most visible win).
- [ ] Capture `examples/cline-before.flow` and `examples/cline-after.flow`
      showing the `usage` diff. Embed the redacted `usage` blocks in
      the README and the corresponding skills.
- [ ] Tweet-shaped before/after screenshot for share material.

### Phase B — coverage

- [ ] Audit + skills for: goose, crush, kilo-code, gptme, avante.nvim,
      aichat. Use [`audits/_TEMPLATE.md`](audits/_TEMPLATE.md) and
      [`skills/_TEMPLATE/SKILL.md`](skills/_TEMPLATE/SKILL.md).
- [ ] Bedrock + Vertex concept docs — currently SCAFFOLD stubs.

### Phase C — go-live

- [ ] `gh repo create OnlyTerp/prompt-cache-skills --public --description "Drop-in prompt-caching fixes for the LLM agent harness you use. Point your AI coding agent at this repo and it ships the patches."`
- [ ] Push.
- [ ] Set repo topics: `prompt-caching`, `llm-agents`, `claude-code`,
      `codex`, `cline`, `aider`, `opencode`, `anthropic`, `openai`,
      `gemini`, `bedrock`, `ai-skills`.
- [ ] Pin the repo on the user's GitHub profile.

### Phase D — distribution

- [ ] Submit upstream PRs for the highest-impact skills:
  - Cline: volatile-msg fix + OpenAI cache key
  - Zoo Code: volatile-message breakpoint fix
  - Continue: default-on caching
  - OpenCode: openai-compat detection (#25984, #26460)
  - Aider: default-on + 1h TTL flag
- [ ] HN post — title: "Most LLM coding agent harnesses leave 90% off
      your API bill on the table — here's the receipts and the fixes"
- [ ] X/Twitter post — same framing, table of the audited harnesses
      with colored verdicts.
- [ ] Reddit r/LocalLLaMA + r/ChatGPTCoding: shorter, lead with the
      "give this to your agent" framing.

## Ground rules for contributors

- One skill = one bug = one fix. No mega-skills.
- Every skill MUST have a working Verify section. Skills without
  verification get closed.
- Capture evidence in `examples/` for any new skill, even if
  redacted.
- Audits are dated and reference a specific commit SHA. Re-audits
  append, not overwrite.

## What's NOT in scope

- Generic "what is prompt caching" tutorial content (`docs/concepts/`
  is the reference, not the explainer).
- Cloud-provider-specific bills/pricing calculators.
- Closed-source binary harness reverse-engineering beyond wire-level
  observation.
