# OpenAI Codex CLI

> Status: STUB — awaiting audit.

| Field | Value |
|-------|-------|
| Repo | `openai/codex` |
| Audited commit | TODO |
| Audit date | TODO |
| Auditor | TODO |
| Provider tested | openai |
| Model tested | TODO |
| Verdict | TODO |

## Notes pre-audit

OpenAI's first-party agent CLI. Since OpenAI prefix caching is automatic
(no `cache_control` knob), the audit reduces to:

1. **Is the prefix byte-stable across turns?** Inspect system prompt
   construction. Look for timestamps, session IDs, randomized fields.
2. **Are tool definitions serialized deterministically?**
3. **What's the measured `cached_tokens` ratio?**

## Source inspection

```bash
rg -n 'system_message|tools\b|build_messages' codex-rs/
rg -n 'cached_tokens|prompt_tokens_details' codex-rs/
```

Codex CLI is partially Rust (`codex-rs/`) plus some TypeScript shell.

## Source / Wire / Verdict / Patch / Reproduction

TODO.
