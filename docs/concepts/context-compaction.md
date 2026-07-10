# Context compaction before caching

Prompt caching lowers the price of repeated input. It does not make oversized
context free.

A 60,000-token worker transcript is still expensive to:

- serialize;
- upload;
- write to cache;
- read from cache;
- scan during inference.

Compact before the stable prefix is cached.

## Lossless compression by indirection

For large tool output:

1. Hash the complete text.
2. Write it to a deterministic local artifact.
3. Keep a short head/tail preview in the prompt.
4. Include the artifact path and digest.
5. Tell the worker to reread it only if an omitted detail becomes relevant.

Example:

```text
command output head...

...[compacted; full=/state/context/ctx-a8c90d.txt;
sha256=a8c90d72f4d1; read only if exact detail is needed]...

...command output tail
```

The model context is smaller, but exact evidence remains recoverable.

## Determinism requirements

To preserve cache locality:

- use content-addressed filenames;
- compact a result on its first provider turn;
- never expand or rewrite that preview later;
- keep the same head/tail algorithm and limits;
- collapse identical large results to the same digest reference;
- retain tool ids and call/result adjacency.

Do not use random artifact names in early prompt content.

## Safety

- Store artifacts outside the repository unless they are intended project
  outputs.
- Restrict the directory to the current user.
- Bound file count and retention time.
- Do not spool binary/NUL-containing output as text.
- Never upload spool contents elsewhere automatically.
- Treat artifacts as potentially sensitive local data.

## What not to compact

Preserve:

- images and non-text blocks;
- tool ids;
- tool call/result ordering;
- short error messages;
- current task instructions;
- structured output required by the next tool call.

Long errors can use a larger preview while keeping the complete local artifact.

## Cache interaction

Compaction changes the exact prompt prefix. Apply it before the first cache
write, then keep the compacted representation immutable.

Server-side Responses compaction is complementary. If enabled, preserve the
opaque compaction output item and pass it to the next request unchanged.

## Verification

Measure both correctness and savings:

1. Run the compactor twice on the same transcript.
2. Assert serialized output is byte-identical.
3. Assert every artifact path exists and hashes to the advertised digest.
4. Confirm tool call/result adjacency still validates.
5. Compare request bytes/tokens before and after.
6. Run a task requiring an omitted detail and confirm the agent can reread the
   artifact.

---

_Last verified: 2026-07-10._
