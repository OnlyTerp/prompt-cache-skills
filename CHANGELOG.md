# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial public release.
- 13 atomic prompt-caching skills covering Cline, Roo Code, Continue,
  OpenCode, and Aider.
- 7 per-harness source audits (Claude Code, Codex CLI, Aider,
  OpenCode, Roo Code, Cline, Continue) with file:line citations.
- Per-provider reference docs (Anthropic, OpenAI, Gemini, Bedrock,
  Vertex) verified against live provider documentation 2026-05-27.
- 16 numbered gotchas covering the highest-frequency caching
  failure modes.
- `tools/check_cache.py` — zero-dependency wire-verification script.
- `AGENTS.md` entry point so AI coding agents pointed at this repo
  know how to apply the skills without further prompting.
- Scorecard summarizing all audited harnesses per provider.
- Continuous-integration workflow that lint-checks Markdown and
  runs gitleaks on every push and PR.

### Security

- Repository scanned with `gitleaks v8.21.2` against both the
  working tree and full git history — no leaks found at release.
