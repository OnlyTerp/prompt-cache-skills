#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_COMPLETED = [
    "claude-code.md",
    "codex-cli.md",
    "aider.md",
    "opencode.md",
    "roo-code.md",
    "cline.md",
    "continue.md",
    "hermes-nous.md",
    "codex-desktop.md",
    "devin-cli.md",
    "windsurf-cascade.md",
    "antigravity.md",
    "grok-cli.md",
]

EXPECTED_STUBS = [
    "aichat.md",
    "avante-nvim.md",
    "crush.md",
    "goose.md",
    "gptme.md",
    "kilo-code.md",
]

EXPECTED_README_ROWS = [
    "Claude Desktop Code",
    "Codex CLI",
    "Aider",
    "OpenCode",
    "Roo Code",
    "Cline",
    "Continue",
    "Hermes / Nous",
    "Codex Desktop",
    "Devin CLI",
    "Windsurf / Cascade",
    "Antigravity",
    "Grok CLI",
]

STALE_COUNT_PHRASES = [
    "13 harnesses audited",
    "13 harnesses graded",
    "7 harness audits from source",
    "13 per-harness audits:",
    "original 7 source audits",
    "original OSS/source set",
    "OSS/source-recon audits",
]

STALE_CLAUDE_CODE_PHRASES = [
    "Claude Code | Closed source; cache behavior inferred from wire shape",
    "No skill; keep as reference/inferred working",
    "`audits/claude-code.md` — inferred; closed source",
    "Claude Code** — inferred reference implementation (closed source)",
    "Claude Code — capture to confirm inferred breakpoint pattern",
    "Claude Code / Cowork | Desktop Cowork launches embedded Claude Code",
    "Claude Code / Cowork | **working (verified Cowork cache counters)**",
    "Claude Code / Cowork baseline verified from desktop local-agent cache counters",
    "We cannot prove this without source",
    "Not yet performed. Recipe",
]

REQUIRED_CLAUDE_CODE_PHRASES = [
    "Claude Desktop Code | Default Desktop Code launches embedded Claude Code; clean Mac logs show non-zero cache read/create counters by default",
    "Claude Desktop Code | **working (default Desktop Code verified)**",
    "Claude Desktop Code | yes (default Code logs)",
    "default Claude Desktop Code baseline verified from clean Mac cache counters",
    "default Desktop Code verified with non-zero cache read/create counters",
]


def fail(message: str) -> None:
    raise SystemExit(message)


def markdown_files() -> list[Path]:
    return [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]


def audit_sets() -> tuple[list[str], list[str], list[Path]]:
    audit_files = sorted(
        p for p in (ROOT / "audits").glob("*.md") if p.name != "_TEMPLATE.md"
    )
    stubs = sorted(
        p.name for p in audit_files if "Status: STUB" in p.read_text(errors="replace")
    )
    completed = sorted(p.name for p in audit_files if p.name not in stubs)
    return completed, stubs, audit_files


def table_rows_between(text: str, start: str, end: str) -> list[str]:
    section = text.split(start, 1)[1].split(end, 1)[0]
    return [
        line.split("|")[1].strip()
        for line in section.splitlines()
        if line.startswith("| ")
        and not line.startswith("| Harness")
        and not line.startswith("|---------")
    ]


def check_audit_counts() -> None:
    completed, stubs, audit_files = audit_sets()
    if completed != sorted(EXPECTED_COMPLETED):
        fail(f"completed audit set mismatch: {completed}")
    if stubs != sorted(EXPECTED_STUBS):
        fail(f"audit stub set mismatch: {stubs}")
    if len(audit_files) != 19 or len(completed) != 13 or len(stubs) != 6:
        fail(
            "bad audit counts: "
            f"total={len(audit_files)} completed={len(completed)} stubs={len(stubs)}"
        )


def check_readme_tables() -> None:
    readme = (ROOT / "README.md").read_text(errors="replace")
    savings_rows = table_rows_between(
        readme, "## What you actually save", "## How to use it"
    )
    if savings_rows != EXPECTED_README_ROWS:
        fail(f"README savings table rows drifted: {savings_rows}")

    grade_rows = table_rows_between(readme, "## The grade card", "## Headline findings")
    if grade_rows != EXPECTED_README_ROWS:
        fail(f"README grade card rows drifted: {grade_rows}")


def check_scorecard_links() -> None:
    scorecard = (ROOT / "docs" / "scorecard.md").read_text(errors="replace")
    linked = set(re.findall(r"\]\(\.\./audits/([^)#]+\.md)\)", scorecard))
    missing_from_scorecard = set(EXPECTED_COMPLETED) - linked
    stub_in_scorecard = set(EXPECTED_STUBS) & linked
    if missing_from_scorecard:
        fail(f"completed audits missing from scorecard: {sorted(missing_from_scorecard)}")
    if stub_in_scorecard:
        fail(f"stub audits listed in scorecard: {sorted(stub_in_scorecard)}")


def check_stale_phrases() -> None:
    stale_phrases = STALE_COUNT_PHRASES + STALE_CLAUDE_CODE_PHRASES
    for path in markdown_files():
        text = path.read_text(errors="replace")
        for phrase in stale_phrases:
            if phrase in text:
                fail(f"stale phrase {phrase!r} in {path.relative_to(ROOT)}")


def check_claude_desktop_code_phrasing() -> None:
    corpus = " ".join(
        "\n".join(path.read_text(errors="replace") for path in markdown_files()).split()
    )
    for phrase in REQUIRED_CLAUDE_CODE_PHRASES:
        if phrase not in corpus:
            fail(f"missing Claude Desktop Code evidence phrase: {phrase!r}")


def check_local_markdown_links() -> None:
    missing_links: list[tuple[str, str]] = []
    for path in markdown_files():
        text = path.read_text(errors="replace")
        for match in re.finditer(r"\]\(([^)]+)\)", text):
            target = match.group(1).split("#", 1)[0]
            if (
                not target
                or re.match(r"^[a-z]+:", target)
                or target.startswith("mailto:")
            ):
                continue
            if not (path.parent / target).resolve().exists():
                missing_links.append((str(path.relative_to(ROOT)), match.group(1)))
    if missing_links:
        fail(f"missing local markdown links: {missing_links}")


def main() -> None:
    check_audit_counts()
    check_readme_tables()
    check_scorecard_links()
    check_stale_phrases()
    check_claude_desktop_code_phrasing()
    check_local_markdown_links()
    print("docs consistency ok")


if __name__ == "__main__":
    main()
