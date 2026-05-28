# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial public release.
- 13 atomic prompt-caching skills covering Cline, Roo Code, Continue,
  OpenCode, and Aider.
- 13 completed per-harness audits: the original 7 source audits plus
  extended source/wire/local-install audits for Hermes/Nous, Codex
  Desktop, Devin CLI, Windsurf/Cascade, Antigravity, and Grok CLI.
  Six additional `audits/` files are queued stubs, not completed audits.
- Per-provider reference docs (Anthropic, OpenAI, Gemini, Bedrock,
  Vertex) verified against live provider documentation 2026-05-27.
- 16 numbered gotchas covering the highest-frequency caching
  failure modes.
- `tools/check_cache.py` — zero-dependency wire-verification script.
- `tools/check_docs_consistency.py` — CI/local guard for audit counts,
  README table rows, scorecard links, stale count phrases, and local
  Markdown links.
- `AGENTS.md` entry point so AI coding agents pointed at this repo
  know how to apply the skills without further prompting.
- Scorecard summarizing completed audited harnesses per provider.
- Continuous-integration workflow that lint-checks Markdown, runs
  Python syntax checks, verifies docs consistency, and runs gitleaks on
  every push and PR.

### Security

- Repository scanned with `gitleaks v8.21.2` against both the
  working tree and full git history — no leaks found at release.
