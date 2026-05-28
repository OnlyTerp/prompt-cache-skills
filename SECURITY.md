# Security Policy

## Scope

This repository contains:

- Documentation (`docs/`, `audits/`, `skills/`) — Markdown content with
  no executable code path.
- Zero-dependency Python scripts:
  - `tools/check_cache.py`, which uses only the Python standard library
    and makes HTTPS calls to the user-configured provider (Anthropic /
    OpenAI / Gemini).
  - `tools/check_docs_consistency.py`, which reads local Markdown files
    and verifies audit counts, README table rows, scorecard links, and
    local Markdown links.
- A small Bash wrapper (`tools/audit_harness.sh`).

The scripts do not collect telemetry, do not write outside their
working directory, and do not require any privileged credentials
beyond the API keys the user voluntarily sets in their environment.

## Supported Versions

Latest commit on `main` is supported. There are no released versions
or backports.

## Reporting a Vulnerability

If you find a security issue (a credential being exfiltrated by a
script, a request body being constructed in a way that leaks user
secrets, etc.), please **do not open a public issue**.

Instead:

1. Open a GitHub Security Advisory via the **Security** tab on this
   repository, or
2. Email the maintainer at the address listed in the GitHub profile
   of the repository owner.

We will acknowledge receipt within 7 days and work toward a fix /
disclosure within 30 days.

## What is NOT a vulnerability here

- A skill's diff being out of date with upstream (that's a content
  bug — open a normal issue).
- A provider's API behavior changing (that's an upstream API
  change — open a normal issue).
- An audit verdict you disagree with (open an `audit-correction`
  issue with evidence).
