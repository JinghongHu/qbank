#!/bin/bash
# qbank v1.2: MC-oriented XAG cut rewriting for category B.
# Builds, in isolation from any system installation:
#   external/src/mockturtle           lsils/mockturtle @ MOCKTURTLE_COMMIT (MIT), header-only, sha256-checked tarball
#   external/src/qbank_minmc/minmc     driver (env/minmc/minmc.cpp): AIGER -> cut rewriting with the minimum-MC
#                                      databases (mockturtle's embedded <= 5-input XAGs + the 6-input database) -> XAG
#   external/src/qbank_minmc/build_db6 converter (env/minmc/build_db6.cpp)
#   .cache/external/minmc/db6.txt      6-input database: NIST usnistgov/Circuits @ NIST_COMMIT data/circuits/n6_circ.txt
#                                      (AND-optimal circuits of the affine classes of 6-variable functions, Calik,
#                                      Turan, Peralta), converted to mockturtle's format and keyed by kitty's hybrid
#                                      exact spectral canonical form; every entry is re-simulated and checked. Classes
#                                      whose canonization needs more than 10^8 steps are left out (6 of 150,356 classes).
#                                      Built by this script (checksum below).
# Requires: curl, a C++17 compiler (tested: Apple clang 16), python3. Time: ~10 min on 12 cores.
set -euo pipefail
cd "$(dirname "$0")/.."
MOCKTURTLE_URL=https://github.com/lsils/mockturtle/archive
MOCKTURTLE_COMMIT=d9e02495f537bac460f7994557184054a3eebd75
MOCKTURTLE_SHA256=ec65d098cd7562e7c93c8e050a123ff805b39eb59b2cea3f8230c2675dcc92c0
NIST_URL=https://github.com/usnistgov/Circuits/archive
NIST_COMMIT=b7678d6736736b14a04a8349f060fed49c7ec874
NIST_SHA256=533228029ca3f141bba50eae7461e44b031ac33c5a7e4b80050c63c7824e0287
DB6_SHA256=2e3795a1b902c78017fdd626f54a42209921c416725a3cc3a90d36d694d18567
STEP_LIMIT=100000000
JOBS=${JOBS:-12}

echo "== mockturtle @ $MOCKTURTLE_COMMIT"
[ -f external/src/mockturtle.tar.gz ] || curl -sSL --max-time 600 -o external/src/mockturtle.tar.gz "$MOCKTURTLE_URL/$MOCKTURTLE_COMMIT.tar.gz"
echo "$MOCKTURTLE_SHA256  external/src/mockturtle.tar.gz" | shasum -a 256 -c -
if [ ! -d external/src/mockturtle ]; then
  tar -xzf external/src/mockturtle.tar.gz -C external/src
  mv "external/src/mockturtle-$MOCKTURTLE_COMMIT" external/src/mockturtle
fi
echo "$MOCKTURTLE_COMMIT" > external/src/mockturtle.COMMIT

echo "== compile driver and converter"
M=external/src/mockturtle
O=external/src/qbank_minmc
mkdir -p $O
INC="-I $M/include -I $M/lib/kitty -I $M/lib/lorina -I $M/lib/fmt -I $M/lib/parallel_hashmap -I $M/lib/rang -I $M/lib/bill -I $M/lib/abcsat -I $M/lib/percy -I $M/lib/nauty -I env/minmc"
c++ -std=c++17 -O2 -DFMT_HEADER_ONLY -w $INC -o $O/minmc env/minmc/minmc.cpp
c++ -std=c++17 -O2 -DFMT_HEADER_ONLY -w $INC -o $O/build_db6 env/minmc/build_db6.cpp

echo "== NIST circuits @ $NIST_COMMIT"
N=.cache/external/nist_circuits
mkdir -p $N
[ -f $N/circuits.tar.gz ] || curl -sSL --max-time 600 -o $N/circuits.tar.gz "$NIST_URL/$NIST_COMMIT.tar.gz"
echo "$NIST_SHA256  $N/circuits.tar.gz" | shasum -a 256 -c -
[ -d "$N/Circuits-$NIST_COMMIT" ] || tar -xzf $N/circuits.tar.gz -C $N

D=.cache/external/minmc
if [ -f $D/db6.txt ] && echo "$DB6_SHA256  $D/db6.txt" | shasum -a 256 -c - >/dev/null 2>&1; then
  echo "== 6-input database present and verified"; exit 0
fi
echo "== build 6-input database ($JOBS jobs, canonization step limit $STEP_LIMIT)"
W=$D/work
rm -rf $W && mkdir -p $W
python3 env/minmc/split_nist.py "$N/Circuits-$NIST_COMMIT/data/circuits/n6_circ.txt" "$JOBS" $W
for f in $W/in*.txt; do
  j=$(basename $f .txt); j=${j#in}
  $O/build_db6 $f $W/out$j.txt $STEP_LIMIT $W/limited$j.txt 2> $W/log$j.txt &
done
wait
cat $W/log*.txt | grep total
python3 env/minmc/merge_db.py $W $D/db6.txt
echo "$DB6_SHA256  $D/db6.txt" | shasum -a 256 -c -
