#!/bin/bash
# install-cron.sh — Install memory management cron jobs for OpenClaw
#
# Usage: bash install-cron.sh [--remove]
#
# Installs four cron jobs:
#   Daily  03:00  memory-eviction.js   Score-based eviction from project files
#   Daily  03:10  hit-tracker.py       Extract memory_search hits from session logs
#   Weekly 04:00  log-compress.py      Compress old daily logs
#   Weekly 04:30  sync-skeleton.py     Sync MEMORY.md Active Projects

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
LOG_DIR="$WORKSPACE/memory/logs"
MARKER="# openclaw-memory-management"

mkdir -p "$LOG_DIR"

if [[ "${1:-}" == "--remove" ]]; then
    crontab -l 2>/dev/null | grep -v "$MARKER" | crontab -
    echo "✅ Removed memory management cron jobs"
    exit 0
fi

# Build cron entries
CRON_ENTRIES=$(cat <<EOF
0 3 * * * cd "$WORKSPACE" && node "$SCRIPT_DIR/memory-eviction.js" >> "$LOG_DIR/eviction.log" 2>&1 $MARKER
10 3 * * * cd "$WORKSPACE" && python3 "$SCRIPT_DIR/hit-tracker.py" >> "$LOG_DIR/hits.log" 2>&1 $MARKER
0 4 * * 0 cd "$WORKSPACE" && python3 "$SCRIPT_DIR/log-compress.py" >> "$LOG_DIR/compress.log" 2>&1 $MARKER
30 4 * * 0 cd "$WORKSPACE" && python3 "$SCRIPT_DIR/sync-skeleton.py" >> "$LOG_DIR/sync.log" 2>&1 $MARKER
EOF
)

# Remove existing entries, then add new ones
EXISTING=$(crontab -l 2>/dev/null | grep -v "$MARKER" || true)
echo "$EXISTING" | { cat; echo "$CRON_ENTRIES"; } | crontab -

echo "✅ Installed cron jobs:"
echo "   Daily  03:00  memory-eviction.js"
echo "   Daily  03:10  hit-tracker.py"
echo "   Weekly 04:00  log-compress.py (Sun)"
echo "   Weekly 04:30  sync-skeleton.py (Sun)"
echo ""
echo "   Logs → $LOG_DIR/"
echo ""
echo "   To remove: bash $SCRIPT_DIR/install-cron.sh --remove"
