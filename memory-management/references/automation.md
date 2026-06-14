# Automation Scripts Reference

The memory system includes cron scripts that run unattended. You don't invoke these directly — they run on schedule and you review their output during weekly maintenance.

## Installation

Run once to set up all cron jobs:

```bash
cd ~/.openclaw/workspace/skills/memory-management
bash scripts/install-cron.sh
```

This adds entries to your crontab. To verify:
```bash
crontab -l | grep memory
```

## Scripts

### memory-eviction.js
**Schedule:** Daily at 03:00
**What it does:** Score-based eviction from project files

Calculates a retention score for each P2 entry based on:
- Age (older = lower score)
- Hit count from hit-tracker.py (more hits = higher score)
- Priority (P1 entries are never evicted)

Entries scoring below threshold move to `memory/archive/YYYY-MM.md`.

**Output:** `memory/.eviction-log.json` with evicted entries

**Why automated?** Prevents project files from growing unbounded. Manual cleanup would be tedious and inconsistent.

### hit-tracker.py
**Schedule:** Daily at 03:10
**What it does:** Extract memory_search hits from session JSONL

Parses OpenClaw session logs to track which memory entries were actually retrieved via memory_search. Stores hit counts in `memory/.hit-tracker.db` (SQLite).

**Output:** SQLite database with schema:
```sql
CREATE TABLE hits (
  entry_hash TEXT PRIMARY KEY,
  entry_text TEXT,
  hit_count INTEGER,
  last_hit_date TEXT,
  file_path TEXT
);
```

**Why automated?** Hit tracking informs priority upgrades/downgrades. Doing this manually would require reading every session log.

### sync-skeleton.py
**Schedule:** Weekly Sunday at 04:30
**What it does:** Sync MEMORY.md Active Projects from project files

Reads each `memory/projects/*.md` file, extracts the most recent P1 status entry, and updates the corresponding one-liner in MEMORY.md's Active Projects section.

**Why automated?** Keeps MEMORY.md in sync with project files without manual copying. Ensures the skeleton stays current.

### log-compress.py
**Schedule:** Weekly Sunday at 04:00
**What it does:** Compress >7-day logs, extract key lines

For daily logs older than 7 days:
1. Extract lines tagged `[DECISION]`, `[FIX]`, `[PREF]`, `[STATUS]`
2. Append extracted lines to relevant project files (rewritten as proper entries)
3. Compress the original log: `memory/YYYY-MM-DD.md` → `memory/compressed/YYYY-MM-DD.md`

**Why automated?** Daily logs accumulate quickly. Manual compression would be forgotten, causing memory/ to bloat.

## Checking Script Output

During weekly maintenance (Step 3), review the automation outputs:

```bash
# Check eviction log
cat memory/.eviction-log.json

# Query hit tracker
python3 scripts/hit-tracker.py --report

# Check sync-skeleton changes
git diff memory/MEMORY.md
```

## Troubleshooting

**Scripts not running?**
```bash
# Check cron service status (macOS)
sudo launchctl list | grep cron

# Check cron logs
grep CRON /var/log/system.log
```

**Hit tracker database missing?**
The database is created on first run. If `memory/.hit-tracker.db` doesn't exist after 24 hours, check that OpenClaw is writing session logs to the expected location.

**Eviction too aggressive?**
Edit `scripts/memory-eviction.js` and adjust the `RETENTION_THRESHOLD` constant (default: 0.3).
