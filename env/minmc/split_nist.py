"""Split NIST's n6_circ.txt (records separated by blank lines) into k files, record i going to file i mod k."""
import sys
src, k, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
recs = [r.strip() for r in open(src).read().split("\n\n") if r.strip()]
for j in range(k):
    open(f"{out}/in{j:02d}.txt", "w").write("\n\n".join(recs[j::k]) + "\n\n")
print(len(recs), "records")
