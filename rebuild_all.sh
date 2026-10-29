#!/bin/bash
# One command to rebuild qbank v1 from scratch: environment, external data, all categories, all tables and reports.
# Baseline runs take many CPU hours (see the reports for the measured budgets); the per-job cache under
# data/v1/cache/ is reused when present, so re-running after an interruption continues where it stopped.
set -euo pipefail
cd "$(dirname "$0")"
bash env/bootstrap_env.sh                 # venv from requirements.lock.txt (hashes), isolated Rust, rustiq (+seed patch), ABC
bash env/patches/apply_olsq2_patch.sh     # OLSQ2 @ 0d7066f4 + Qiskit-2 patch
bash data/v1/external/fetch_A.sh
bash data/v1/external/fetch_B.sh
bash data/v1/external/fetch_C.sh
.venv/bin/qbank rebuild all --workers "${QBANK_WORKERS:-10}"
.venv/bin/python -m pytest tests -q
