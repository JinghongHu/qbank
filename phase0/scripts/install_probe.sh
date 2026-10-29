#!/bin/bash
# Phase 0: try installing each candidate package into qbank/.venv individually; log success/failure.
# Usage: bash phase0/scripts/install_probe.sh pkg1 pkg2 ...
cd "$(dirname "$0")/../.."
LOG=phase0/logs/install_probe.log
for p in "$@"; do
  echo "=== $p  ($(date -u +%FT%TZ))" >> "$LOG"
  if perl -e 'alarm shift; exec @ARGV' 900 .venv/bin/pip install --no-input "$p" >> "$LOG" 2>&1; then
    echo "OK   $p" | tee -a "$LOG"
  else
    echo "FAIL $p" | tee -a "$LOG"
  fi
done
