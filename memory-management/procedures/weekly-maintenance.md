# Weekly Maintenance Procedure

Run through all steps in order. Report results to the user at the end.

## Step 1: MEMORY.md Health Check

1. Count lines in MEMORY.md (excluding comments and blank lines).
2. If > 50 lines: trigger `procedures/overflow-triage.md` before continuing.
3. Verify every Active Projects entry has a matching file in `memory/projects/`.
4. Remove entries pointing to nonexistent project files.

## Step 2: Daily Log Distillation

Scan `memory/YYYY-MM-DD.md` files from the past 7 days (skip today and yesterday,
which are still actively used).

For each log, extract entries worth persisting:

- Lines prefixed with `[DECISION]`, `[FIX]`, `[PREF]`, `[STATUS]` →
  Append to the relevant `memory/projects/{name}.md` file as a `[P1]` or `[P2]` entry.
- Lines prefixed with `[HIT]` → Skip (consumed by hit-tracker.py).
- Cross-project patterns (same lesson appearing in 2+ project contexts) →
  Flag for knowledge distillation (Step 5).

Do NOT copy raw daily log content into project files. Rewrite each item as a
concise one-liner (≤80 chars) with proper `[Px][date][src:x]` format.

## Step 3: Review Hit Data

If `memory/.hit-tracker.db` exists, run:

```bash
python3 ~/.openclaw/workspace/skills/memory-management/scripts/hit-tracker.py --report
```

Review the output:

- **30+ days zero hits on P1 entries** → Suggest demotion to P2.
  Ask user for confirmation before changing priority.
- **7-day window ≥3 hits on P2 entries** → Auto-upgrade to P1.
  Log the upgrade in today's daily log.
- **30-day window ≥15 hits on P1 entries** → Propose P0 upgrade to user.
  P0 upgrades always require explicit user confirmation.

If the database doesn't exist, skip this step and note it in the report.

## Step 4: Project File Cleanup

For each file in `memory/projects/`:

1. **Dedup**: Identify entries describing the same thing in different words.
   Merge into the most recent/complete version. Sum their hit counts if tracked.
2. **Stale P2 cleanup**: P2 entries older than 30 days with zero hits → move to
   `memory/archive/YYYY-MM.md` with source annotation.
3. **Conflict scan**: Look for entries that contradict each other
   (e.g., "uses PostgreSQL" vs "migrated to MySQL"). Flag for user review.
   Follow `procedures/conflict-check.md` for resolution.

## Step 5: Knowledge Distillation Check

Review recent daily logs and project file changes. If you notice:

- The same lesson/pattern appearing across 2+ projects
- A general principle that was discovered through a specific incident
- A reusable technique that transcends any single project

→ Trigger `procedures/knowledge-distill.md` for those items.

## Step 6: Sync MEMORY.md Active Projects

For each project in `memory/projects/`:
1. Read the file and identify the current top-priority status item.
2. Update the one-liner in MEMORY.md's Active Projects section.
3. If a project has had zero activity for 30+ days, suggest archiving to user.

Project archival flow (only after user confirms):
1. Remove from MEMORY.md Active Projects.
2. Move `memory/projects/{name}.md` → `memory/archive/project-{name}.md`.
3. The file remains searchable via memory_search.

## Step 7: Generate Report

Output a maintenance summary:

```
📊 Weekly Memory Maintenance Report — YYYY-MM-DD

MEMORY.md: XX/50 lines
Project files: N files, total XX entries
Knowledge base: N entries
Archive: N entries

Changes made:
- Distilled X entries from daily logs → project files
- Upgraded X entries (P2→P1)
- Demoted X entries (P1→P2) [pending user confirmation: Y]
- Merged X duplicate entries
- Archived X expired entries
- Flagged X conflicts for review

Proposed actions (need your approval):
- [list any P0 upgrades, project archival, conflict resolutions]
```
