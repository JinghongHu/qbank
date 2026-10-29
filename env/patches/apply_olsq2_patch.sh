#!/bin/bash
# Fetch OLSQ2 (BSD-3) at the pinned commit into external/src/OLSQ2 and apply the Qiskit-2 compatibility patch
# (removes the unused `Unroller` import that no longer exists in Qiskit 2.x; Qiskit-2 CircuitInstruction access).
set -euo pipefail
cd "$(dirname "$0")/../.."
C=0d7066f45b073bfd5f163a424b758026639f5acf
mkdir -p external/src && cd external/src
[ -d OLSQ2 ] && exit 0
curl -sSL --max-time 300 -o olsq2.tar.gz https://codeload.github.com/UCLA-VAST/OLSQ2/tar.gz/$C
echo "d8566fffcf1ad6571ef3751af92d9cc64d6dc1138c475dd3342493c0e89dba54  olsq2.tar.gz" | shasum -a 256 -c -
tar xzf olsq2.tar.gz && mv OLSQ2-$C OLSQ2 && echo $C > OLSQ2.COMMIT
patch -p0 < ../../env/patches/olsq2_qiskit2.patch
