# Devin CLI

| Field | Value |
|-------|-------|
| Repo | closed-source CLI (`devin 2026.5.26-1`) |
| Audited commit | local binary `devin 2026.5.26-1 (8bbb9324)` |
| Audit date | `2026-05-27` |
| Auditor | `terp` |
| Provider tested | Devin/Codeium managed backend (`server.codeium.com`, `api.devin.ai`) |
| Model tested | `swe-1-6-fast` in raw mode |
| Verdict | **unverified (opaque managed backend)** |

## Summary

Devin CLI is a managed, closed-source harness. Local documentation confirms that
CLI HTTP traffic honors proxy settings, and a raw-mode `devin -p` run was
successfully captured through mitmproxy. The captured model path uses
Codeium/Devin Connect protobuf (`application/connect+proto`) rather than a
provider JSON body, so the redacted capture cannot inspect `cache_control`,
`prompt_cache_key`, or usage cache counters.

This is not evidence that caching is broken. It means prompt-cache behavior is
server-side/opaque from the public CLI surface tested here.

## Source inspection

The local `devin` command is a workstation wrapper, not upstream source. It
routes plain `devin` through a BYOK local proxy by default and can be bypassed
with `DEVIN_BYOK=0`:

```text
file: ~/.local/bin/devin
lines: 15-24, 37-41
```

Relevant wrapper behavior:

```bash
REAL_DEVIN_BIN="${DEVIN_REAL_BIN:-$HOME/.local/share/devin/cli/_versions/current/bin/devin}"
export DEVIN_BYOK="${DEVIN_BYOK:-1}"
if [ "$DEVIN_BYOK" = "1" ]; then
  exec "$HOME/devin-local-proxy/run-devin-with-byok.sh" "$@"
fi
exec "$REAL_DEVIN_BIN" "$@"
```

For this audit, the capture used raw mode (`DEVIN_BYOK=0`) so the result reflects
Cognition/Devin CLI traffic rather than Terp's local BYOK shim.

The public Devin CLI docs document proxy handling:

```text
file: docs/reference/configuration/config-file.mdx
lines: 257-273
```

Key point: `proxy.mode = "system"` respects `HTTP_PROXY`, `HTTPS_PROXY`, and
`ALL_PROXY`; `manual` can force an explicit proxy URL.

## Wire capture

Captured with:

```bash
mitmdump -q -p 8090 -s /tmp/prompt_cache_mitm_summary.py
DEVIN_BYOK=0 DEVIN_NO_CGROUP=1 \
HTTPS_PROXY=http://127.0.0.1:8090 \
HTTP_PROXY=http://127.0.0.1:8090 \
ALL_PROXY=http://127.0.0.1:8090 \
SSL_CERT_FILE=$HOME/.mitmproxy/mitmproxy-ca-cert.pem \
REQUESTS_CA_BUNDLE=$HOME/.mitmproxy/mitmproxy-ca-cert.pem \
devin -p "Reply with exactly: OK" --model swe-1-6-fast
```

The command completed with `OK`.

### Captured request highlights

The redacted mitm summary showed these relevant calls:

```jsonc
{ "host": "api.devin.ai", "method": "GET", "path": "/v3/self", "status_code": 200 }
{ "host": "api.devin.ai", "method": "POST", "path": "/v3/organizations/.../skills/events", "status_code": 200 }
{
  "host": "server.codeium.com",
  "method": "POST",
  "path": "/exa.api_server_pb.ApiServerService/GetChatMessage",
  "request_headers": {
    "content-type": "application/connect+proto"
  },
  "status_code": 200
}
```

The request body is protobuf, not JSON. The redacted JSON extractor therefore
reported it as `"<non-json-or-empty>"`.

### Computed hit rate

Not computed. The public/raw CLI wire shape does not expose provider cache
fields in inspectable JSON.

## Verdict reasoning

**Unverified (opaque managed backend).** Devin CLI routes model traffic through a
managed Codeium/Devin protobuf service. From the local CLI surface we can prove
that traffic is proxyable and identify the RPC endpoint, but not inspect provider
prompt-cache markers or token usage. Any cache implementation is either inside
that managed service or behind an internal provider boundary.

## Patch

None. No new skill added: there is no public harness source path or verified
patchable cache bug.

## Reproduction

Run the mitm command above in raw mode (`DEVIN_BYOK=0`). If a future Devin build
adds JSON debug dumps or exposes provider usage counters, re-run this audit and
record `cached_tokens` / `cache_read_input_tokens` equivalents.
