# prompt-cache-audit

> An opinionated, living audit of how the major LLM agent harnesses (Claude
> Code, Cline, Roo Code, Aider, Continue, OpenCode, Crush, Codex CLI, etc.)
> use — or fail to use — prompt caching from Anthropic, OpenAI, Google
> Gemini, AWS Bedrock, and Vertex.

If you run an agent harness against a frontier model and you aren't getting
`cache_read_input_tokens` back on most turns, you are setting fire to 5-10x
more money than you need to and your agent loop is several hundred ms
slower per turn than it should be.

This repo is two things:

1. **A reference**: a single source of truth for how prompt caching actually
   works on each provider, including the parts the official docs gloss over
   (TTL behavior, breakpoint placement, the cache-write premium, tool-result
   interactions, byte-identity rules on OpenAI, minimum sizes on Gemini).
2. **An audit**: a per-harness scorecard — does this harness send
   `cache_control`, where, with how many breakpoints, and does the provider
   actually return cache hits? With reproducible methodology.

## Why this exists

Anthropic, OpenAI, and Google all ship prompt caching, but in very different
shapes:

- **Anthropic** — explicit, opt-in via `cache_control: {type: "ephemeral"}`
  breakpoints on content blocks. 4 breakpoints max per request. 5-minute
  TTL (default) or 1-hour (beta). 90% read discount, 25% write premium.
- **OpenAI** — automatic, no API surface. Prefix must be ≥1024 tokens
  and byte-identical across calls. ~50% read discount, no write premium.
  Routing is by org+prefix-hash.
- **Google Gemini** — two flavors: implicit (automatic, free) and explicit
  (`CachedContent` objects with minimum sizes and TTL).
- **Bedrock / Vertex** — pass-throughs of the underlying provider's
  semantics, with their own footguns.

Most harnesses were written when none of this existed, or for a single
provider. The result: caching is left on the table everywhere.

## What this repo is NOT

- Not a generic "what is prompt caching" explainer. The Anthropic docs page
  is fine for that. We assume you already know roughly what it is.
- Not a sales pitch for any specific harness. We grade them on a single
  axis: does caching work end-to-end?
- Not a substitute for reading the provider docs. Links in
  [`docs/providers/`](docs/providers/).

## Quick start

If you just want to fix your own harness:

1. Read [`docs/concepts/anthropic.md`](docs/concepts/anthropic.md) (or
   whichever provider you target).
2. Read [`docs/gotchas.md`](docs/gotchas.md). Most caching bugs are in here.
3. Read [`docs/verification.md`](docs/verification.md) — how to actually
   confirm a cache hit, not just hope.
4. Find your harness in [`harnesses/`](harnesses/). If it's red, the file
   tells you exactly which line to patch.

## Status

First wave of audits complete (2026-05-27). 7 harnesses graded:

| Harness | Anthropic | OpenAI | Bedrock | Gemini |
|---------|-----------|--------|---------|--------|
| Claude Code | working* | n/a | n/a | n/a |
| Codex CLI | n/a | **working** | n/a | n/a |
| Aider | working | automatic | n/a | n/a |
| OpenCode | working | working | partial | n/a |
| Roo Code | partial | working | partial | n/a |
| Cline | partial | **broken** | unverified | n/a |
| Continue | partial | partial | partial | broken |

\* inferred from wire shape; source closed.

Full scorecard with file:line citations and proposed upstream patches
in [`docs/scorecard.md`](docs/scorecard.md).

Headline findings:
- A "last 2 user messages" copy-paste bug propagated Cline → Roo →
  Continue, burning a breakpoint on the volatile current turn.
- Cline OpenAI native sends no `prompt_cache_key` and no prefix-stability
  work — users are paying full price.
- Gemini explicit caching (`cachedContents`) is universally unimplemented.
- Codex CLI is the reference for OpenAI-side caching (thread_id cache key,
  preserved across compaction and sub-agents).
- OpenCode's system-prompt split is the best Anthropic pattern in OSS.

Remaining work (Phase 3 for: goose, aichat, gptme, avante.nvim,
kilo-code, crush) tracked in [`PROGRESS.md`](PROGRESS.md). Wire-capture
re-validation tracked in [`EXECUTION_PLAN.md`](EXECUTION_PLAN.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Submissions must include a
reproducible test (request body + response body showing `cache_*` fields)
or they will be closed. We don't grade on vibes.

## License

MIT. Audit reports are CC-BY-4.0.
