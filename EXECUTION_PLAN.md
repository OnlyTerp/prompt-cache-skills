# EXECUTION_PLAN.md

> Handoff document. The repo scaffold (this directory) is done. This file
> tells the next agent exactly what to do, in what order, and what "done"
> looks like for each step.

## Context for the executing agent

You are taking over a scaffolded repo that audits prompt-caching support
in major LLM agent harnesses. The scaffolding (directory layout, README,
all doc/harness/tool stubs) is complete. Your job is to fill in real,
verified content. Do not invent facts. Every concrete claim about a
harness must be backed by a citation: a file+line in that harness's
source, or a captured HTTP request/response.

You have full write access to this repo. Treat it as a normal engineering
task: scope work into PRs (logically, even if you commit straight to
main), keep commits atomic, and update the todo file (`PROGRESS.md`) as
you go.

## Ground rules

1. **No fabricated audits.** If you can't verify a harness's behavior by
   reading its source AND by running it against a real provider with
   request/response capture, mark that harness as `unverified` and move on.
2. **Cite everything.** Every claim like "Cline sets cache_control on the
   system prompt" must link to a permalink (commit SHA, line range) at
   the time of audit. Harnesses change fast.
3. **One harness per PR / commit group.** Easy to review, easy to revert
   when a harness changes upstream.
4. **Reproducibility > completeness.** Better to ship 4 high-quality
   audits than 12 sloppy ones.

## Work queue (do in this order)

### Phase 1 — Finalize the reference docs (docs/)

Files are stubbed but most contain `TODO` markers. For each, replace TODOs
with verified content. Cross-check against the official provider docs as
of the date you write (don't trust pre-existing scrapes — providers update
this stuff often).

- [ ] `docs/concepts/anthropic.md` — Anthropic Messages API caching, full
      reference. Cover: `cache_control` shape, 4-breakpoint limit, ephemeral
      vs 1h TTL, cache hierarchy (system → tools → messages), tool_use /
      tool_result placement, beta headers, pricing math (write 1.25x,
      read 0.1x for 5min; write 2x, read 0.1x for 1h).
- [ ] `docs/concepts/openai.md` — OpenAI automatic prefix caching: ≥1024
      token minimum, byte-identical requirement, org-scoped, no header to
      enable, `usage.prompt_tokens_details.cached_tokens` in response.
      Note difference vs Anthropic: no write premium.
- [ ] `docs/concepts/gemini.md` — Gemini implicit caching (free, automatic
      on 2.5 series) vs explicit `cachedContents` API with `ttl` and
      `displayName`. Minimum token sizes per model (32k for Pro, 4k for
      Flash; verify current).
- [ ] `docs/concepts/bedrock.md` — Anthropic-on-Bedrock caching quirks
      (`cachePoint` field shape, model-version availability).
- [ ] `docs/concepts/vertex.md` — Anthropic-on-Vertex and Gemini-on-Vertex.
- [ ] `docs/gotchas.md` — fully written below; just verify and expand.
- [ ] `docs/verification.md` — fully written below; just verify and expand.

### Phase 2 — Build the verification tool (tools/)

- [ ] `tools/check_cache.py` — script that takes a JSON request body for a
      provider, fires it twice (warm + cold), and prints a diff of the
      `cache_*` fields from `usage`. See stub for required behavior.
- [ ] `tools/replay_harness.md` — methodology doc: how to capture a real
      harness's outbound request (mitmproxy recipe), strip it of secrets,
      and re-fire it to verify caching independently of the harness's
      own logging.

### Phase 3 — Per-harness audits (harnesses/)

For each harness in `harnesses/`, fill in the template by doing:

1. Clone the harness at HEAD. Note the commit SHA.
2. `grep -r cache_control` (or equivalent for the harness's language).
3. Read the provider-call code path. Identify:
   - Does it set `cache_control` at all?
   - How many breakpoints?
   - Where (system / tools / last user / etc.)?
   - Does it use the 5-min default or `extended-cache-ttl-2025-04-11`?
   - Does it set `cache_control` on volatile content (would cause cache
     thrash)?
4. Run the harness against the provider with mitmproxy capturing the wire.
5. Verify `cache_read_input_tokens` > 0 on the second turn.
6. Compute the savings (or losses) vs an optimal config.
7. If suboptimal, write the patch as a diff in the harness's audit file.

Harnesses to audit (priority order):

1. **claude-code** — Anthropic's own. Expected: correct. Verify and
   document the pattern as a reference implementation.
2. **cline** — most-used OSS agent harness. Expected: partial.
3. **roo-code** — Cline fork. Expected: inherits Cline's behavior.
4. **aider** — popular CLI. Expected: provider-aware, partial.
5. **continue** — VS Code extension + CLI. Expected: unknown.
6. **opencode** — Anthropic-focused. Expected: should be correct.
7. **crush** — Charmbracelet's TUI. Expected: unknown.
8. **codex-cli** — OpenAI's own. Expected: relies on automatic; verify
   prompt structure keeps the prefix stable.
9. **goose** — Block's harness. Expected: unknown.
10. **aichat** — sigoden's CLI. Expected: probably no caching.
11. **gptme** — Erik Bjäreholt's. Expected: unknown.
12. **avante.nvim** — Neovim agent. Expected: unknown.
13. **kilo-code** — emerging harness. Expected: unknown.

### Phase 4 — Scorecard (docs/scorecard.md)

Once at least 6 harnesses are audited, write `docs/scorecard.md`: a single
table with columns:

| Harness | Provider | cache_control set? | Breakpoints | Hit rate (measured) | Optimal? | Patch available |

Sort by hit rate descending. This is the headline artifact of the repo.

### Phase 5 — PRs upstream

For each harness where you wrote a patch, open the PR upstream and link
it from the harness's audit file. The audit repo should track:
"submitted", "merged", "rejected", "stale".

## What "done" looks like

- All Phase 1 doc TODOs replaced with verified content.
- `tools/check_cache.py` works end-to-end against Anthropic and OpenAI.
- At least 6 harnesses in Phase 3 have completed audits with captured
  request/response evidence.
- `docs/scorecard.md` exists and is sortable / scannable.
- At least 2 upstream patches submitted.

## What NOT to do

- Don't fill in audits by reading the harness's README and guessing.
- Don't accept "the maintainer says it caches" as evidence. Verify on wire.
- Don't conflate "the harness sends cache_control" with "caching works."
  A breakpoint on volatile content is worse than no breakpoint at all.
- Don't lecture in the docs. Terse, technical, sourced.
- Don't add emoji.

## Pointers

- Memory MCP has prior caching notes; `mcp__memory__memory_search` for
  "prompt cache" before starting Phase 1 to pick up Terp's prior context.
- Terp's shim at `~/devin-local-proxy` already implements caching correctly
  for Claude/Codex; it's a worked example but **not** in scope for this
  audit (the audit is about public harnesses, not Terp's shims).
- mitmproxy is already installed and configured on this box; use port
  8443/8444 via `devin-local-proxy` for capture if convenient, or run a
  fresh mitmdump on a different port for clean captures.
