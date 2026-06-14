# Daily Log Compression Procedure

Compresses daily logs older than 7 days into structured summaries.

## When to Run

- Heartbeat detects `memory/YYYY-MM-DD.md` files older than 7 days
- User explicitly requests "压缩日志" / "compress logs"
- Weekly maintenance Step 2 (partial — this procedure is the full version)

## Process

### 1. Identify Target Logs

List all `memory/YYYY-MM-DD.md` files. Exclude:
- Today's log
- Yesterday's log (still auto-loaded by OpenClaw)
- Files already processed (check for `<!-- compressed -->` marker at top)

### 2. Extract Key Lines

From each target log, extract lines matching these criteria:

| Prefix/Pattern | Destination | Priority |
|---------------|-------------|----------|
| `[DECISION]` | Relevant `memory/projects/` file | P1 |
| `[FIX]` | Relevant `memory/projects/` file | P2 |
| `[PREF]` | MEMORY.md Preferences (if cross-project) or project file | P1 |
| `[STATUS]` | Relevant `memory/projects/` file | P1 |
| `- [P0]` or `- [P1]` | Preserve as-is to destination | As tagged |
| `[HIT]` | Skip (consumed by hit-tracker.py) | — |

Ignore:
- Casual conversation summaries
- Greetings and session bookkeeping
- Information already present in MEMORY.md or project files
- Unresolved discussion without conclusions

### 3. Rewrite as Structured Entries

Each extracted item becomes a properly formatted entry:

```
- [P1][2026-02-12][src:system] Rewritten concise summary ≤80 chars
```

Set `src:system` because these are system-generated compressions. If the original
line was clearly quoting the user (e.g., from a [PREF] capture), use `src:user`.

### 4. Route to Destination Files

- Project-specific items → `memory/projects/{project-name}.md` under the
  appropriate section (Architecture, Current Status, Solved Issues).
- Cross-project items → evaluate for `memory/knowledge/` (see knowledge-distill.md).
- Preference changes → update MEMORY.md Preferences section if significant.

### 5. Mark Source Logs as Compressed

Add `<!-- compressed: YYYY-MM-DD -->` at the top of processed log files.
Do NOT delete the original logs — the `scripts/log-compress.py` cron job handles
archival of compressed logs to `memory/compressed/`.

### 6. Output Summary

```
📋 Log Compression — YYYY-MM-DD

Processed: X daily logs (date range)
Extracted: Y key entries
  → Z routed to project files
  → W routed to knowledge base
  → V updated preferences
Skipped: N entries (duplicates or low-value)
```
