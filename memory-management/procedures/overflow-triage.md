# Overflow Triage Procedure

Emergency procedure when MEMORY.md exceeds the 50-line limit.

## When to Run

- Weekly maintenance detects > 50 lines
- Agent notices MEMORY.md is too large during normal operation
- After adding entries that push past the limit

## Process

### 1. Count and Categorize

Count actual memory entries (exclude comments, blank lines, section headers).
Group by type:

```
[P0] Core Identity:      XX entries
[P1] Active Projects:    XX entries
[P1] Preferences:        XX entries
Other / untagged:        XX entries
Total:                   XX entries (limit: ~35 entries to stay ≤50 lines with headers)
```

### 2. Triage (in this order)

**Round 1 — Untagged entries**: Any entry without `[P0]` or `[P1]` tag.
Move to today's daily log for reprocessing, or to `memory/archive/` if clearly stale.

**Round 2 — Project details masquerading as index entries**: Active Projects
entries that are more than one line or contain details beyond "name: status, see file".
Move the detail to the project file, keep only the one-liner.

**Round 3 — Preferences that belong in a project**: Preferences that only apply
to one project (e.g., "WonderTok uses UUID v7 for primary keys"). Move to the
relevant project file.

**Round 4 — Stale project entries**: Active Projects entries pointing to projects
with zero activity in 30+ days. Suggest archival to user.

**Round 5 — P0 review (rare)**: If P0 entries exceed 10, review whether any have
become obsolete. P0 removal requires explicit user confirmation.

### 3. Execute

After each round, recount. Stop as soon as total is ≤50 lines (with headers).
If still over after all 5 rounds, alert the user:

```
⚠️ MEMORY.md is at XX lines after triage. The 50-line limit requires
removing more entries. Here are candidates ranked by least impact:

1. [entry] — last referenced X days ago
2. [entry] — could move to memory/knowledge/
3. [entry] — duplicate of entry in memory/projects/xxx.md

Which should I move out?
```

### 4. Verify Structure

After triage, verify MEMORY.md still has all required sections:
- `## Core Identity` (with ≥1 P0 entry)
- `## Active Projects`
- `## Preferences`
- `## Memory Index`

If any section was accidentally emptied, restore from backup or flag.
