"""Tests for tools/check_docs_consistency.py — structural checks only."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import check_docs_consistency as cdc


# ---------------------------------------------------------------------------
# Expected-lists sanity
# ---------------------------------------------------------------------------

class TestExpectedLists:
    def test_completed_count(self) -> None:
        assert len(cdc.EXPECTED_COMPLETED) == 13

    def test_stub_list_is_sorted(self) -> None:
        assert cdc.EXPECTED_STUBS == sorted(cdc.EXPECTED_STUBS)

    def test_no_overlap(self) -> None:
        overlap = set(cdc.EXPECTED_COMPLETED) & set(cdc.EXPECTED_STUBS)
        assert overlap == set(), f"overlap: {overlap}"

    def test_all_end_in_md(self) -> None:
        for name in cdc.EXPECTED_COMPLETED + cdc.EXPECTED_STUBS:
            assert name.endswith(".md"), f"{name} doesn't end with .md"


# ---------------------------------------------------------------------------
# audit_sets
# ---------------------------------------------------------------------------

class TestAuditSets:
    def test_completed_matches_expected(self) -> None:
        completed, _, _ = cdc.audit_sets()
        assert completed == sorted(cdc.EXPECTED_COMPLETED)

    def test_stubs_match_expected(self) -> None:
        _, stubs, _ = cdc.audit_sets()
        assert stubs == sorted(cdc.EXPECTED_STUBS)

    def test_total_audit_count(self) -> None:
        _, _, all_files = cdc.audit_sets()
        assert len(all_files) == len(cdc.EXPECTED_COMPLETED) + len(cdc.EXPECTED_STUBS)


# ---------------------------------------------------------------------------
# table_rows_between
# ---------------------------------------------------------------------------

class TestTableRowsBetween:
    def test_extracts_rows(self) -> None:
        text = (
            "## Start\n"
            "| Harness | Data |\n"
            "|---------| ---- |\n"
            "| Alpha | foo |\n"
            "| Beta | bar |\n"
            "## End\n"
        )
        rows = cdc.table_rows_between(text, "## Start", "## End")
        assert rows == ["Alpha", "Beta"]

    def test_skips_header_and_separator(self) -> None:
        text = (
            "## A\n"
            "| Harness | X |\n"
            "|---------|---|\n"
            "| Row1 | y |\n"
            "## B\n"
        )
        rows = cdc.table_rows_between(text, "## A", "## B")
        assert rows == ["Row1"]


# ---------------------------------------------------------------------------
# full consistency check (integration)
# ---------------------------------------------------------------------------

class TestFullConsistency:
    def test_main_passes(self) -> None:
        cdc.main()


# ---------------------------------------------------------------------------
# markdown_files
# ---------------------------------------------------------------------------

class TestMarkdownFiles:
    def test_returns_only_md(self) -> None:
        for p in cdc.markdown_files():
            assert p.suffix == ".md"

    def test_excludes_git(self) -> None:
        for p in cdc.markdown_files():
            assert ".git" not in p.parts

    def test_nonempty(self) -> None:
        assert len(cdc.markdown_files()) > 0
