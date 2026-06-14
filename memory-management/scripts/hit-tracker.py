#!/usr/bin/env python3
"""
hit-tracker.py — Track memory_search recall frequency from OpenClaw session logs.

Parses session JSONL files, finds memory_search tool results, and records which
memory files/lines were recalled. This data feeds the eviction scoring formula.

Usage:
    python3 hit-tracker.py              # Update hit database from session logs
    python3 hit-tracker.py --report     # Print hit summary for weekly maintenance
    python3 hit-tracker.py --dry-run    # Show what would be recorded without writing

Designed to run via cron daily at 03:10.
"""

import json
import sqlite3
import glob
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta

OPENCLAW_DIR = Path(os.environ.get("OPENCLAW_STATE_DIR", Path.home() / ".openclaw"))
WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", OPENCLAW_DIR / "workspace"))
DB_PATH = WORKSPACE / "memory" / ".hit-tracker.db"
PROCESSED_MARKER = DB_PATH.parent / ".hit-tracker-last-run"


def init_db(db_path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hits (
            file_path TEXT NOT NULL,
            line_start INTEGER NOT NULL DEFAULT 0,
            hit_count INTEGER NOT NULL DEFAULT 0,
            last_hit TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            PRIMARY KEY (file_path, line_start)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_hits_last ON hits(last_hit)
    """)
    conn.commit()
    return conn


def find_session_files():
    """Find all session JSONL files across all agents."""
    patterns = [
        str(OPENCLAW_DIR / "agents" / "*" / "sessions" / "*.jsonl"),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    return files


def get_last_run_time():
    """Read the last successful run timestamp to avoid reprocessing."""
    if PROCESSED_MARKER.exists():
        try:
            ts = PROCESSED_MARKER.read_text().strip()
            return datetime.fromisoformat(ts)
        except (ValueError, OSError):
            pass
    return datetime.min


def save_last_run_time():
    PROCESSED_MARKER.write_text(datetime.now().isoformat())


def extract_hits_from_session(jsonl_path, since):
    """
    Parse a session JSONL file and extract memory_search tool result references.

    OpenClaw memory_search returns snippets with file path and line range metadata.
    We look for patterns like: memory/projects/wondertok.md#L15-L20
    or structured result objects with 'file' and 'lineStart' fields.
    """
    hits = []
    file_mtime = datetime.fromtimestamp(os.path.getmtime(jsonl_path))
    if file_mtime < since:
        return hits

    today = datetime.now().strftime("%Y-%m-%d")

    # Patterns to match memory file references in tool results
    # Pattern 1: file#L15-L20 format
    file_line_re = re.compile(r'((?:memory|MEMORY)[/\w.-]*\.md)(?:#L(\d+)(?:-(?:L)?(\d+))?)?')
    # Pattern 2: JSON-ish {"file": "memory/...", "lineStart": N}
    json_file_re = re.compile(r'"file"\s*:\s*"((?:memory|MEMORY)[^"]+\.md)"')
    json_line_re = re.compile(r'"lineStart"\s*:\s*(\d+)')

    in_memory_search_result = False

    try:
        with open(jsonl_path, 'r', errors='replace') as f:
            for line_raw in f:
                line_raw = line_raw.strip()
                if not line_raw:
                    continue
                try:
                    entry = json.loads(line_raw)
                except json.JSONDecodeError:
                    continue

                # Detect memory_search tool results in various formats
                content = entry.get("content", "")

                # Handle content as string
                if isinstance(content, str):
                    if "memory_search" in content:
                        in_memory_search_result = True
                    if in_memory_search_result:
                        for m in file_line_re.finditer(content):
                            hits.append({
                                "file": m.group(1),
                                "line_start": int(m.group(2)) if m.group(2) else 0,
                                "date": today,
                            })
                        # Reset after processing
                        if hits and "tool_result" not in content.lower():
                            in_memory_search_result = False

                # Handle content as list of blocks
                elif isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue

                        block_type = block.get("type", "")
                        block_name = block.get("name", "") or block.get("tool_name", "")
                        block_text = str(block.get("content", "") or block.get("text", ""))

                        if "memory_search" in block_name or "memory_search" in block_type:
                            in_memory_search_result = True

                        if block_type in ("tool_result",) and in_memory_search_result:
                            for m in file_line_re.finditer(block_text):
                                hits.append({
                                    "file": m.group(1),
                                    "line_start": int(m.group(2)) if m.group(2) else 0,
                                    "date": today,
                                })
                            in_memory_search_result = False

    except (OSError, PermissionError) as e:
        print(f"  ⚠️  Cannot read {jsonl_path}: {e}", file=sys.stderr)

    return hits


def update_db(conn, hits):
    """Upsert hit records. Same file+line on the same day counts once."""
    seen = set()
    for hit in hits:
        key = (hit["file"], hit["line_start"], hit["date"])
        if key in seen:
            continue
        seen.add(key)

        conn.execute("""
            INSERT INTO hits (file_path, line_start, hit_count, last_hit, first_seen)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(file_path, line_start) DO UPDATE SET
                hit_count = hit_count + 1,
                last_hit = CASE WHEN ? > last_hit THEN ? ELSE last_hit END
        """, (hit["file"], hit["line_start"], hit["date"], hit["date"],
              hit["date"], hit["date"]))

    conn.commit()


def report(conn):
    """Generate a maintenance-friendly hit report."""
    now_str = datetime.now().strftime("%Y-%m-%d")
    print(f"=== Memory Hit Report — {now_str} ===\n")

    # Summary
    total = conn.execute("SELECT COUNT(*), SUM(hit_count) FROM hits").fetchone()
    print(f"Tracked entries: {total[0]} | Total hits: {total[1] or 0}\n")

    # Zero/cold hits (candidates for demotion)
    print("🔴 Cold memories (30+ days since last hit):")
    rows = conn.execute("""
        SELECT file_path, line_start, hit_count, last_hit
        FROM hits
        WHERE last_hit < date('now', '-30 days') OR hit_count = 0
        ORDER BY last_hit ASC
        LIMIT 20
    """).fetchall()
    if rows:
        for r in rows:
            print(f"   {r[0]}:L{r[1]} | hits={r[2]} | last={r[3]}")
    else:
        print("   (none)")

    # Hot memories (candidates for upgrade)
    print(f"\n🟢 Hot memories (≥3 hits in last 7 days):")
    rows = conn.execute("""
        SELECT file_path, line_start, hit_count, last_hit
        FROM hits
        WHERE last_hit >= date('now', '-7 days') AND hit_count >= 3
        ORDER BY hit_count DESC
        LIMIT 20
    """).fetchall()
    if rows:
        for r in rows:
            print(f"   {r[0]}:L{r[1]} | hits={r[2]} | last={r[3]}")
    else:
        print("   (none)")

    # Very hot (P0 candidates)
    print(f"\n🔥 P0 candidates (≥15 hits in last 30 days):")
    rows = conn.execute("""
        SELECT file_path, line_start, hit_count, last_hit
        FROM hits
        WHERE last_hit >= date('now', '-30 days') AND hit_count >= 15
        ORDER BY hit_count DESC
        LIMIT 10
    """).fetchall()
    if rows:
        for r in rows:
            print(f"   {r[0]}:L{r[1]} | hits={r[2]} | last={r[3]}")
    else:
        print("   (none)")


def main():
    dry_run = "--dry-run" in sys.argv
    do_report = "--report" in sys.argv

    conn = init_db(DB_PATH)

    if do_report:
        report(conn)
        conn.close()
        return

    since = get_last_run_time()
    session_files = find_session_files()
    total_hits = 0

    print(f"Scanning {len(session_files)} session files (since {since.isoformat()[:19]})...")

    for sf in session_files:
        hits = extract_hits_from_session(sf, since)
        if hits:
            if not dry_run:
                update_db(conn, hits)
            basename = os.path.basename(sf)
            print(f"  {basename}: {len(hits)} hit(s)")
            total_hits += len(hits)

    if not dry_run:
        save_last_run_time()

    prefix = "⚠️  DRY RUN |" if dry_run else "✅"
    print(f"\n{prefix} Processed {total_hits} total hits from {len(session_files)} files")
    conn.close()


if __name__ == "__main__":
    main()
