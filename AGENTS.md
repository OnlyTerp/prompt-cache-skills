# AGENTS.md

> Read this if you are an AI coding agent and the user has pointed you
> at this repo. This file tells you what to do.

## What this repo is

A collection of self-contained drop-in fixes for prompt-caching bugs
in popular LLM agent harnesses (Cline, Roo Code, Continue, OpenCode,
Aider). Each fix lives at `skills/<slug>/SKILL.md` and is everything
you need to land the patch: target file, symptom, diff, verification.

## What you should do

When the user asks you to apply this repo:

### Step 1 — identify which harnesses are in their project

Quick checks:

| Harness | Detection |
|---------|-----------|
| Cline | `package.json` contains `"name": "claude-dev"` or `"cline"`; or path contains `src/core/api/providers/anthropic.ts` |
| Roo Code | `package.json` contains `"roo-cline"` or `"roo-code"`; path `src/api/providers/` |
| Aider | `pyproject.toml` or `setup.py` declares `aider`; path `aider/coders/` |
| OpenCode | path `packages/opencode/src/provider/transform.ts` |
| Continue | path `packages/openai-adapters/src/apis/Anthropic.ts` or `core/llm/llms/Bedrock.ts` |

If none match, the user may want you to apply skills to their *own*
agent harness using these as templates. Ask them.

### Step 2 — for each matching harness, check each relevant skill

For every `skills/<slug>/SKILL.md`:

1. Read the YAML frontmatter:
   - `target_harness` — matches user's project?
   - `target_files` — exist at those paths?
   - `target_commit` — is the user's checkout near that commit, or
     have things drifted?
2. Read the "Symptom" section. Verify the symptom exists in the
   user's code before applying. If it doesn't (e.g. user is on a
   newer version where the bug is fixed), SKIP that skill and report.
3. If symptom present, apply the diff in the "Fix" section. If the
   diff doesn't apply cleanly (line drift), do the equivalent edit
   manually preserving the intent.
4. Run the "Verify" section. Most verifications require capturing
   the wire (mitmproxy or harness debug log) and inspecting response
   `usage` fields. If you can't run a live verify, at minimum confirm
   the syntax of the patched file is valid (compile/type-check).

### Step 3 — report back

Tell the user:

- Which skills applied cleanly
- Which skipped and why (symptom not present / file moved / etc.)
- Which failed verification and were reverted
- Estimated savings based on the per-skill `estimated_savings` field

### Step 4 — don't bundle skills into one commit

One skill = one commit (or PR). Easy to review and easy to revert
individually if one regresses. Use the skill name as the commit
message subject.

## What you should NOT do

- **Don't modify the skills themselves** unless the user explicitly
  asks. If you spot a bug in a skill, write it up as a comment or
  patch and stop there.
- **Don't apply skills speculatively.** Every skill has a target
  file + symptom check; verify before applying. The fixes are
  surgical, not heuristic.
- **Don't replace `cache_control` with random UUIDs or session IDs
  thinking it'll "randomize the cache".** That's the #1 footgun. See
  `docs/gotchas.md` #9b.
- **Don't combine skills into one mega-fix.** Each one is atomic for
  a reason — separate bugs can have separate reviewers and separate
  upstream PRs.
- **Don't open upstream PRs without the user's explicit go-ahead.**
  The skills are written to be applied locally; pushing them upstream
  is a separate decision the user owns.

## Useful reference paths

If you need to understand WHY a fix matters before applying:

- `docs/concepts/anthropic.md` — Anthropic prompt caching mechanics
- `docs/concepts/openai.md` — OpenAI prompt caching + `prompt_cache_key`
- `docs/concepts/gemini.md` — Gemini implicit + explicit caching
- `docs/concepts/bedrock.md` — Bedrock `cachePoint` semantics
- `docs/gotchas.md` — 16 numbered failure modes
- `docs/verification.md` — how to confirm caching is working

For the audit evidence behind each skill:

- `audits/<harness>.md` — full source audit + permalinks

## Verifying your work

The repo ships `tools/check_cache.py` — a zero-dependency Python
script that fires any request body twice and dumps the cache token
diff. Use it as a smoke test:

```bash
# After applying a skill that targets Anthropic:
python3 tools/check_cache.py --provider anthropic --body /tmp/req.json
# Expect: warm.cache_read > 0 and significantly larger than warm.input
```

If `cache_read` is 0 on the warm call, the fix didn't land or there's
a second upstream issue. Stop and report rather than retrying blindly.

## Development setup

### Prerequisites

- Python 3.11+ (stdlib only — no pip install needed)
- Node.js 18+ (for `markdownlint-cli2` via npx)

### Build / lint / test commands

```bash
# Python syntax check (CI job: python-syntax)
python3 -m py_compile tools/check_cache.py tools/check_docs_consistency.py

# Docs consistency guard (CI job: consistency)
python3 tools/check_docs_consistency.py

# Markdown lint (CI job: markdown-lint)
npx markdownlint-cli2 '**/*.md' '!**/node_modules/**'

# Python unit tests (CI job: python-tests)
python3 -m pytest tests/ -v

# Python type check (CI job: python-typecheck)
python3 -m mypy tools/ --strict

# Secrets scan (CI job: secrets-scan — requires gitleaks binary)
gitleaks dir . --no-banner
```

### CI

GitHub Actions workflow at `.github/workflows/ci.yml` runs on every
push and PR: gitleaks, markdownlint, python syntax, docs consistency,
pytest, mypy, and link check.

## When in doubt

Read the SKILL.md fully. They're written to be self-explanatory for
agents. If a skill is ambiguous, treat that as a bug in the skill
and ask the user how to proceed rather than guessing.
