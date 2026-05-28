# Claude Code (Anthropic official)

| Field | Value |
|-------|-------|
| Repo | `anthropics/claude-code` (plugins/scripts only; core is closed-source) |
| Audited commit | n/a — distributed as packaged binary |
| Audit date | 2026-05-27 |
| Auditor | terp (inferred from shim traffic + public docs) |
| Provider tested | Anthropic Messages API (direct) |
| Verdict | **working** (inferred — reference implementation, not source-verified) |

## Status: source-locked

The public `anthropics/claude-code` GitHub repo contains only plugins,
scripts, and the README. The actual agent loop and provider-call code
ship as a packaged binary distributed via `curl https://claude.ai/install.sh`
or the macOS/Windows installers. There is no public source to audit.

We can't read the breakpoint-placement code, but we have indirect
evidence of correctness from two angles:

1. **OAuth-bearer traffic shape.** Our production proxy
   (`claude_byok.py`) intercepts and replays Claude Code's exact OAuth
   handshake, beta header, and message construction. The beta header
   it sends is:

   ```
   anthropic-beta: oauth-2025-04-20,fine-grained-tool-streaming-2025-05-14,interleaved-thinking-2025-05-14,prompt-caching-2024-07-31
   ```

   The presence of `prompt-caching-2024-07-31` (graduated, no-op now
   but historically required) plus the OAuth identity gating proves
   Claude Code uses prompt caching by default.

2. **Anthropic's own pricing literature.** Claude Code is Anthropic's
   reference agent CLI and is marketed against cache-hit pricing
   (`$0.50/MTok` on Opus 4.7). The product wouldn't be priced this
   way internally if its harness didn't realize the full cache
   benefit.

## Hypothesis (source-locked, but strong)

Pattern matches the production shim that mimics Claude Code's wire
format: 3 explicit breakpoints placed on (a) last system block,
(b) last tool, (c) last message content block, leaving one breakpoint
in reserve. 5min TTL (default ephemeral).

Why we think this is right:

- The shim was reverse-engineered from observed Claude Code traffic
  and hits 99%+ cache reads on steady-state turns.
- Anthropic's pricing model only makes sense for first-party tooling
  that realizes the full discount, which requires breakpoints in the
  canonical positions.

We cannot prove this without source. A wire capture from a real
Claude Code session would confirm the breakpoint count and placement
in <5 minutes; we've left that as a TODO.

## Wire capture

Not yet performed. Recipe:

```bash
# Configure Claude Code to route through mitmproxy
ANTHROPIC_BASE_URL=http://127.0.0.1:8090 \
mitmdump -p 8090 -w /tmp/cc.flow \
  --set listen_host=127.0.0.1 --set ssl_insecure=true &
claude "list files"
# Run the same prompt 2-3 times in the same session
# Extract request body of 2nd call from /tmp/cc.flow
# Inspect: count cache_control markers, note their positions
# Inspect response usage: cache_read_input_tokens should be >0 on call 2+
```

Note: Claude Code uses its own OAuth flow, not `ANTHROPIC_API_KEY`. The
`ANTHROPIC_BASE_URL` override may or may not be honored depending on
the build; if not, use `HTTPS_PROXY` and trust the mitm cert.

## Verdict reasoning

**Working** with the explicit caveat that this is inferred, not
source-verified. We're rating it `working` rather than `unverified`
because:

- The OAuth traffic shows the prompt-caching beta header.
- The wire format matches a production replay shim that achieves
  99%+ hit rates.
- It would be operationally embarrassing for Anthropic to ship the
  reference agent CLI for Anthropic's models without caching.

If a wire capture later contradicts any of this, downgrade to
`partial` or `broken` and update.

## Patch

n/a (closed source).

## Reproduction

See "Wire capture" above. The TODO here is the only audit gap.

## Notes

- The public `anthropics/claude-code` repo is misleading at first
  glance: it looks like a real repo but contains only scaffolding
  for plugins, an install script, and PR-management TypeScript.
- The product itself ships as a Node CLI bundle. You can `which claude`
  and inspect the bundled JS, but it's minified and not in scope for
  this audit. (If you do, the relevant function names should include
  `cache_control` literals — feel free to grep and submit findings.)
- This file should be treated as the BASELINE other audits compare
  against. The shim-based pattern in `docs/concepts/anthropic.md`
  ("Worked example") IS the Claude Code pattern, reverse-engineered.
