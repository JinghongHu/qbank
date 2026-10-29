"""Phase 0: how large can QMAP's SAT-optimal Clifford synthesis (two_qubit_gates) go? Random stabilizer states, n=2..6."""
import json, multiprocessing as mp, sys, time
import stim

def work(stabs, q):
    from mqt.qmap.clifford_synthesis import TargetMetric
    from mqt.qmap.plugins.qiskit.clifford_synthesis import synthesize_clifford
    t = time.perf_counter()
    qc, r = synthesize_clifford(str(stabs), target_metric=TargetMetric.two_qubit_gates, heuristic=False)
    q.put({"two_qubit_gates": r.two_qubit_gates, "time_s": time.perf_counter() - t})

if __name__ == "__main__":
    timeout = float(sys.argv[1])
    out = []
    for n in range(2, 7):
        for seed in range(2):
            t = stim.Tableau.random(n) if False else None
            import numpy as np
            np.random.seed(1000 * n + seed)
            tab = stim.Tableau.random(n)  # stim's RNG is not seedable here; stabilizers are recorded below
            stabs = [str(tab.z_output(i)) for i in range(n)]
            q = mp.Queue(); p = mp.Process(target=work, args=(stabs, q)); t0 = time.perf_counter(); p.start(); p.join(timeout)
            if p.is_alive():
                p.kill(); p.join(); r = {"status": "timeout", "time_s": time.perf_counter() - t0}
            elif p.exitcode != 0:
                r = {"status": "crash", "exitcode": p.exitcode}
            else:
                r = {"status": "ok", **q.get()}
            r.update(n=n, stabilizers=stabs); out.append(r)
            print(json.dumps({k: v for k, v in r.items() if k != "stabilizers"}), flush=True)
    json.dump(out, open("phase0/logs/qmap_sat_scaling.json", "w"), indent=1)
