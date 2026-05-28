# prompt-cache-skills

> Drop-in prompt-caching fixes for the LLM agent harness you use.
> Point your AI coding agent at this repo and it ships the patches.

Most popular OSS agent harnesses (Cline, Roo Code, Continue, OpenCode,
Aider) leave **30-90% off your API bill** on the table because their
prompt-caching code is subtly wrong, off-by-default, or just missing
for some providers.

This repo is a set of **drop-in skills** that any AI coding agent
(Claude Code, Codex, Cline, Cursor, Devin, Gemini CLI, OpenCode…) can
read and apply on its own.

You don't read the diffs. You point your agent at this repo and say:

> "Apply every skill in this repo that matches the harnesses I use."

The agent reads each `SKILL.md`, checks if it applies to your setup,
lands the diff, and verifies the fix on the wire. You go from broken
or partial caching to 80-99% cache hit rates without doing the
research yourself.

## What you actually save

Real numbers from the audit underneath this:

| Harness | Bug | Current cost | After fix |
|---------|-----|--------------|-----------|
| Cline (Anthropic) | Caches volatile current user msg every turn | 1 of 3 breakpoints wasted, 30% premium-burn | Full breakpoint utilization, ~99% hit rate |
| Cline (OpenAI) | No `prompt_cache_key`, no cache hits at all | 0% cache reads | 50-90% input discount |
| Roo Code (Bedrock custom ARN) | Silently disables caching | 0% cache reads | Full Bedrock caching |
| Continue | Caching opt-in by default; most users never enable it | 0% for most users | 90% discount default |
| Continue (Gemini) | Explicit `cachedContents` API not implemented at all | Implicit-cache luck only | Guaranteed 75% discount on Pro |
| Aider | 5min TTL + costly keepalive pings | 5min cache windows | 1h cache, no pings |
| Aider | `--cache-prompts` off by default | 0% for most users | 90% discount default |
| OpenCode | OpenAI-compatible proxies → Anthropic miss caching | 0% on LiteLLM/Bifrost routes | Full Anthropic caching through proxies |

13 skills total, each one a self-contained fix. See
[`skills/README.md`](skills/README.md) for the full index.

## How to use it

### Option A — point any AI coding agent at this repo

In your agent of choice (Claude Code, Codex, Cline, Cursor, Devin, etc.):

```
Read https://github.com/<owner>/prompt-cache-skills

Apply every skill in skills/ that matches the harnesses I currently
use. For each one:
1. Confirm the target file exists in my project at the cited path.
2. Apply the diff.
3. Run the SKILL's Verify steps and confirm the assertion passes.
4. If verify fails, revert and tell me why.
```

That's it. The agent picks up the rest from each `SKILL.md`'s
machine-readable frontmatter and instructions.

### Option B — install as a skill bundle in Claude Code / Devin / etc.

If you use one of the agents that supports a skills directory:

```bash
# Claude Code
git clone <this-repo> ~/.claude/skills/prompt-cache-skills

# Devin
git clone <this-repo> ~/.config/devin/skills/prompt-cache-skills

# OpenCode
git clone <this-repo> ~/.config/opencode/skills/prompt-cache-skills
```

Then ask your agent:

```
Run the prompt-cache-skills bundle on this codebase.
```

### Option C — read and apply by hand

Each [`skills/<name>/SKILL.md`](skills/) is a complete fix: target,
symptom, diff, verification. Apply the relevant ones manually if you
don't trust your agent to do it.

## What's in here

```
prompt-cache-skills/
├── skills/                       ← the fixes (this is what your agent reads)
│   ├── cline-fix-volatile-msg/
│   ├── cline-openai-cache-key/
│   ├── cline-pin-timestamp/
│   ├── roo-fix-volatile-msg/
│   ├── roo-bedrock-custom-arn/
│   ├── continue-fix-volatile-msg/
│   ├── continue-enable-defaults/
│   ├── continue-gemini-explicit/
│   ├── opencode-detect-openai-compat/
│   ├── opencode-bedrock-doc-blocks/
│   ├── opencode-mistral-cache-key/
│   ├── aider-1h-ttl/
│   └── aider-cache-default-on/
├── audits/                       ← evidence: per-harness audit reports
│   ├── cline.md
│   ├── roo-code.md
│   ├── aider.md
│   ├── opencode.md
│   ├── continue.md
│   ├── codex-cli.md              ← (reference, already correct)
│   └── claude-code.md
├── docs/                         ← the underlying API mechanics
│   ├── concepts/                 ← per-provider caching reference
│   ├── gotchas.md                ← 16 numbered footguns
│   ├── verification.md           ← how to confirm caching on wire
│   └── scorecard.md              ← all harnesses graded at a glance
├── tools/                        ← scripts to verify caching yourself
│   ├── check_cache.py            ← fire request twice, dump cache_* fields
│   ├── audit_harness.sh
│   └── replay_harness.md
└── AGENTS.md                     ← entry point for AI agents reading this repo
```

## Why this exists

If your agent harness sends 30,000 tokens of system prompt + tools per
turn, on Claude 4.7 Opus that's $0.15 per turn uncached vs $0.015
cached — a 10x difference. A 50-turn coding session costs $7.50 vs
$0.75. **You're paying 10x what you should be** because the harness
you use either:

- doesn't set `cache_control` at all,
- sets it on volatile content that thrashes the cache,
- doesn't set `prompt_cache_key` for OpenAI,
- has caching gated behind a config flag you never set, or
- just doesn't implement it for one of your providers.

None of these are hard to fix. They're all 5-15 line diffs. The
hard part is knowing which one applies to your harness and getting it
right. This repo does that work for you.

## The grade card

7 harnesses audited from source, dated 2026-05-27:

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

Full per-provider breakdown with file:line citations in
[`docs/scorecard.md`](docs/scorecard.md).

## Headline findings

1. **The "last 2 user messages" pattern is a copy-paste bug** that
   propagated Cline → Roo → Continue. All three burn a breakpoint on
   the volatile current turn. Same one-line fix in each.
2. **Cline OpenAI native is silently broken** — no `prompt_cache_key`,
   no prefix-stability work. Users on Cline+OpenAI pay full price.
3. **Gemini explicit caching is universally unimplemented.** Only
   implicit (best-effort, free) caching engages, even on long
   sessions with massive stable system prompts where explicit gives
   a guaranteed 75% discount.
4. **Codex CLI is the reference for OpenAI-side caching** — thread_id
   as cache key, preserved across compaction and into sub-agents.
5. **OpenCode's system-prompt split is the best Anthropic pattern.**

## Trust but verify

Every skill ships with a Verify section that captures the wire and
confirms the fix landed. Don't take our word for it — the
[`tools/check_cache.py`](tools/check_cache.py) script fires any
request body twice (cold + warm) and prints the diff of `cache_*`
token fields.

Run it before and after applying a skill. You should see
`cache_read_input_tokens` (Anthropic) or `cached_tokens` (OpenAI) or
`cachedContentTokenCount` (Gemini) go from 0 to most of your input.

## Contributing

We accept new skills, new harness audits, and corrections. See
[`CONTRIBUTING.md`](CONTRIBUTING.md). The bar is: a captured request
body + a verified hit-rate change. We don't take vibe submissions.

## License

Skills and audit prose: CC-BY-4.0. Code (`tools/`): MIT.

## Star and share

If this saved you money, share it with the other people using these
harnesses. The whole point is that everyone gets caching working at
once.
