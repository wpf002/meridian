#!/bin/bash
#
# Pull a consistent snapshot of the Railway-hosted Meridian DB down to this Mac.
# Uses SQLite's online .backup (safe while the app is running), verifies
# integrity, and keeps the most recent $KEEP backups.
#
# Scheduled daily by ~/Library/LaunchAgents/com.meridian.backup.plist.
# Requires the `meridian-railway` SSH alias (railway ssh config --alias …).
#
set -uo pipefail

ALIAS="meridian-railway"
REMOTE_DB="/app/data/meridian.db"
BACKUP_DIR="$HOME/meridian-backups"
KEEP=14
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20"

mkdir -p "$BACKUP_DIR"
TS=$(date +%Y%m%d-%H%M%S)
OUT="$BACKUP_DIR/meridian-$TS.db"

echo "[$(date)] starting backup -> $OUT"

# 1) consistent online backup on the container
$SSH "$ALIAS" python3 - <<PY || { echo "remote backup failed"; exit 1; }
import sqlite3
src = sqlite3.connect("$REMOTE_DB")
dst = sqlite3.connect("/tmp/_meridian_bk.db")
src.backup(dst)
dst.close(); src.close()
PY

# 2) stream it down, then clean up the container temp
$SSH "$ALIAS" "cat /tmp/_meridian_bk.db" > "$OUT" || { echo "download failed"; rm -f "$OUT"; exit 1; }
$SSH "$ALIAS" "rm -f /tmp/_meridian_bk.db" >/dev/null 2>&1

# 3) verify what we pulled is a valid SQLite DB
if ! python3 -c "import sqlite3,sys; print(sqlite3.connect(sys.argv[1]).execute('PRAGMA integrity_check').fetchone()[0])" "$OUT" 2>/dev/null | grep -q '^ok$'; then
    echo "integrity check FAILED — discarding $OUT"
    rm -f "$OUT"
    exit 1
fi

SIZE=$(du -h "$OUT" | cut -f1)
echo "[$(date)] backup OK: $OUT ($SIZE)"

# 4) prune to the most recent $KEEP
ls -1t "$BACKUP_DIR"/meridian-*.db 2>/dev/null | tail -n +$((KEEP+1)) | xargs -r rm -f
echo "kept $(ls -1 "$BACKUP_DIR"/meridian-*.db 2>/dev/null | wc -l | tr -d ' ') backup(s) in $BACKUP_DIR"
