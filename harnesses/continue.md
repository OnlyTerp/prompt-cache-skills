# Continue

> Status: STUB — awaiting audit.

| Field | Value |
|-------|-------|
| Repo | `continuedev/continue` |
| Audited commit | TODO |
| Audit date | TODO |
| Auditor | TODO |
| Provider tested | anthropic (primary) — multi-provider; test 2-3 |
| Model tested | TODO |
| Verdict | TODO |

## Notes pre-audit

Continue is multi-provider with a common chat protocol. Caching support
depends on each provider adapter. Audit each adapter separately:

- `core/llm/llms/Anthropic.ts`
- `core/llm/llms/OpenAI.ts`
- `core/llm/llms/Gemini.ts`
- `core/llm/llms/Bedrock.ts`

(Verify paths at audit time.)

## Source / Wire / Verdict / Patch / Reproduction

TODO.
