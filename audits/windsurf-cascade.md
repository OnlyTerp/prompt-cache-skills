# Windsurf / Cascade

| Field | Value |
|-------|-------|
| Repo | closed-source desktop/editor backend; local VS Code-derived app install |
| Audited commit | local Windsurf launcher commit `a5d3f1ff990cabc0e8001cce6642bdb7ad429e73` |
| Audit date | `2026-05-27` |
| Auditor | `terp` |
| Provider tested | Codeium/Windsurf managed backend |
| Model tested | n/a (desktop chat not exercised from CLI) |
| Verdict | **unverified (closed desktop + managed backend)** |

## Summary

Windsurf/Cascade is a closed-source desktop/editor harness backed by Codeium
services. The local install is a VS Code-derived Electron app with a WSL launcher,
and the product metadata identifies the bundled Windsurf application and the
`codeium.windsurf` extension trust override. No local source path exposes
provider request construction or prompt-cache fields. A non-interactive model
turn was not available from the WSL launcher, so this audit does not claim a
working or broken cache verdict.

The important distinction from Devin CLI is that Windsurf was not exercised on
the wire in this pass. Devin's raw CLI model RPC was captured as Codeium Connect
protobuf; Windsurf likely uses related managed services, but that should be
verified with an editor-session capture rather than assumed.

## Source inspection

### Local launcher

The WSL launcher is a VS Code-style shell wrapper:

```text
file: AppData/Local/Programs/Windsurf/bin/windsurf
lines: 9-16, 38-61
```

Key local metadata:

```bash
COMMIT="a5d3f1ff990cabc0e8001cce6642bdb7ad429e73"
APP_NAME="windsurf"
QUALITY="stable"
NAME="Windsurf"
SERVERDATAFOLDER=".windsurf-server"
```

When invoked from WSL it resolves the Windows Electron app and, if available,
routes through the Remote WSL extension script.

### Product metadata

`resources/app/product.json` identifies Windsurf as the application and includes
Windsurf/Codeium-specific configuration:

```jsonc
{
  "nameShort": "Windsurf",
  "applicationName": "windsurf",
  "serverApplicationName": "windsurf-server",
  "serverDataFolderName": ".windsurf-server",
  "extensionUntrustedWorkspaceSupport": {
    "codeium.windsurf": { "override": true }
  },
  "commandPaletteSuggestedCommandIds": [
    "windsurf.prioritized.chat.open"
  ]
}
```

No local text search under the visible Windsurf/Codeium configuration found
`prompt_cache_key`, `cache_control`, `cached_tokens`, or equivalent provider
cache fields.

## Wire capture

Not performed for a model turn in this pass. The installed launcher opens the
Windows desktop/editor surface; it does not provide a documented one-shot
Cascade prompt command analogous to `devin -p`, `hermes -z`, or `grok -p`.

The redacted mitm environment used for other targets was:

```bash
mitmdump -q -p 8090 -s /tmp/prompt_cache_mitm_summary.py
```

To complete this audit, launch the desktop app with system proxy settings that
route Electron/Codeium traffic through mitmproxy, trigger a small Cascade turn,
and inspect the resulting Codeium/Windsurf request channel.

### Computed hit rate

Not computed. No model-turn wire capture was collected.

## Verdict reasoning

**Unverified.** Windsurf/Cascade is closed and the visible local install does not
include provider request-construction source. The desktop model path was not
captured, so there is no evidence either way for prompt-cache markers or
provider-reported cached-token usage.

## Patch

None. No public target file or verified patchable bug.

## Reproduction

1. Start mitmproxy on loopback port 8090.
2. Configure Windows/Electron proxying for Windsurf or launch the app in an
environment that honors `HTTPS_PROXY=http://127.0.0.1:8090`.
3. Trigger a Cascade prompt in the editor.
4. Inspect Codeium/Windsurf model RPCs for cache-routing fields or usage
counters.
