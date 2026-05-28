# Aider

> Status: STUB — awaiting audit.

| Field | Value |
|-------|-------|
| Repo | `Aider-AI/aider` |
| Audited commit | TODO |
| Audit date | TODO |
| Auditor | TODO |
| Provider tested | anthropic + openai (test both) |
| Model tested | TODO |
| Verdict | TODO |

## Notes pre-audit

Aider has had explicit prompt-caching support since 2024 (look for
`--cache-prompts` CLI flag). Audit covers:

1. Does the flag actually engage caching on Anthropic?
2. Does it set breakpoints sensibly (system + repo-map + history)?
3. Does it use the 1h TTL beta? (Aider's chat-style flow can have
   long gaps between turns.)
4. On OpenAI, is the prefix kept byte-stable?

## Source inspection

```bash
rg -n 'cache_control|cache_prompts|cache-prompts' aider/
```

`aider/coders/` and `aider/llm.py` (or current equivalents) are
likely sites.

## Hypothesis

Probably `working` on Anthropic with the flag enabled. Uncertain about
OpenAI byte-stability across turns when the repo-map drifts.

## Source / Wire / Verdict / Patch / Reproduction

TODO.
