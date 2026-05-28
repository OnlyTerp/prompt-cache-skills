# Cline

> Status: STUB — awaiting audit.

| Field | Value |
|-------|-------|
| Repo | `cline/cline` |
| Audited commit | TODO |
| Audit date | TODO |
| Auditor | TODO |
| Provider tested | anthropic (primary) — also test bedrock if maintained |
| Model tested | TODO |
| Verdict | TODO |

## Why this is high priority

Most-used OSS agent harness. Even a 10% improvement in cache hit rate
translates to large absolute dollar savings across the userbase. Has
historically had open issues around caching (search the repo's Issues
for "cache_control", "prompt cache", "cached_tokens").

## Hypothesis (pre-audit)

Suspected partial: likely sets `cache_control` on system prompt but
may miss the assistant-turn breakpoint, leaving 50%+ of the prefix
re-billed every turn.

## Source inspection

Starting points to grep:

```bash
rg -n 'cache_control' src/api/providers/
rg -n 'cacheControl|cachePoint' src/api/providers/
rg -n 'ephemeral' src/api/providers/
```

Anthropic provider lives in `src/api/providers/anthropic.ts` historically.
Verify path at audit time.

## Wire capture

`HTTPS_PROXY=http://127.0.0.1:8090` and configure the VS Code extension's
Anthropic base URL override (Cline settings → Anthropic Base URL).

Run two identical small tasks back-to-back ("list files in this repo"
twice in a row) — the second should show high `cache_read_input_tokens`.

## Verdict

TODO.

## Patch

TODO. If suboptimal, draft the diff here and open upstream PR.

## Reproduction

TODO.
