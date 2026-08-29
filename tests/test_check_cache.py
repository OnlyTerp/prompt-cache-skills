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

    # -- DeepSeek top-level counters (prompt_cache_hit_tokens) --------------

    def test_deepseek_top_level_cache_hit_tokens(self) -> None:
        resp = {
            "usage": {
                "prompt_tokens": 2104,
                "completion_tokens": 312,
                "prompt_cache_hit_tokens": 1920,
                "prompt_cache_miss_tokens": 184,
            }
        }
        result = cc.extract_usage("deepseek", resp)
        assert result == {
            "input": 2104,
            "cache_creation": 0,
            "cache_read": 1920,
            "output": 312,
        }

    def test_deepseek_null_counters(self) -> None:
        resp = {"usage": {"prompt_tokens": 100, "completion_tokens": 10,
                          "prompt_cache_hit_tokens": None}}
        assert cc.extract_usage("deepseek", resp)["cache_read"] == 0

    # -- OpenAI-compat relay shapes (openrouter / xai / custom) -------------

    def test_openrouter_nested_shape(self) -> None:
        resp = {"usage": {"prompt_tokens": 900, "completion_tokens": 50,
                          "prompt_tokens_details": {"cached_tokens": 800}}}
        assert cc.extract_usage("openrouter", resp)["cache_read"] == 800

    def test_xai_top_level_shape(self) -> None:
        resp = {"usage": {"prompt_tokens": 900, "completion_tokens": 50,
                          "prompt_cache_hit_tokens": 700}}
        assert cc.extract_usage("xai", resp)["cache_read"] == 700

    def test_custom_provider_nested_shape(self) -> None:
        resp = {"usage": {"prompt_tokens": 900, "completion_tokens": 50,
                          "prompt_tokens_details": {"cached_tokens": 640}}}
        assert cc.extract_usage("custom", resp)["cache_read"] == 640

    def test_nested_wins_over_top_level(self) -> None:
        resp = {"usage": {"prompt_tokens": 900, "completion_tokens": 50,
                          "prompt_tokens_details": {"cached_tokens": 800},
                          "prompt_cache_hit_tokens": 700}}
        assert cc.extract_usage("openai", resp)["cache_read"] == 800


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

    def test_deepseek_no_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit, match="DEEPSEEK_API_KEY"):
                cc.call_deepseek({"model": "test"})

    def test_openrouter_no_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit, match="OPENROUTER_API_KEY"):
                cc.call_openrouter({"model": "test"})

    def test_xai_no_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit, match="XAI_API_KEY"):
                cc.call_xai({"model": "test"})

    def test_custom_no_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit, match="CUSTOM_API_KEY"):
                cc.call_custom({"model": "test"})

    def test_gemini_no_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit, match="GEMINI_API_KEY"):
                cc.call_gemini({"model": "test"})

    def test_openrouter_injects_usage_optin(self) -> None:
        captured: dict = {}

        def fake_http(url, headers, body):
            captured["body"] = body
            return {"usage": {}}

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "k"}, clear=True):
            with patch.object(cc, "_http", fake_http):
                cc.call_openrouter({"model": "m"})
        assert captured["body"].get("usage") == {"include": True}

    def test_openrouter_respects_existing_usage(self) -> None:
        captured: dict = {}

        def fake_http(url, headers, body):
            captured["body"] = body
            return {"usage": {}}

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "k"}, clear=True):
            with patch.object(cc, "_http", fake_http):
                cc.call_openrouter({"model": "m", "usage": {"include": False}})
        assert captured["body"]["usage"] == {"include": False}

    def test_openrouter_headers_from_env(self) -> None:
        captured: dict = {}

        def fake_http(url, headers, body):
            captured["headers"] = headers
            return {"usage": {}}

        env = {"OPENROUTER_API_KEY": "k",
               "OPENROUTER_SITE_URL": "https://x.dev",
               "OPENROUTER_SITE_NAME": "X"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(cc, "_http", fake_http):
                cc.call_openrouter({"model": "m"})
        assert captured["headers"]["HTTP-Referer"] == "https://x.dev"
        assert captured["headers"]["X-Title"] == "X"


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
        assert set(cc.CALLERS.keys()) == {
            "anthropic", "openai", "deepseek", "openrouter", "xai", "gemini", "custom"
        }

    def test_openai_compat_registry_consistent(self) -> None:
        # extract_usage treats every CALLERS entry except anthropic/gemini
        # as OpenAI-compatible — keep the sets in lockstep.
        non_compat = {"anthropic", "gemini"}
        assert set(cc.CALLERS.keys()) - non_compat == cc.OPENAI_COMPAT_PROVIDERS

    def test_callers_are_callable(self) -> None:
        for name, fn in cc.CALLERS.items():
            assert callable(fn), f"{name} caller is not callable"
