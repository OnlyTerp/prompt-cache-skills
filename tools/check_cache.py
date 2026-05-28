#!/usr/bin/env python3
"""
check_cache.py — fire a request body at a provider twice and report
cache behavior.

Usage:
  check_cache.py --provider anthropic --body req.json
  check_cache.py --provider openai    --body req.json
  check_cache.py --provider gemini    --body req.json

Reads provider credentials from env:
  ANTHROPIC_API_KEY
  OPENAI_API_KEY
  GEMINI_API_KEY (or GOOGLE_API_KEY)

For Bedrock/Vertex, configure via the respective SDKs' standard env vars
(AWS_*, GOOGLE_APPLICATION_CREDENTIALS) and use --provider bedrock /
--provider vertex.

The script:
  1. Sends the request body once (cold).
  2. Waits 1 second.
  3. Sends the same body again (warm).
  4. Prints a small report:
       - Cold turn cache_creation / cache_read / input
       - Warm turn cache_creation / cache_read / input
       - Computed hit rate

It does NOT modify the request body. If you want to test what *your*
harness sends, capture a request via mitmproxy, save the body to
req.json, and run this against it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

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


def call_openai(body: dict[str, Any]) -> dict[str, Any]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY not set")
    headers = {
        "authorization": f"Bearer {key}",
        "content-type": "application/json",
    }
    return _http("https://api.openai.com/v1/chat/completions", headers, body)


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


CALLERS = {
    "anthropic": call_anthropic,
    "openai": call_openai,
    "gemini": call_gemini,
}


def extract_usage(provider: str, resp: dict[str, Any]) -> dict[str, int]:
    if provider == "anthropic":
        u = resp.get("usage", {})
        return {
            "input": u.get("input_tokens", 0),
            "cache_creation": u.get("cache_creation_input_tokens", 0),
            "cache_read": u.get("cache_read_input_tokens", 0),
            "output": u.get("output_tokens", 0),
        }
    if provider == "openai":
        u = resp.get("usage", {})
        details = u.get("prompt_tokens_details", {}) or {}
        return {
            "input": u.get("prompt_tokens", 0),
            "cache_creation": 0,  # OpenAI has no write premium / explicit creation count
            "cache_read": details.get("cached_tokens", 0),
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
    ap.add_argument("--sleep", type=float, default=1.0, help="seconds between cold and warm")
    args = ap.parse_args()

    try:
        with open(args.body) as f:
            body = json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"body file not found: {args.body}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"invalid JSON in {args.body}: {e}")

    if not isinstance(body, dict):
        raise SystemExit(f"body must be a JSON object, got {type(body).__name__}")

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
