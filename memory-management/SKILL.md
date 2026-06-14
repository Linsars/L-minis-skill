---
name: memory-management
description: >
  Maintain your agent's memory system across sessions. Use this skill whenever
  memory needs attention: MEMORY.md approaching/exceeding 50 lines, daily logs
  piling up, duplicate entries, contradicting information, or cross-project
  patterns worth distilling into reusable knowledge. Triggers on: "记忆维护",
  "memory maintenance", "整理记忆", "清理记忆", "提炼知识", "knowledge distill",
  "检查冲突", "conflict check", "记忆迁移", "migrate memory". Proactively suggest
  this skill when MEMORY.md grows beyond 40 lines or when the same debugging
  pattern appears across multiple projects. Don't wait for the user to ask —
  if you notice memory bloat or repeated patterns during conversation, recommend
  running maintenance.
---

# Memory Management Skill

Maintains a three-layer memory system designed around OpenClaw's constraints.

## Why This Architecture?

OpenClaw injects MEMORY.md into every conversation turn, which means it must stay tiny (≤50 lines) to avoid wasting context. But you need more than 50 lines of memory to work effectively across sessions. The solution: MEMORY.md holds only a skeleton (core identity + project pointers), while detailed context lives in `memory/` and gets retrieved on-demand via `memory_search`.

This design lets you maintain rich, persistent memory without paying the context cost every turn.

## Architecture

```
MEMORY.md (≤50 lines, injected every turn)
  ├── Core Identity [P0] — permanent, no date
  ├── Active Projects [P1] — one-liner + pointer to memory/projects/
  ├── Preferences [P1] — cross-project
  └── Memory Index — navigation for memory_search

memory/ (searchable, not auto-injected)
  ├── projects/*.md     — per-project detailed context
  ├── knowledge/*.md    — cross-project distilled knowledge
  ├── archive/*.md      — retired memories (still searchable)
  ├── compressed/*.md   — compressed old logs
  └── YYYY-MM-DD.md     — daily logs (today+yesterday auto-loaded)
```

## Entry Format

See `references/format-guide.md` for detailed explanation of the format, priority levels (P0/P1/P2), and source attribution (user/infer/system). Quick reference:

```
- [P0-2][YYYY-MM-DD][src:user|infer|system] content (≤80 chars)
```

P0 entries in MEMORY.md omit the date: `- [P0] content`

## Tasks

Read the relevant procedure file before executing any task. Each procedure explains the reasoning behind its steps, not just the mechanics.

| Task | When | Procedure |
|------|------|-----------|
| Weekly maintenance | User says "记忆维护" / Sunday heartbeat | `procedures/weekly-maintenance.md` |
| Daily log compression | User says "压缩日志" / heartbeat finds >7-day logs | `procedures/daily-compress.md` |
| Knowledge distillation | User says "提炼知识" / weekly maintenance finds patterns | `procedures/knowledge-distill.md` |
| Conflict check | Before overwriting existing memory / user says "检查冲突" | `procedures/conflict-check.md` |
| Initial migration | User says "记忆迁移" / first-time setup | `procedures/migration.md` |
| MEMORY.md overflow | MEMORY.md exceeds 50 lines | `procedures/overflow-triage.md` |

## Automation

Cron scripts handle routine maintenance automatically. See `references/automation.md` for details on what runs when and how to check their output during weekly maintenance.

## Templates

Reference templates live in `templates/`. Use them when creating new files:
- `templates/MEMORY.md.example` — skeleton file structure
- `templates/project-context.md.example` — new project file
- `templates/knowledge-entry.md.example` — new knowledge entry
