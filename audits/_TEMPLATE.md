# <Harness name>

> Copy this template to `<harness-slug>.md` for each new harness audit.

| Field | Value |
|-------|-------|
| Repo | `<github org/repo>` |
| Audited commit | `<SHA>` |
| Audit date | `YYYY-MM-DD` |
| Auditor | `<github handle>` |
| Provider tested | `<anthropic / openai / gemini / bedrock / vertex>` |
| Model tested | `<exact model id>` |
| Verdict | `working / partial / broken / unverified` |

## Summary

One paragraph. What does this harness do with prompt caching, and is it
actually working on the wire?

## Source inspection

What does the source code do?

- Does it set `cache_control` (Anthropic) / use `cachedContents` (Gemini)
  / structure prefixes stably (OpenAI)?
- Where in the code path? Cite file+lines as permalinks.
- How many breakpoints? On what content?
- Does it use 5min or 1h TTL?
- Any config flag that controls caching behavior?

### Relevant code

```text
file: src/providers/anthropic.ts
lines: 142-178
permalink: https://github.com/<org>/<repo>/blob/<SHA>/src/providers/anthropic.ts#L142-L178
```

(Quote the relevant snippet here, kept short.)

## Wire capture

Captured under mitmproxy, two identical agent turns.

### Turn 1 (cold) request highlights

```jsonc
{
  // relevant cache_control fields only, redact secrets
}
```

### Turn 1 response usage

```jsonc
"usage": { ... }
```

### Turn 2 (warm) response usage

```jsonc
"usage": { ... }
```

### Computed hit rate

Hit rate = `cache_read / (cache_read + cache_creation + input_tokens)`

Value: `XX.X%`

## Verdict reasoning

Why we graded it `working / partial / broken / unverified`.

If `partial` or `broken`: what's the specific failure mode? Cite the
gotcha number from [`../docs/gotchas.md`](../docs/gotchas.md) where
applicable.

## Patch (if applicable)

If the harness is suboptimal and we have a fix:

```diff
--- a/src/providers/anthropic.ts
+++ b/src/providers/anthropic.ts
@@ ...
```

PR status: `not submitted / submitted #123 / merged / rejected / stale`

## Reproduction

- Capture file: `examples/<slug>-YYYY-MM-DD.flow`
- Harness invocation: `<exact command line used>`
- Provider auth: `<env var name, redacted>`
- Mitmdump command used: `mitmdump -p 8090 -w examples/<slug>.flow`

## Notes

Anything else worth recording. Maintainer correspondence, related issues,
historical context.
