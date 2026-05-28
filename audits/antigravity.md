# Google Antigravity

| Field | Value |
|-------|-------|
| Repo | closed-source desktop app; visible local bundle includes `chrome-devtools-mcp` |
| Audited commit | local Windows app install, updater URL `antigravity-hub-auto-updater-974169037036.us-central1.run.app/manifest/` |
| Audit date | `2026-05-27` |
| Auditor | `terp` |
| Provider tested | Google/Antigravity managed backend |
| Model tested | n/a (desktop agent turn not exercised from CLI) |
| Verdict | **unverified (closed desktop + no model capture)** |

## Summary

Antigravity is installed locally as a Windows desktop application, but no
non-interactive CLI or public desktop source was available from this workstation
pass. The visible unpacked resources show a bundled `chrome-devtools-mcp`
package, which is tool/browser infrastructure rather than the agent model
transport. No local file exposed Gemini `cachedContents`, OpenAI-style
`prompt_cache_key`, Anthropic `cache_control`, or provider usage counters.

Because no model turn was captured and no provider request-construction source
was available, this audit is **unverified**. Do not infer Gemini implicit or
explicit caching behavior from the product name alone.

## Source inspection

### Local install evidence

The app is installed at:

```text
AppData/Local/Programs/Antigravity/Antigravity.exe
```

Windows file metadata did not expose `ProductVersion` or `FileVersion` for the
local executable.

The updater configuration is:

```yaml
provider: generic
url: https://antigravity-hub-auto-updater-974169037036.us-central1.run.app/manifest/
updaterCacheDirName: antigravity-updater
```

Visible unpacked Node resources include `chrome-devtools-mcp`:

```json
{
  "name": "chrome-devtools-mcp",
  "version": "0.23.0",
  "repository": "ChromeDevTools/chrome-devtools-mcp",
  "author": "Google LLC",
  "devDependencies": {
    "@google/genai": "^1.37.0",
    "puppeteer": "24.42.0"
  }
}
```

That package is an MCP/devtools integration. It does not prove anything about
Antigravity's agent prompt construction or provider cache settings.

### What was not found

Local visible files did not contain source-level evidence for:

- Gemini explicit cache handles (`cachedContents` / `cachedContent`),
- OpenAI Responses `prompt_cache_key`,
- Anthropic `cache_control`,
- response usage counters such as `cached_tokens` or `cachedContentTokenCount`.

## Wire capture

Not performed for a model turn. Unlike `hermes -z`, `devin -p`, or `grok -p`, no
local one-shot Antigravity command surface was found during this pass. Launching
and driving the Windows desktop UI through mitmproxy was outside the bounded
capture run.

The mitm environment used for the other targets was:

```bash
mitmdump -q -p 8090 -s /tmp/prompt_cache_mitm_summary.py
```

### Computed hit rate

Not computed. No model-turn request/response was captured.

## Verdict reasoning

**Unverified.** Antigravity is closed-source at the desktop layer and the visible
local files only establish the app install plus bundled devtools/MCP support.
There is no source or wire evidence in this audit showing whether the agent uses
Gemini implicit caching, Gemini explicit `cachedContents`, OpenAI
`prompt_cache_key`, or any other provider-specific cache mechanism.

## Patch

None. No public target file or verified patchable bug.

## Reproduction

To complete this audit:

1. Start mitmproxy on loopback port 8090.
2. Configure the Windows Antigravity desktop app to trust the mitm CA and route
   HTTPS through the proxy.
3. Trigger two identical small agent turns in the same workspace/session.
4. Inspect model calls for `cachedContents` / `cachedContentTokenCount` if the
   backend is Gemini, or the provider-specific cache fields if another backend
   is selected.
