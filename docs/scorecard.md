# Scorecard

> Status: SCAFFOLD. To be filled in as harness audits complete. Sort by
> measured hit rate descending once we have real numbers.

| Harness | Provider | cache_control set? | Breakpoints | Measured hit rate | Optimal? | Patch | Audit |
|---------|----------|--------------------|-------------|-------------------|----------|-------|-------|
| Claude Code | Anthropic | TODO | TODO | TODO | TODO | n/a | [`../harnesses/claude-code.md`](../harnesses/claude-code.md) |
| Cline | Anthropic | TODO | TODO | TODO | TODO | TODO | [`../harnesses/cline.md`](../harnesses/cline.md) |
| Roo Code | Anthropic | TODO | TODO | TODO | TODO | TODO | [`../harnesses/roo-code.md`](../harnesses/roo-code.md) |
| Aider | Anthropic | TODO | TODO | TODO | TODO | TODO | [`../harnesses/aider.md`](../harnesses/aider.md) |
| Aider | OpenAI | n/a (automatic) | n/a | TODO | TODO | TODO | [`../harnesses/aider.md`](../harnesses/aider.md) |
| Continue | Anthropic | TODO | TODO | TODO | TODO | TODO | [`../harnesses/continue.md`](../harnesses/continue.md) |
| OpenCode | Anthropic | TODO | TODO | TODO | TODO | TODO | [`../harnesses/opencode.md`](../harnesses/opencode.md) |
| Crush | TODO | TODO | TODO | TODO | TODO | TODO | [`../harnesses/crush.md`](../harnesses/crush.md) |
| Codex CLI | OpenAI | n/a (automatic) | n/a | TODO | TODO | TODO | [`../harnesses/codex-cli.md`](../harnesses/codex-cli.md) |
| Goose | TODO | TODO | TODO | TODO | TODO | TODO | [`../harnesses/goose.md`](../harnesses/goose.md) |
| aichat | TODO | TODO | TODO | TODO | TODO | TODO | [`../harnesses/aichat.md`](../harnesses/aichat.md) |
| gptme | TODO | TODO | TODO | TODO | TODO | TODO | [`../harnesses/gptme.md`](../harnesses/gptme.md) |
| avante.nvim | TODO | TODO | TODO | TODO | TODO | TODO | [`../harnesses/avante-nvim.md`](../harnesses/avante-nvim.md) |
| Kilo Code | TODO | TODO | TODO | TODO | TODO | TODO | [`../harnesses/kilo-code.md`](../harnesses/kilo-code.md) |

## Reading this table

- **cache_control set?** — does the harness send Anthropic's `cache_control`
  field (or `cachePoint` on Bedrock) at all? Yes/No/N/A.
- **Breakpoints** — count of `cache_control` markers per typical request.
- **Measured hit rate** — `cache_read / (cache_read + cache_creation + input)`
  on the second of two identical agent turns, captured on wire.
- **Optimal?** — Yes if hit rate ≥ 80% on a steady-state loop, No otherwise.
- **Patch** — link to a proposed fix in this repo or upstream PR.

## Provider-specific notes

- **OpenAI** harnesses are graded purely on prefix stability and
  measured `cached_tokens` ratio. No `cache_control` field exists.
- **Gemini** harnesses are graded on both implicit hit rate and (if
  applicable) correct use of explicit `cachedContents`.
