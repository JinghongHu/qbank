#!/bin/bash
# qbank patch: make rustiq reproducible.
# rustiq-core 0.0.11 draws randomness from rand::thread_rng() (OS-seeded, no seed API), so identical inputs give
# different circuits. We copy the pinned crate (crates.io rustiq-core 0.0.11, .crate sha256 51bfa802…07a6),
# route every thread_rng() call through crate::qbank_rng::thread_rng(), which is a ChaCha12 StdRng seeded from the
# environment variable QBANK_RUSTIQ_SEED=SEED[:NONCE] (re-seeded whenever the value changes; OS entropy if unset,
# i.e. upstream behaviour). No algorithmic change. rustiq's Cargo.toml gets a [patch.crates-io] entry.
set -euo pipefail
cd "$(dirname "$0")/../.."
SRC=$(ls -d external/rust/cargo/registry/src/*/rustiq-core-0.0.11)
DST=external/src/rustiq-core-0.0.11-qbank
rm -rf "$DST" && cp -R "$SRC" "$DST"
cat > "$DST/src/qbank_rng.rs" <<'RS'
//! qbank patch: seedable replacement for rand::thread_rng().
use rand::rngs::StdRng;
use rand::{Error, RngCore, SeedableRng};
use std::cell::RefCell;

thread_local! {
    static STATE: RefCell<(Option<String>, StdRng)> = RefCell::new((None, StdRng::from_entropy()));
}

fn with_rng<T>(f: impl FnOnce(&mut StdRng) -> T) -> T {
    let want = std::env::var("QBANK_RUSTIQ_SEED").ok();
    STATE.with(|cell| {
        let mut st = cell.borrow_mut();
        if st.0 != want {
            st.1 = match &want {
                // format "SEED" or "SEED:NONCE": only SEED seeds the RNG; a changed NONCE forces a fresh re-seed,
                // so every top-level call made with a new nonce starts from the same state for the same SEED.
                Some(s) => StdRng::seed_from_u64(s.split(':').next().unwrap().trim().parse::<u64>().expect("QBANK_RUSTIQ_SEED must be u64[:nonce]")),
                None => StdRng::from_entropy(),
            };
            st.0 = want;
        }
        f(&mut st.1)
    })
}

pub struct QbankRng;

pub fn thread_rng() -> QbankRng {
    QbankRng
}

impl RngCore for QbankRng {
    fn next_u32(&mut self) -> u32 { with_rng(|r| r.next_u32()) }
    fn next_u64(&mut self) -> u64 { with_rng(|r| r.next_u64()) }
    fn fill_bytes(&mut self, dest: &mut [u8]) { with_rng(|r| r.fill_bytes(dest)) }
    fn try_fill_bytes(&mut self, dest: &mut [u8]) -> Result<(), Error> { with_rng(|r| r.try_fill_bytes(dest)) }
}
RS
grep -q "pub mod qbank_rng;" "$DST/src/lib.rs" || printf '\npub mod qbank_rng;\n' >> "$DST/src/lib.rs"
grep -rl "thread_rng" "$DST/src" | grep -v qbank_rng.rs | while read -r f; do
  sed -i '' -e 's/use rand::thread_rng;/use crate::qbank_rng::thread_rng;/' -e 's/rand::thread_rng()/crate::qbank_rng::thread_rng()/g' "$f"
done
(cd "$(dirname "$SRC")" && diff -ruN rustiq-core-0.0.11 "$OLDPWD/$DST") > env/patches/rustiq-core-0.0.11-seed.patch || true
# point rustiq (pinned commit) at the patched crate
R=external/src/rustiq
cp "$R/Cargo.toml" "$R/Cargo.toml.orig-qbank" 2>/dev/null || true
grep -q "patch.crates-io" "$R/Cargo.toml" || printf '\n[patch.crates-io]\nrustiq-core = { path = "../rustiq-core-0.0.11-qbank" }\n' >> "$R/Cargo.toml"
diff -u "$R/Cargo.toml.orig-qbank" "$R/Cargo.toml" > env/patches/rustiq-Cargo.toml.patch || true
echo "patched; remaining thread_rng sites outside qbank_rng:"; grep -rn "rand::thread_rng\|use rand::thread_rng" "$DST/src" || echo "  none"
