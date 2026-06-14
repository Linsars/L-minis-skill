#!/usr/bin/env python3
"""
log-compress.py — Compress daily logs older than 7 days.

Extracts tagged key lines ([DECISION], [FIX], [PREF], [STATUS], [P0], [P1]),
saves them to monthly compressed files, and moves originals to archive/.

Usage:
    python3 log-compress.py              # Execute compression
    python3 log-compress.py --dry-run    # Preview without writing

Designed to run via cron weekly on Sundays at 04:00.
"""

import os
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE",
    Path.home() / ".openclaw" / "workspace"))
MEMORY_DIR = WORKSPACE / "memory"
ARCHIVE_DIR = MEMORY_DIR / "archive"
COMPRESSED_DIR = MEMORY_DIR / "compressed"
DAYS_TO_KEEP_RAW = 7
DRY_RUN = "--dry-run" in sys.argv

DATE_FILE_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})\.md$')
KEY_PREFIXES = ['[DECISION]', '[FIX]', '[PREF]', '[STATUS]']
ENTRY_RE = re.compile(r'^\s*-\s*\[P[01]\]')
COMPRESSED_MARKER = '<!-- compressed'


def get_log_files():
    """Find date-formatted log files in memory/."""
    files = []
    for f in MEMORY_DIR.iterdir():
        m = DATE_FILE_RE.match(f.name)
        if m:
            date = datetime.strptime(m.group(1), '%Y-%m-%d')
            files.append((date, f))
    return sorted(files, key=lambda x: x[0])


def is_already_compressed(filepath):
    """Check if file has already been compressed."""
    try:
        with open(filepath, 'r') as f:
            first_line = f.readline()
            return COMPRESSED_MARKER in first_line
    except OSError:
        return False


def extract_key_lines(filepath):
    """Extract lines worth preserving from a daily log."""
    key_lines = []
    with open(filepath, 'r') as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            # Skip the compressed marker and headers
            if stripped.startswith('<!--') or stripped.startswith('#'):
                continue
            # Match tagged lines
            if any(prefix in stripped for prefix in KEY_PREFIXES):
                key_lines.append(stripped)
            # Match P0/P1 formatted entries
            elif ENTRY_RE.match(stripped):
                key_lines.append(stripped)
    return key_lines


def compress():
    cutoff = datetime.now() - timedelta(days=DAYS_TO_KEEP_RAW)
    log_files = get_log_files()
    old_logs = [(d, f) for d, f in log_files
                if d < cutoff and not is_already_compressed(f)]

    if not old_logs:
        print("No uncompressed logs older than 7 days. Nothing to do.")
        return

    print(f"Found {len(old_logs)} log(s) to compress")

    # Group by month
    monthly = {}
    for date, filepath in old_logs:
        month_key = date.strftime('%Y-%m')
        monthly.setdefault(month_key, []).append((date, filepath))

    total_extracted = 0
    total_archived = 0

    for month, files in sorted(monthly.items()):
        all_key_lines = []

        for date, filepath in files:
            key_lines = extract_key_lines(filepath)
            if key_lines:
                all_key_lines.append(f"\n### {date.strftime('%Y-%m-%d')}")
                all_key_lines.extend(key_lines)

        extracted = len([l for l in all_key_lines if not l.startswith('\n###')])
        total_extracted += extracted

        print(f"\n📅 {month}: {len(files)} file(s) → {extracted} key line(s)")

        if DRY_RUN:
            for line in all_key_lines[:10]:
                print(f"   {line[:70]}")
            if len(all_key_lines) > 10:
                print(f"   ... and {len(all_key_lines) - 10} more")
            continue

        # Write compressed summary
        if all_key_lines:
            COMPRESSED_DIR.mkdir(parents=True, exist_ok=True)
            compressed_file = COMPRESSED_DIR / f"{month}-compressed.md"
            header = f"# {month} Compressed Logs\n"

            with open(compressed_file, 'a') as f:
                if compressed_file.stat().st_size == 0 if compressed_file.exists() else True:
                    f.write(header)
                f.write('\n'.join(all_key_lines) + '\n')

        # Mark original files as compressed (don't delete — archive handles that)
        for date, filepath in files:
            # Add compressed marker
            original_content = filepath.read_text()
            marker = f"<!-- compressed: {datetime.now().strftime('%Y-%m-%d')} -->\n"
            tmp = str(filepath) + f'.tmp.{os.getpid()}'
            with open(tmp, 'w') as f:
                f.write(marker + original_content)
            os.replace(tmp, str(filepath))

        # Move compressed originals to archive
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        for date, filepath in files:
            dest = ARCHIVE_DIR / f"log-{filepath.name}"
            if not dest.exists():
                shutil.move(str(filepath), str(dest))
                total_archived += 1

    prefix = "⚠️  DRY RUN |" if DRY_RUN else "✅"
    print(f"\n{prefix} Extracted: {total_extracted} key lines | Archived: {total_archived} log files")


if __name__ == "__main__":
    compress()
