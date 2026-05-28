# skills/

Each subdirectory is a self-contained `SKILL.md` that an AI coding
agent (Claude Code, Codex, Cline, Cursor, Devin, etc.) can read and
apply on its own.

## Format

Every skill follows the same shape:

- **Target**: which harness/file/lines this applies to
- **Symptom**: what's broken right now
- **Fix**: a diff or imperative steps to apply
- **Verify**: how to confirm the fix landed and caching now works

Skills are atomic. One bug, one fix. If a harness has 3 bugs there are
3 skills for it.

## How to point your agent at this

```
Read https://github.com/OnlyTerp/prompt-cache-skills and apply every
skill in skills/ that matches the harnesses I use. Verify each fix
per its own SKILL.md.
```

That's it. The agent does the rest.

## Index

| Skill | Harness | What it fixes | Estimated savings |
|-------|---------|---------------|-------------------|
| [cline-fix-volatile-msg](cline-fix-volatile-msg/SKILL.md) | Cline | Burns 1 of 3 Anthropic cache breakpoints every turn on the volatile current user message | ~30% wasted cache write premium per turn |
| [cline-openai-cache-key](cline-openai-cache-key/SKILL.md) | Cline | OpenAI native provider sends no `prompt_cache_key` — 0% cache hit | 50-90% input discount on OpenAI calls |
| [cline-pin-timestamp](cline-pin-timestamp/SKILL.md) | Cline | System-prompt timestamp may invalidate cache | Restores system-prompt cache reads |
| [roo-fix-volatile-msg](roo-fix-volatile-msg/SKILL.md) | Roo Code | Same volatile-msg bug as Cline | Same as Cline fix |
| [roo-bedrock-custom-arn](roo-bedrock-custom-arn/SKILL.md) | Roo Code | Bedrock custom ARN silently disables caching (#11983) | Enables Bedrock caching for custom ARNs |
| [continue-fix-volatile-msg](continue-fix-volatile-msg/SKILL.md) | Continue | Same volatile-msg bug as Cline / Roo | Same as Cline fix |
| [continue-enable-defaults](continue-enable-defaults/SKILL.md) | Continue | Caching is opt-in by default; most users never enable it | 90% discount for every user who hasn't manually configured it |
| [continue-gemini-explicit](continue-gemini-explicit/SKILL.md) | Continue | Gemini `cachedContents` API completely unimplemented | Enables explicit Gemini caching |
| [opencode-detect-openai-compat](opencode-detect-openai-compat/SKILL.md) | OpenCode | OpenAI-compatible proxies routing to Anthropic send wrong cache shape (#25984, #26460) | Cache works through LiteLLM/Bifrost/MiMo |
| [opencode-bedrock-doc-blocks](opencode-bedrock-doc-blocks/SKILL.md) | OpenCode | Bedrock cachePoint on DocumentBlock messages produces hard error (#17300) | Restores Bedrock caching for doc-attachment sessions |
| [opencode-mistral-cache-key](opencode-mistral-cache-key/SKILL.md) | OpenCode | No `prompt_cache_key` set for Mistral (#27556) | Enables Mistral cache discount |
| [aider-1h-ttl](aider-1h-ttl/SKILL.md) | Aider | 5min TTL expires during long thinking pauses; keepalive pings are wasteful | Eliminates keepalive cost; survives long gaps |
| [aider-cache-default-on](aider-cache-default-on/SKILL.md) | Aider | `--cache-prompts` is off by default | Default users get 90% discount automatically |

## Adding your own skill

Copy `_TEMPLATE/SKILL.md`, fill in target/symptom/fix/verify. Submit a
PR. Skills are versioned per harness commit; if upstream changes,
update the file refs in your skill.

## License

Skills (prose + diffs) are CC-BY-4.0. Tooling is MIT. See [LICENSE](../LICENSE).
