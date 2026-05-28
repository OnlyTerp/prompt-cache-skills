# Scorecard

> Source-recon audit of 7 harnesses, dated 2026-05-27. Hit-rate columns
> are absent because wire capture wasn't performed in this round —
> verdicts are based on source inspection. Re-runs with measured rates
> are tracked in [`../PROGRESS.md`](../PROGRESS.md).

## Anthropic providers

| Harness | Sets `cache_control`? | Breakpoints | TTL | Volatile-msg bug? | Verdict | Audit |
|---------|----------------------|-------------|-----|-------------------|---------|-------|
| Claude Code | yes (inferred) | 3 (system, tools, last) | 5min | no (inferred) | **working** | [`../audits/claude-code.md`](../audits/claude-code.md) |
| OpenCode | yes | 4 (system×2 split, last 2 msgs) | 5min / 1h flag | partial | **working** | [`../audits/opencode.md`](../audits/opencode.md) |
| Aider | yes (--cache-prompts) | 4 (system, repo-map, files, current) | 5min | no | **working** | [`../audits/aider.md`](../audits/aider.md) |
| Cline | yes | 3 (system, last 2 user msgs) | 5min | **yes** | **partial** | [`../audits/cline.md`](../audits/cline.md) |
| Roo Code | yes | 3 (system, last 2 user msgs) | 5min | **yes** | **partial** | [`../audits/roo-code.md`](../audits/roo-code.md) |
| Continue | yes (config-gated, off by default) | 3 (system, last 2 user msgs) | 5min | **yes** | **partial** | [`../audits/continue.md`](../audits/continue.md) |

## OpenAI providers (Responses API + Chat Completions)

OpenAI caching is automatic; harnesses are graded on prefix stability
and whether they set `prompt_cache_key` to a stable value.

| Harness | `prompt_cache_key` set? | Stable hash or UUID? | Prefix byte-stable? | Verdict | Audit |
|---------|------------------------|----------------------|---------------------|---------|-------|
| Codex CLI | yes | stable (`thread_id`) | yes (`base_instructions`) | **working** | [`../audits/codex-cli.md`](../audits/codex-cli.md) |
| Aider | n/a (Chat Completions; auto) | n/a | yes (no timestamp pollution) | **automatic** | [`../audits/aider.md`](../audits/aider.md) |
| Roo Code | yes | stable (sha256 of system + first msg) | yes | **working** | [`../audits/roo-code.md`](../audits/roo-code.md) |
| OpenCode | yes | unverified (likely stable) | yes (with system split) | **working** | [`../audits/opencode.md`](../audits/opencode.md) |
| Continue | no | n/a | unverified | **partial** | [`../audits/continue.md`](../audits/continue.md) |
| Cline | **no** | n/a | unverified | **broken** | [`../audits/cline.md`](../audits/cline.md) |

## Bedrock (Anthropic models via Converse API)

Bedrock requires `cachePoint`, not `cache_control`. Harnesses that
hardcode `cache_control` will silently not cache here.

| Harness | Uses `cachePoint` correctly? | Custom ARN handling | Verdict | Audit |
|---------|------------------------------|---------------------|---------|-------|
| OpenCode | yes (broken on DocumentBlocks #17300) | n/a | **partial** | [`../audits/opencode.md`](../audits/opencode.md) |
| Continue | yes | n/a | **partial** | [`../audits/continue.md`](../audits/continue.md) |
| Cline | yes (but gated, incomplete impl) | n/a | **unverified** | [`../audits/cline.md`](../audits/cline.md) |
| Roo Code | yes for declared models | **broken** for custom ARNs (#11983) | **partial** | [`../audits/roo-code.md`](../audits/roo-code.md) |

## Gemini

Implicit caching (Gemini 2.5+) works automatically without harness
involvement. Explicit `cachedContents` requires the harness to use
the API.

| Harness | Uses `cachedContents`? | Implicit cache OK? | Verdict | Audit |
|---------|-----------------------|--------------------|---------|-------|
| Continue | **no** | yes (no prefix pollution) | **broken** (explicit) / **automatic** (implicit) | [`../audits/continue.md`](../audits/continue.md) |

(Other harnesses don't ship Gemini support, or do via OpenRouter
passthrough — which is rated under the Anthropic column above when
Gemini is being routed.)

## OpenRouter / multi-route adapters

Note: OpenRouter forwards `cache_control` (Anthropic-shape) to
Anthropic-backed models and `cachedContents` shape to Gemini-backed.
Top-level `prompt_cache_ttl` is silently dropped (OpenCode #16848).

| Harness | OpenRouter Anthropic | OpenRouter Gemini | Verdict | Audit |
|---------|---------------------|-------------------|---------|-------|
| OpenCode | yes (content-level ttl) | yes (PR #20266 Vertex) | **working** | [`../audits/opencode.md`](../audits/opencode.md) |
| Roo Code | yes (delegates via transform module) | yes | **working** | [`../audits/roo-code.md`](../audits/roo-code.md) |
| Cline | yes (Anthropic + MiniMax detected) | unverified | **partial** | [`../audits/cline.md`](../audits/cline.md) |

## Headline findings

1. **The "last 2 user messages" pattern is a copy-paste mistake** that
   has propagated through Cline → Roo → Continue. All three burn a
   breakpoint on the volatile current user turn. Fix is the same diff
   in each.

2. **OpenAI Chat Completions caching is silently broken in Cline.**
   No `prompt_cache_key`, no prefix-stability work — users on OpenAI
   via Cline are paying full price. Roo fixed this; Cline upstream
   hasn't.

3. **Bedrock detection is fragile everywhere.** OpenCode misses
   OpenAI-compatible proxies routing to Bedrock; Roo misses custom
   ARNs; Cline's Bedrock impl is incomplete. None of the auditors
   appears to have great test coverage for Bedrock paths.

4. **Gemini explicit caching is universally unimplemented.** Every
   multi-provider harness in the audit either uses only implicit
   caching (best-effort, free) or skips Gemini entirely. Explicit
   `cachedContents` with controllable TTL is a gap across the
   ecosystem.

5. **Codex CLI is the reference for OpenAI-side caching.** Thread-id
   as cache key, preserved across compaction and into sub-agents,
   with stable base_instructions. Other harnesses targeting GPT-5+
   should pattern-match this.

6. **OpenCode's system-prompt split is the best Anthropic pattern.**
   Two breakpoints on the static-vs-dynamic system split lets the
   tools+global-config half live in a long-lived cache while
   per-project context drifts independently. Worth porting to Cline/Roo.

7. **Continue requires explicit opt-in.** Default is no caching. For
   the median user this means the harness is leaving 90% input
   discount on the table.

## Recommended ranking (best to worst for typical Anthropic-targeted use)

1. **Aider** (`--cache-prompts` enabled) — 4 canonical breakpoints, no thrash
2. **OpenCode** — 4 breakpoints with system split; experimental 1h TTL flag
3. **Claude Code** — inferred reference implementation (closed source)
4. **Codex CLI** — for OpenAI workloads, top of class
5. **Roo Code** — partial; volatile-msg bug; ahead of Cline on OpenAI
6. **Cline** — partial; same volatile-msg bug; broken OpenAI native
7. **Continue** — works only when explicitly configured; default off
