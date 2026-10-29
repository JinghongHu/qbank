"""Merge build_db6 outputs into one database sorted by the canonical representative (deterministic file)."""
import glob, sys
db = {}
for f in sorted(glob.glob(sys.argv[1] + "/out*.txt")):
    for l in open(f).read().split("\n"):
        if l:
            k = l.split(" ")[0]
            if k in db and db[k] != l:
                raise SystemExit(f"conflicting entries for {k}")
            db[k] = l
open(sys.argv[2], "w").write("".join(db[k] + "\n" for k in sorted(db)))
print(len(db), "classes")
