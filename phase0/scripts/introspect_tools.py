"""Phase 0: list versions and the relevant entry points of every installed baseline tool."""
import importlib, importlib.metadata as md, json, sys

def ver(dist):
    try:
        return md.version(dist)
    except md.PackageNotFoundError:
        return None

out = {"python": sys.version.split()[0], "versions": {}, "entry_points": {}}
for d in ["qiskit", "qiskit-aer", "qiskit-qasm3-import", "stim", "mqt.qmap", "mqt.qcec", "mqt.qecc",
          "mqt.bench", "mqt.core", "pytket", "pytket-qiskit", "bqskit", "bqskitrs", "qclib", "python-sat",
          "dd", "z3-solver", "py-aiger", "pyzx", "numpy", "scipy", "networkx", "rustiq"]:
    out["versions"][d] = ver(d)

def names(modname, pred=lambda n: True):
    try:
        m = importlib.import_module(modname)
    except Exception as e:  # record, don't hide
        return f"IMPORT ERROR: {type(e).__name__}: {e}"
    return sorted(n for n in dir(m) if not n.startswith("_") and pred(n))

ep = out["entry_points"]
ep["qiskit.synthesis"] = names("qiskit.synthesis", lambda n: n.startswith("synth_"))
ep["qiskit.circuit.library(oracle/mcx)"] = names("qiskit.circuit.library",
    lambda n: any(k in n.lower() for k in ("oracle", "mcx", "mcmt", "rccx", "rc3x", "c3x", "c4x", "dicke", "statepreparation", "qft")))
ep["qiskit.transpiler.passes(routing)"] = names("qiskit.transpiler.passes",
    lambda n: any(k in n.lower() for k in ("sabre", "swap", "route", "routing", "layout", "commut")))
ep["qiskit...commuting_2q_gate_routing"] = names("qiskit.transpiler.passes.routing.commuting_2q_gate_routing")
ep["stim.Tableau.to_circuit doc"] = __import__("stim").Tableau.to_circuit.__doc__.split("\n")[0:25]
ep["mqt.qmap"] = names("mqt.qmap")
for sub in ["mqt.qmap.clifford_synthesis", "mqt.qmap.plugins", "mqt.qmap.plugins.qiskit", "mqt.qmap.pyqmap"]:
    ep[sub] = names(sub)
ep["mqt.qecc"] = names("mqt.qecc")
for sub in ["mqt.qecc.circuit_synthesis", "mqt.qecc.codes"]:
    ep[sub] = names(sub)
ep["mqt.qcec"] = names("mqt.qcec")
ep["mqt.bench"] = names("mqt.bench")
ep["pytket.passes(route/clifford/synth)"] = names("pytket.passes",
    lambda n: any(k in n.lower() for k in ("rout", "clifford", "synth", "placement", "pauli")))
ep["pytket.tableau"] = names("pytket.tableau")
ep["pytket.mapping"] = names("pytket.mapping")
ep["qclib.state_preparation"] = names("qclib.state_preparation")
ep["pysat.solvers"] = names("pysat.solvers", lambda n: n[0].isupper())
print(json.dumps(out, indent=1, ensure_ascii=False))
