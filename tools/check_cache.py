#!/usr/bin/env python3
"""
check_cache.py — fire a request body at a provider twice and report
cache behavior.

Usage:
  check_cache.py --provider anthropic  --body req.json
  check_cache.py --provider openai     --body req.json
  check_cache.py --provider gemini     --body req.json
  check_cache.py --provider deepseek   --body req.json
  check_cache.py --provider openrouter --body req.json
  check_cache.py --provider xai        --body req.json
  check_cache.py --provider custom     --body req.json \
                 --base-url https://relay.example/v1/chat/completions

Reads provider credentials from env:
  ANTHROPIC_API_KEY
  OPENAI_API_KEY
  GEMINI_API_KEY (or GOOGLE_API_KEY)
  DEEPSEEK_API_KEY
  OPENROUTER_API_KEY
  XAI_API_KEY
  CUSTOM_API_KEY (used with --provider custom)

All OpenAI-compatible providers (openai/deepseek/openrouter/xai/custom)
accept both nested `usage.prompt_tokens_details.cached_tokens` (OpenAI
shape) and DeepSeek-style top-level `usage.prompt_cache_hit_tokens`,
whichever the backend returns.

OpenRouter only reports usage accounting when the request body asks for
it — the `usage: {"include": true}` field is injected automatically
unless the body already sets `usage`.

Bedrock and Vertex use SDK credential chains and signed requests that
this script deliberately does not reimplement — capture those bodies via
your harness or mitmproxy and replay them with `--provider custom`
against an OpenAI-compatible relay, or audit them with the harness's own
SDK in a one-off script.

The script:
  1. Sends the request body once (cold).
  2. Waits 1 second.
  3. Sends the same body again (warm).
  4. Prints a small report:
       - Cold turn cache_creation / cache_read / input
       - Warm turn cache_creation / cache_read / input
       - Computed hit rate

It does NOT otherwise modify the request body. If you want to test what
*your* harness sends, capture a request via mitmproxy, save the body to
req.json, and run this against it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Callable

import urllib.request
import urllib.error


def _http(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
            return result
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')}")
    except urllib.error.URLError as e:
        raise SystemExit(f"connection error: {e.reason}")


def call_anthropic(body: dict[str, Any]) -> dict[str, Any]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY not set")
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    # Pass through any anthropic-beta requested via env (e.g. 1h cache)
    beta = os.environ.get("ANTHROPIC_BETA")
    if beta:
        headers["anthropic-beta"] = beta
    return _http("https://api.anthropic.com/v1/messages", headers, body)


def _openai_compat(
    base_url: str, key_env: str, extra_headers: dict[str, str] | None = None
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def _call(body: dict[str, Any]) -> dict[str, Any]:
        key = os.environ.get(key_env)
        if not key:
            raise SystemExit(f"{key_env} not set")
        headers = {
            "authorization": f"Bearer {key}",
            "content-type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        return _http(base_url, headers, body)

    return _call


def call_openai(body: dict[str, Any]) -> dict[str, Any]:
    return _openai_compat(
        "https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY"
    )(body)


def call_deepseek(body: dict[str, Any]) -> dict[str, Any]:
    return _openai_compat(
        "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY"
    )(body)


def call_openrouter(body: dict[str, Any]) -> dict[str, Any]:
    # OpenRouter reports zero usage accounting unless the body opts in.
    # Inject the opt-in when the caller didn't set it (the tool's whole
    # job is measuring usage).
    if "usage" not in body:
        body = dict(body)
        body["usage"] = {"include": True}
    extra = {}
    referer = os.environ.get("OPENROUTER_SITE_URL")
    if referer:
        extra["HTTP-Referer"] = referer
    title = os.environ.get("OPENROUTER_SITE_NAME")
    if title:
        extra["X-Title"] = title
    return _openai_compat(
        "https://openrouter.ai/api/v1/chat/completions",
        "OPENROUTER_API_KEY",
        extra_headers=extra,
    )(body)


def call_xai(body: dict[str, Any]) -> dict[str, Any]:
    return _openai_compat("https://api.x.ai/v1/chat/completions", "XAI_API_KEY")(
        body
    )


CUSTOM_BASE_URL = "https://set-via---base-url/invalid"


def call_custom(body: dict[str, Any]) -> dict[str, Any]:
    base = os.environ.get("CHECK_CACHE_BASE_URL", CUSTOM_BASE_URL)
    return _openai_compat(base, "CUSTOM_API_KEY")(body)


def call_gemini(body: dict[str, Any]) -> dict[str, Any]:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY (or GOOGLE_API_KEY) not set")
    model = body.pop("_model", "gemini-2.5-pro")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    return _http(url, {"content-type": "application/json"}, body)


CALLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "anthropic": call_anthropic,
    "openai": call_openai,
    "deepseek": call_deepseek,
    "openrouter": call_openrouter,
    "xai": call_xai,
    "gemini": call_gemini,
    "custom": call_custom,
}

OPENAI_COMPAT_PROVIDERS = {"openai", "deepseek", "openrouter", "xai", "custom"}


def extract_usage(provider: str, resp: dict[str, Any]) -> dict[str, int]:
    if provider == "anthropic":
        u = resp.get("usage", {})
        return {
            "input": u.get("input_tokens", 0),
            "cache_creation": u.get("cache_creation_input_tokens", 0),
            "cache_read": u.get("cache_read_input_tokens", 0),
            "output": u.get("output_tokens", 0),
        }
    if provider in OPENAI_COMPAT_PROVIDERS:
        u = resp.get("usage", {}) or {}
        details = u.get("prompt_tokens_details", {}) or {}
        # OpenAI shape nests it; DeepSeek returns top-level counters.
        # Nested wins when both exist. `or 0` also normalizes null.
        cache_read = details.get("cached_tokens") or u.get("prompt_cache_hit_tokens") or 0
        return {
            "input": u.get("prompt_tokens", 0),
            "cache_creation": 0,  # no write premium / explicit creation count
            "cache_read": int(cache_read),
            "output": u.get("completion_tokens", 0),
        }
    if provider == "gemini":
        u = resp.get("usageMetadata", {}) or {}
        return {
            "input": u.get("promptTokenCount", 0),
            "cache_creation": 0,
            "cache_read": u.get("cachedContentTokenCount", 0),
            "output": u.get("candidatesTokenCount", 0),
        }
    raise SystemExit(f"Unknown provider {provider}")


def hit_rate(usage: dict[str, int]) -> float:
    denom = usage["input"] + usage["cache_creation"] + usage["cache_read"]
    if denom == 0:
        return 0.0
    return 100.0 * usage["cache_read"] / denom


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=sorted(CALLERS))
    ap.add_argument("--body", required=True, help="path to JSON request body")
    ap.add_argument(
        "--base-url",
        default=None,
        help="override endpoint (required for --provider custom; also "
        "honored via CHECK_CACHE_BASE_URL env)",
    )
    ap.add_argument("--sleep", type=float, default=1.0, help="seconds between cold and warm")
    args = ap.parse_args()

    if args.provider == "custom" and not args.base_url:
        raise SystemExit("--provider custom requires --base-url (an OpenAI-compatible chat/completions URL)")

    try:
        with open(args.body) as f:
            body = json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"body file not found: {args.body}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"invalid JSON in {args.body}: {e}")

    if not isinstance(body, dict):
        raise SystemExit(f"body must be a JSON object, got {type(body).__name__}")

    if args.base_url:
        os.environ["CHECK_CACHE_BASE_URL"] = args.base_url

    caller = CALLERS[args.provider]

    print(f"[1/2] cold call to {args.provider} ...", file=sys.stderr)
    cold = caller(json.loads(json.dumps(body)))  # deep copy
    cold_usage = extract_usage(args.provider, cold)

    time.sleep(args.sleep)

    print(f"[2/2] warm call to {args.provider} ...", file=sys.stderr)
    warm = caller(json.loads(json.dumps(body)))
    warm_usage = extract_usage(args.provider, warm)

    report = {
        "provider": args.provider,
        "cold": cold_usage,
        "warm": warm_usage,
        "hit_rate_cold": round(hit_rate(cold_usage), 2),
        "hit_rate_warm": round(hit_rate(warm_usage), 2),
    }
    print(json.dumps(report, indent=2))

    if warm_usage["cache_read"] == 0:
        print("\nWARN: warm call had zero cache reads. Caching is NOT working "
              "for this request body.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
