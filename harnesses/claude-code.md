# Claude Code (Anthropic official)

> Status: STUB — awaiting audit.

| Field | Value |
|-------|-------|
| Repo | `anthropics/claude-code` |
| Audited commit | TODO |
| Audit date | TODO |
| Auditor | TODO |
| Provider tested | anthropic |
| Model tested | claude-3-7-sonnet-20250219 or claude-sonnet-4 (current) |
| Verdict | TODO |

## Why this is the reference

Claude Code is Anthropic's own first-party agent CLI. It is the reference
implementation for "how to use Anthropic prompt caching correctly in an
agent loop." Audit it first; treat its breakpoint pattern as the gold
standard against which we compare third-party harnesses.

## Hypothesis (pre-audit)

Should set 4 breakpoints in roughly this pattern:

1. System prompt
2. Tool definitions
3. Last stable assistant turn
4. Current user turn (for retry)

Should use 5min default TTL (1h would be wasteful — agent loops have
tight inter-turn timing).

Should report ≥80% hit rate on a steady-state edit-test-fix loop.

## Source inspection

TODO. Claude Code is partially open-source; check what's available
under `anthropics/claude-code` and supplement with wire capture.

## Wire capture

TODO. Easy to capture: set `ANTHROPIC_BASE_URL=http://127.0.0.1:8090`
(or use `HTTPS_PROXY`) and route through mitmdump.

## Verdict

TODO.

## Reproduction

TODO.
