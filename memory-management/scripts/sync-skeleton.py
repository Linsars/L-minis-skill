#!/usr/bin/env python3
"""
sync-skeleton.py — Sync MEMORY.md Active Projects index from memory/projects/ files.

Reads each project file, extracts the most recent [P1] entry as a one-liner,
and updates the Active Projects section in MEMORY.md.

Usage:
    python3 sync-skeleton.py              # Execute sync
    python3 sync-skeleton.py --dry-run    # Preview changes without writing

Designed to run via cron weekly on Sundays at 04:30.
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE",
    Path.home() / ".openclaw" / "workspace"))
MEMORY_FILE = WORKSPACE / "MEMORY.md"
PROJECTS_DIR = WORKSPACE / "memory" / "projects"

ENTRY_RE = re.compile(r'^\s*-\s*\[P([012])\]\[(\d{4}-\d{2}-\d{2})\](?:\[src:\w+\])?\s*(.+)$')
DRY_RUN = "--dry-run" in sys.argv


def get_project_summaries():
    """Extract a one-liner from each project file."""
    if not PROJECTS_DIR.exists():
        return []

    summaries = []
    for f in sorted(PROJECTS_DIR.iterdir()):
        if not f.name.endswith('.md'):
            continue

        project_name = f.stem
        latest_date = None
        latest_content = None

        # Find the most recent P1 entry (by date)
        with open(f, 'r') as fh:
            for line in fh:
                m = ENTRY_RE.match(line.strip())
                if m and m.group(1) == '1':  # P1 only
                    date_str = m.group(2)
                    if latest_date is None or date_str > latest_date:
                        latest_date = date_str
                        latest_content = m.group(3)

        # Fallback: use first non-header, non-blank line
        if not latest_content:
            with open(f, 'r') as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('<!--'):
                        latest_content = line.lstrip('- ').strip()[:60]
                        latest_date = datetime.now().strftime('%Y-%m-%d')
                        break

        if latest_content and latest_date:
            summaries.append({
                'name': project_name,
                'date': latest_date,
                'summary': latest_content[:60],
                'path': f"memory/projects/{f.name}",
            })

    return summaries


def update_memory_file(summaries):
    """Replace the Active Projects section in MEMORY.md."""
    if not MEMORY_FILE.exists():
        print(f"⚠️  {MEMORY_FILE} does not exist. Skipping.")
        return

    content = MEMORY_FILE.read_text()

    # Build new Active Projects section
    new_lines = ["## Active Projects"]
    new_lines.append("<!-- One-liner + pointer only. Details in memory/projects/*.md -->")
    for s in summaries:
        new_lines.append(
            f"- [P1][{s['date']}] {s['name']}: {s['summary']}, see {s['path']}"
        )

    new_section = '\n'.join(new_lines)

    # Replace existing section (from ## Active Projects to next ## or EOF)
    pattern = r'## Active Projects\n.*?(?=\n## |\Z)'
    new_content, count = re.subn(pattern, new_section, content, flags=re.DOTALL)

    if count == 0:
        print("⚠️  Could not find '## Active Projects' section in MEMORY.md.")
        print("   Add the section header manually, then rerun.")
        return

    if DRY_RUN:
        print("--- Proposed Active Projects Section ---")
        print(new_section)
        print("\n--- End ---")
    else:
        # Atomic write
        tmp = str(MEMORY_FILE) + f'.tmp.{os.getpid()}'
        with open(tmp, 'w') as f:
            f.write(new_content)
        os.replace(tmp, str(MEMORY_FILE))
        print(f"✅ Updated {len(summaries)} project entries in MEMORY.md")

    # Line count check
    final_lines = new_content.split('\n')
    content_lines = [l for l in final_lines
                     if l.strip() and not l.strip().startswith('<!--') and not l.strip().startswith('#')]
    if len(content_lines) > 50:
        print(f"⚠️  WARNING: MEMORY.md has {len(content_lines)} content lines (limit: 50)")


def main():
    summaries = get_project_summaries()
    if not summaries:
        print("No project files found in memory/projects/. Nothing to sync.")
        return

    print(f"Found {len(summaries)} project file(s):")
    for s in summaries:
        print(f"  {s['name']}: {s['summary'][:50]}...")

    update_memory_file(summaries)


if __name__ == "__main__":
    main()
