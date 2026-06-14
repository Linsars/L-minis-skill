# Conflict Check Procedure

Detects and resolves contradictions between memory entries.

## When to Run

- Before overwriting any existing memory entry
- During weekly maintenance (Step 4)
- User says "检查冲突" / "check conflicts"
- memoryFlush writes new information that might contradict existing entries

## Conflict Types

### Type 1: Fact Update (most common)

Old: `- [P1][2026-01-10][src:user] Tech stack: Go + PostgreSQL`
New: `- [P1][2026-02-12][src:user] Migrated database to CockroachDB`

**Resolution**: This isn't a conflict — it's an evolution. Replace old with new.
Move old entry to archive with annotation:

```
- [P1][2026-01-10][src:user] Tech stack: Go + PostgreSQL [SUPERSEDED 2026-02-12: migrated to CockroachDB]
```

### Type 2: Genuine Contradiction

Old: `- [P1][2026-02-01][src:user] Prefers short responses`
New: `- [P1][2026-02-12][src:infer] User seems to want detailed explanations`

**Resolution**: Apply trust hierarchy:
1. `src:user` always wins over `src:infer` and `src:system`
2. Between same-source entries, more recent wins
3. Between `src:user` entries of similar recency, flag for user review

In this example: keep the `src:user` entry. Discard the `src:infer` entry.
If the inference might be valid (user's preference genuinely changed), ask
the user.

### Type 3: Partial Overlap

Old: `- [P1][2026-01-15][src:user] Uses Vim for all editing`
New: `- [P1][2026-02-12][src:user] Switched to Cursor for Go projects`

**Resolution**: Both are true — the scope is different. Merge:

```
- [P1][2026-02-12][src:user] Uses Cursor for Go, Vim for everything else
```

## Process

### 1. Detect

When writing a new entry, search for existing entries with overlapping topics:

```
memory_search "{key terms from the new entry}"
```

Also scan the target file directly for entries about the same subject.

### 2. Classify

For each potential conflict, determine the type (1, 2, or 3 above).

### 3. Resolve

| Type | src:user vs src:user | src:user vs src:infer | src:infer vs src:infer |
|------|---------------------|----------------------|----------------------|
| Fact Update | Replace, archive old with [SUPERSEDED] | Replace infer with user | Replace older with newer |
| Contradiction | **Ask user** | Keep user, discard infer | **Ask user** |
| Partial Overlap | Merge both into one entry | Merge, prioritize user phrasing | Merge, note uncertainty |

### 4. Log

Record all conflict resolutions in today's daily log:

```
- [CONFLICT-RESOLVED] Merged: "Uses Vim" + "Switched to Cursor for Go" → combined entry in memory/projects/tools.md
```

For unresolved conflicts (needing user input), mark both entries:

```
- [P1][2026-02-12][src:user][CONFLICT:needs-review] New claim about X
```

And flag in today's log:

```
- [CONFLICT-PENDING] Two entries about editor preference contradict. See memory/projects/tools.md. Needs user decision.
```
