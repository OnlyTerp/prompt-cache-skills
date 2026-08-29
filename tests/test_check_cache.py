"""Tests for tools/check_cache.py — pure-logic functions only (no live API calls)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Allow imports from the tools directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import check_cache as cc


# ---------------------------------------------------------------------------
# extract_usage
# ---------------------------------------------------------------------------

class TestExtractUsage:
    def test_anthropic_full(self) -> None:
        resp = {
            "usage": {
                "input_tokens": 23,
                "cache_creation_input_tokens": 1842,
                "cache_read_input_tokens": 0,
                "output_tokens": 412,
            }
        }
        result = cc.extract_usage("anthropic", resp)
        assert result == {
            "input": 23,
            "cache_creation": 1842,
            "cache_read": 0,
            "output": 412,
        }

    def test_anthropic_missing_fields(self) -> None:
        result = cc.extract_usage("anthropic", {})
        assert result == {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}

    def test_openai_full(self) -> None:
        resp = {
            "usage": {
                "prompt_tokens": 2104,
                "completion_tokens": 312,
                "prompt_tokens_details": {"cached_tokens": 1920},
            }
        }
        result = cc.extract_usage("openai", resp)
        assert result == {
            "input": 2104,
            "cache_creation": 0,
            "cache_read": 1920,
            "output": 312,
        }

    def test_openai_null_details(self) -> None:
        resp = {
            "usage": {
                "prompt_tokens": 500,
                "completion_tokens": 100,
                "prompt_tokens_details": None,
            }
        }
        result = cc.extract_usage("openai", resp)
        assert result["cache_read"] == 0

    def test_openai_missing_details(self) -> None:
        resp = {"usage": {"prompt_tokens": 500, "completion_tokens": 100}}
        result = cc.extract_usage("openai", resp)
        assert result["cache_read"] == 0

    def test_gemini_full(self) -> None:
        resp = {
            "usageMetadata": {
                "promptTokenCount": 38500,
                "cachedContentTokenCount": 32100,
                "candidatesTokenCount": 420,
            }
        }
        result = cc.extract_usage("gemini", resp)
        assert result == {
            "input": 38500,
            "cache_creation": 0,
            "cache_read": 32100,
            "output": 420,
        }

    def test_gemini_null_metadata(self) -> None:
        resp = {"usageMetadata": None}
        result = cc.extract_usage("gemini", resp)
        assert result == {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}

    def test_unknown_provider(self) -> None:
        with pytest.raises(SystemExit, match="Unknown provider"):
            cc.extract_usage("bedrock", {})


# ---------------------------------------------------------------------------
# hit_rate
# ---------------------------------------------------------------------------

class TestHitRate:
    def test_zero_denominator(self) -> None:
        assert cc.hit_rate({"input": 0, "cache_creation": 0, "cache_read": 0}) == 0.0

    def test_no_cache_reads(self) -> None:
        assert cc.hit_rate({"input": 100, "cache_creation": 50, "cache_read": 0}) == 0.0

    def test_full_cache(self) -> None:
        assert cc.hit_rate({"input": 0, "cache_creation": 0, "cache_read": 100}) == 100.0

    def test_partial_cache(self) -> None:
        usage = {"input": 23, "cache_creation": 0, "cache_read": 11890}
        rate = cc.hit_rate(usage)
        assert 99.0 < rate < 100.0

    def test_mixed(self) -> None:
        usage = {"input": 100, "cache_creation": 100, "cache_read": 200}
        rate = cc.hit_rate(usage)
        assert rate == 50.0


# ---------------------------------------------------------------------------
# caller env-var guards
# ---------------------------------------------------------------------------

class TestCallerEnvGuards:
    def test_anthropic_no_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit, match="ANTHROPIC_API_KEY"):
                cc.call_anthropic({"model": "test"})

    def test_openai_no_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
                cc.call_openai({"model": "test"})

    def test_gemini_no_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit, match="GEMINI_API_KEY"):
                cc.call_gemini({"model": "test"})


# ---------------------------------------------------------------------------
# main() — argument parsing and body loading
# ---------------------------------------------------------------------------

class TestMain:
    def test_missing_body_file(self) -> None:
        with patch("sys.argv", ["check_cache.py", "--provider", "anthropic", "--body", "/nonexistent.json"]):
            with pytest.raises(SystemExit, match="body file not found"):
                cc.main()

    def test_invalid_json_body(self) -> None:
        # NOTE: close the temp file BEFORE main() opens it and before
        # os.unlink() — on Windows the open handle causes WinError 32.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            name = f.name
            f.write("not json {{{")
        try:
            with patch("sys.argv", ["check_cache.py", "--provider", "anthropic", "--body", name]):
                with pytest.raises(SystemExit, match="invalid JSON"):
                    cc.main()
        finally:
            os.unlink(name)

    def test_non_object_body(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            name = f.name
            json.dump([1, 2, 3], f)
        try:
            with patch("sys.argv", ["check_cache.py", "--provider", "anthropic", "--body", name]):
                with pytest.raises(SystemExit, match="body must be a JSON object"):
                    cc.main()
        finally:
            os.unlink(name)


# ---------------------------------------------------------------------------
# CALLERS registry
# ---------------------------------------------------------------------------

class TestCallersRegistry:
    def test_all_providers_registered(self) -> None:
        assert set(cc.CALLERS.keys()) == {"anthropic", "openai", "gemini"}

    def test_callers_are_callable(self) -> None:
        for name, fn in cc.CALLERS.items():
            assert callable(fn), f"{name} caller is not callable"
