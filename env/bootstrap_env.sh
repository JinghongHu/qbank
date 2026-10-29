#!/bin/bash
# Rebuild the qbank environment from scratch (Phase 0).
#   bash env/bootstrap_env.sh            # venv + external tools
#   bash env/bootstrap_env.sh --venv-only
#
# Everything is created inside qbank/ ; nothing outside qbank/ is modified:
#   qbank/.venv                       Python 3.11 venv, installed from the official PyPI with --require-hashes
#   qbank/.venv/pip.conf              pins the index to https://pypi.org/simple (overrides any user/global mirror)
#   qbank/external/rust/{rustup,cargo} isolated Rust toolchain (no PATH / shell-profile changes)
#   qbank/external/src/rustiq         qiskit-community/rustiq @ RUSTIQ_COMMIT (not on PyPI)
#   qbank/external/src/abc            berkeley-abc/abc @ ABC_COMMIT
set -euo pipefail
cd "$(dirname "$0")/.."
QB=$PWD
PY=${QBANK_PYTHON:-/usr/local/bin/python3.11}   # python.org CPython 3.11.4 on the Phase-0 machine
RUSTIQ_URL=https://github.com/qiskit-community/rustiq
RUSTIQ_COMMIT=425000222e21a7a28d70a08c75be968f16fd6903
ABC_URL=https://github.com/berkeley-abc/abc
ABC_COMMIT=ab2139ee0c418f54136deb4e8e89eeea3b87efc8
RUSTUP_INIT_SHA256=7d0ea0f8eba7fa1ebfe998091cd7ec4501e33ec5ca6b884eb4d894d7da5170af  # sh.rustup.rs as fetched 2026-09-25
export GIT_CONFIG_GLOBAL=/dev/null   # ignore user-level git url rewrites; fetch over https from the official hosts
export PIP_CACHE_DIR=$QB/.cache/pip  # keep pip's download cache inside qbank/

echo "== venv"
rm -rf .venv
"$PY" -m venv .venv
printf '[global]\nindex-url = https://pypi.org/simple\n' > .venv/pip.conf
.venv/bin/python -m pip install --quiet --upgrade "pip==26.2.1"
.venv/bin/python -m pip install --require-hashes --no-deps -r requirements.lock.txt
[ "${1:-}" = "--venv-only" ] && exit 0

echo "== isolated Rust toolchain (for rustiq)"
export RUSTUP_HOME=$QB/external/rust/rustup CARGO_HOME=$QB/external/rust/cargo
mkdir -p external/rust external/src
if [ ! -x "$CARGO_HOME/bin/cargo" ]; then
  curl --proto '=https' --tlsv1.2 -sSf --max-time 120 https://sh.rustup.rs -o external/rust/rustup-init.sh
  echo "$RUSTUP_INIT_SHA256  external/rust/rustup-init.sh" | shasum -a 256 -c - || echo "WARNING: rustup-init.sh changed upstream (record the new hash)"
  sh external/rust/rustup-init.sh -y --no-modify-path --profile minimal --default-toolchain stable
fi

echo "== rustiq @ $RUSTIQ_COMMIT"
rm -rf external/src/rustiq
git clone -q "$RUSTIQ_URL" external/src/rustiq
git -C external/src/rustiq checkout -q "$RUSTIQ_COMMIT"
git -C external/src/rustiq rev-parse HEAD > external/src/rustiq.COMMIT && rm -rf external/src/rustiq/.git  # no nested repo (IDE auto-registers it)
(cd external/src/rustiq && PATH=$CARGO_HOME/bin:$PATH cargo fetch -q)   # puts rustiq-core 0.0.11 into the isolated cargo registry
bash env/patches/apply_rustiq_seed_patch.sh                            # seedable RNG (QBANK_RUSTIQ_SEED), see env/patches/
PATH=$CARGO_HOME/bin:$PATH .venv/bin/python -m pip install --no-deps ./external/src/rustiq

echo "== ABC @ $ABC_COMMIT"
rm -rf external/src/abc
git clone -q "$ABC_URL" external/src/abc
git -C external/src/abc checkout -q "$ABC_COMMIT"
git -C external/src/abc rev-parse HEAD > external/src/abc.COMMIT && rm -rf external/src/abc/.git
(cd external/src/abc && make -j8 ABC_USE_NO_READLINE=1 abc > /dev/null)
external/src/abc/abc -q "version"

echo "== done"
.venv/bin/python -c "import qiskit, stim, rustiq, mqt.qecc, pytket; print('qiskit', qiskit.__version__, '| stim', stim.__version__)"
