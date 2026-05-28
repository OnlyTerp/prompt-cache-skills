# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Unit test suite for `tools/check_cache.py` and
  `tools/check_docs_consistency.py` (34 tests via pytest).
- `mypy --strict` type checking for all Python tooling.
- CI jobs for pytest and mypy.
- `pyproject.toml` with mypy and pytest configuration.
- Development setup section in `AGENTS.md` with all build/lint/test
  commands.

### Fixed

- LICENSE copyright holder referenced stale project name
  (`prompt-cache-audit` → `prompt-cache-skills`).
- README and `skills/README.md` used `<owner>` / `<this-repo>`
  placeholders instead of actual repo URL.
- `check_cache.py` now validates the body file (missing file, malformed
  JSON, non-object body) before attempting API calls.
- `check_cache.py` now catches `URLError` (connection failures) in
  addition to `HTTPError`.
- Mypy strict type annotation fix in `_http()` return value.
- `FUNDING.yml` pointed at placeholder instead of `OnlyTerp`.
- `bedrock.md` and `vertex.md` `_Last verified: TODO_` stamped with
  dates and explicit scaffold caveats.

## [0.1.0] — 2026-05-28

### Added

- Initial public release.
- 13 atomic prompt-caching skills covering Cline, Roo Code, Continue,
  OpenCode, and Aider.
- 13 completed per-harness audits: the default Claude Desktop Code
  baseline verified from clean Mac cache counters, source-recon audits
  for Codex CLI, Aider, OpenCode, Roo Code, Cline, and Continue, plus
  extended source/wire/local-install audits for Hermes/Nous, Codex
  Desktop, Devin CLI, Windsurf/Cascade, Antigravity, and Grok CLI. Six
  additional `audits/` files are queued stubs, not completed audits.
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
