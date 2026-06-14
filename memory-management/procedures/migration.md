# Migration Procedure

Restructures an existing MEMORY.md into the multi-layer memory system.
Run once during initial setup, or when the user wants to restructure.

## Prerequisites

- Back up existing MEMORY.md: `cp MEMORY.md MEMORY.md.backup`
- Ensure `memory/` directory exists: `mkdir -p memory/{projects,knowledge,archive}`

## Process

### Step 1: Categorize Every Entry

Read the current MEMORY.md. For each entry, classify:

| Category | Destination | Criteria |
|----------|-------------|----------|
| Core identity | Stay in MEMORY.md as [P0] | Who the user is, permanent preferences, safety rules, work mode |
| Active project detail | `memory/projects/{name}.md` as [P1] | Architecture, tech stack, current status, blockers |
| Cross-project preference | Stay in MEMORY.md as [P1] | Applies to all projects: response style, code style, language |
| Reusable knowledge | `memory/knowledge/{topic}.md` as [P1] | Lessons, patterns, techniques applicable across contexts |
| Expired/completed | `memory/archive/migration.md` as [P2] | Old projects, resolved issues, outdated info |
| Temporary/one-time | `memory/archive/migration.md` as [P2] | Single events, debug notes older than 30 days |

Present the classification plan to the user BEFORE executing:

```
📋 Migration Plan

Staying in MEMORY.md (XX entries):
  [P0] Core identity: X entries
  [P1] Active project index: X one-liners
  [P1] Cross-project preferences: X entries

Moving to memory/projects/ (XX entries):
  wondertok.md: X entries
  rpa.md: X entries
  ...

Moving to memory/knowledge/ (XX entries):
  {topic}.md: X entries
  ...

Moving to memory/archive/migration.md (XX entries):
  Expired: X entries
  Temporary: X entries

Proceed? (y/n)
```

### Step 2: Create Project Files

For each active project identified in Step 1:

1. Create `memory/projects/{name}.md` using the template:
   ```bash
   cat skills/memory-management/templates/project-context.md.example
   ```
2. Move relevant entries from MEMORY.md into the appropriate sections.
3. Reformat entries to include `[src:user]` or `[src:infer]` tags.
   If uncertain about source, default to `[src:user]` for entries that
   clearly reflect the user's own statements, `[src:infer]` for everything else.

### Step 3: Build the Skeleton MEMORY.md

Rewrite MEMORY.md using the template:
```bash
cat skills/memory-management/templates/MEMORY.md.example
```

For each active project, create a one-liner:
```
- [P1][YYYY-MM-DD] ProjectName: one-sentence status, see memory/projects/xxx.md
```

### Step 4: Add Memory Index

Append to MEMORY.md:

```markdown
## Memory Index
- Project context: memory/projects/*.md
- Cross-project knowledge: memory/knowledge/*.md
- Retired memories: memory/archive/*.md
```

### Step 5: Verify

1. Count MEMORY.md lines — must be ≤50.
2. Verify each project file is searchable: `memory_search "{project name}"`.
3. Verify archive is searchable: `memory_search "{archived topic}"`.
4. Delete backup only after user confirms everything looks right.

### Step 6: Install Cron Scripts

```bash
bash ~/.openclaw/workspace/skills/memory-management/scripts/install-cron.sh
```

Report to user:
```
✅ Migration Complete

MEMORY.md: XX/50 lines (was: YYY lines)
Project files created: N
Knowledge entries: N
Archived entries: N
Cron scripts: installed (daily eviction + weekly sync)

Token savings estimate: ~XX% reduction in per-turn memory injection
```

## Backward Compatibility

For entries without `[src:]` tags (pre-migration), default behavior:
- Entries are treated as `src:user` for conflict resolution
- Eviction scripts treat missing `src` as neutral (no bonus/penalty)
- The `[src:]` tag gets added naturally when entries are next updated
