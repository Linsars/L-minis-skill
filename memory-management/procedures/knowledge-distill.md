# Knowledge Distillation Procedure

Extracts cross-project, reusable knowledge from project files and daily logs
into `memory/knowledge/` entries.

## When to Run

- Weekly maintenance identifies cross-project patterns
- User says "提炼知识" / "distill knowledge"
- Same lesson appears in 2+ different project contexts

## What Qualifies as Knowledge

Knowledge entries capture **reusable principles** that transcend any single project.

✅ Good candidates:
- A debugging technique that solved problems in multiple projects
- A configuration pitfall encountered repeatedly (e.g., PostgreSQL RLS ordering)
- An architectural pattern that proved effective across contexts
- A tool usage insight (e.g., "FFmpeg streaming mode prevents OOM on large files")

❌ Not knowledge (stays in project files):
- Project-specific architecture decisions
- Current project status or blockers
- One-time events that haven't recurred

## Process

### 1. Identify Candidates

Scan recent project file additions and daily logs for:
- Similar entries appearing in 2+ project files
- Entries tagged `[FIX]` with solutions applicable beyond the original context
- Patterns you've seen the user encounter repeatedly

### 2. Check for Existing Knowledge

Before creating a new entry, search `memory/knowledge/` to see if a related
entry already exists. If so, update/enrich the existing one rather than creating
a duplicate.

```bash
# Use memory_search to check
memory_search "the topic you're about to write about"
```

### 3. Write the Knowledge Entry

Create or update a file in `memory/knowledge/`:

**Filename**: `memory/knowledge/{topic-slug}.md` (lowercase, hyphens, descriptive)

**Structure**:

```markdown
# {Topic Title}

## Principle
- [P1][YYYY-MM-DD][src:system] One-line distilled principle (≤80 chars)

## Context
Why this matters. When you'd encounter this. 2-3 sentences max.

## Details
- Specific technical details
- Configuration examples if applicable
- What NOT to do (common mistakes)

## Source Projects
- First encountered in: {project-name} on {date}
- Also seen in: {project-name} on {date}
```

Keep the entire file under 30 lines. This isn't documentation — it's distilled
wisdom that memory_search can retrieve.

### 4. Update MEMORY.md Index

If this is the first entry in `memory/knowledge/`, ensure MEMORY.md's
Memory Index section includes:

```
- Cross-project knowledge: memory/knowledge/*.md
```

### 5. Remove Redundancy from Project Files

After distilling knowledge, the original entries in project files can be
simplified. Replace detailed explanations with a reference:

```
- [P2][2026-02-12][src:system] FFmpeg OOM fix — see memory/knowledge/ffmpeg-streaming.md
```

This keeps project files focused on project-specific context.
