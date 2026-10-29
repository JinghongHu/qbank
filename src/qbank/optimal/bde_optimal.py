"""Known optima and lower bounds for categories B and D (data/v1/optimal/<C>.jsonl). Every record states its kind:
  optimal       value proven optimal (proof or reference given)
  lower_bound   proven lower bound (the gap of a baseline to it is an upper bound on the true gap)
  upper_bound   published construction bound (not a proof of optimality)
B  probe: Toffoli (AND) count >= multiplicative complexity >= deg_ANF(f) - 1 on the Toffoli tracks, for BIT-FLIP
   oracles only (10-23: false for phase oracles: (-1)^(ab) is one free CZ; phase records are "unproven_bound").
D  n = 2 probe: optimum 1 CX for an entangled state (>= 1: a product-free state needs a two-qubit gate; <= 1: Schmidt
   decomposition a|00> + b|11> = CX (RY (x) I)|00> up to local unitaries).
   n = 3 probe: lower bound 2 when no qubit is in a product with the others (one two-qubit gate leaves a qubit
   untouched), upper bound 3 (Znidaric, Giraud & Georgeot, PRA 77, 032320 (2008): at most three CNOTs for any state).
   cx >= n - 1 when the state is entangled across EVERY bipartition (the two-qubit-gate interaction graph must be
   connected, otherwise the state factorises across its components). 10-23 correction: all single-qubit marginals
   mixed is NOT enough for n >= 4 (two Bell pairs: every marginal mixed, 2 CX). Proven here by a sufficient test: the
   graph joining qubits whose two-qubit marginal is not the product of their one-qubit marginals is connected (every
   bipartition is then crossed by such a pair, and a state that is a product across S|T has product marginals for
   every pair split by S|T). Otherwise the n - 1 record is kept as "unproven_bound" (proven = False).
   10-24 merge (C5, DECISIONS_FINAL 2.7, Codex RECONCILE 50): "proven" now means proven FOR THE CONTRACT, which accepts
   every circuit whose state has fidelity >= 1 - EXACT_TOL with the target (contracts/state.py), not just the exact
   target. A bound is proven only by tests that hold for every state within that tolerance (robust certificates):
     * pair (i, j) is a robust edge if ||rho_ij - rho_i (x) rho_j||_1 > 6 sqrt(tol) + margin on the target: a state
       psi with F >= 1 - tol has ||psi - target||_1 <= 2 sqrt(tol) and partial traces contract, so a psi that is a
       product across a cut separating i and j would make the target's difference <= 6 sqrt(tol);
     * qubit q is robustly mixed if lambda_min(rho_q) > sqrt(tol) + margin (a pure marginal of psi would be within
       trace distance 2 sqrt(tol), and ||rho - pure||_1 >= 2 lambda_min(rho));
     * lower bound = max(n - 1 if the robust-edge graph is connected, ceil(#robustly mixed qubits / 2)) (every
       mixed qubit must be touched by a two-qubit gate; each gate touches two). Both bounds are proofs.
   Results of the exact-target tests (1e-9 thresholds) that the robust tests do not confirm are numerical references
   ("unproven_bound", proven = False), never used for "distance to optimum" claims. Every record carries the
   contract tolerance and the certificate thresholds.
"""
from __future__ import annotations

import json

import numpy as np

from ..core.instance import data_root, load_index, load_private, load_public


def _marginals_mixed(pub) -> bool:
    n = pub["n"]
    amp = {int(k): complex(re, im) for k, re, im in pub["amplitudes"]}
    for q in range(n):
        rho = np.zeros((2, 2), dtype=complex)
        rest: dict = {}
        for x, a in amp.items():
            rest.setdefault(x & ~(1 << q), [0j, 0j])[(x >> q) & 1] += a
        for v0, v1 in rest.values():
            v = np.array([v0, v1])
            rho += np.outer(v, v.conj())
        if abs(np.linalg.eigvalsh(rho)).min() < 1e-9:
            return False
    return True


def _correlation_graph_connected(pub) -> bool:
    """True if the graph on the qubits with an edge {i, j} whenever rho_ij != rho_i (x) rho_j is connected (n >= 2).
    Sufficient for the pure state to be entangled across every bipartition (see the module docstring)."""
    n = pub["n"]
    amp = {int(k): complex(re, im) for k, re, im in pub["amplitudes"]}
    nrm = sum(abs(a) ** 2 for a in amp.values())

    def marg(qs):
        k = len(qs)
        rest: dict = {}
        mask = sum(1 << q for q in qs)
        for x, a in amp.items():
            idx = sum(((x >> q) & 1) << j for j, q in enumerate(qs))
            rest.setdefault(x & ~mask, np.zeros(1 << k, dtype=complex))[idx] += a
        rho = np.zeros((1 << k, 1 << k), dtype=complex)
        for v in rest.values():
            rho += np.outer(v, v.conj())
        return rho / nrm
    one = [marg([q]) for q in range(n)]
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for i in range(n):
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            # marg([i, j]) index bit 0 = qubit i, bit 1 = qubit j  ->  kron(rho_j, rho_i)
            if np.abs(marg([i, j]) - np.kron(one[j], one[i])).max() > 1e-9:
                parent[find(i)] = find(j)
    return len({find(q) for q in range(n)}) == 1


ROBUST_MARGIN = 1e-7     # numerical margin of the robust certificates (target amplitudes are floats, errors ~1e-12)


def _marginal(amp, qs, nrm):
    k = len(qs)
    rest: dict = {}
    mask = sum(1 << q for q in qs)
    for x, a in amp.items():
        idx = sum(((x >> q) & 1) << j for j, q in enumerate(qs))
        rest.setdefault(x & ~mask, np.zeros(1 << k, dtype=complex))[idx] += a
    rho = np.zeros((1 << k, 1 << k), dtype=complex)
    for v in rest.values():
        rho += np.outer(v, v.conj())
    return rho / nrm


def _u3(t, p, l) -> np.ndarray:
    return np.array([[np.cos(t / 2), -np.exp(1j * l) * np.sin(t / 2)],
                     [np.exp(1j * p) * np.sin(t / 2), np.exp(1j * (p + l)) * np.cos(t / 2)]])


def max_fidelity_with_cx(tgt: np.ndarray, n: int, skeleton: list, restarts: int, rng) -> float:
    """Numerical evidence only (10-29: re-implemented, the helper was missing from the source): the largest fidelity
    |<tgt|C|0...0>|^2 found over circuits C = L_k CX(skeleton[k-1]) ... CX(skeleton[0]) L_0, where every L is a layer
    of arbitrary one-qubit unitaries (U3) and CX(a, b) has control a, target b; `restarts` random starts of BFGS.
    Little-endian qubit order (qubit q = bit q of the basis index), like the instance amplitudes."""
    from scipy.optimize import minimize
    dim = 1 << n
    tgt = np.asarray(tgt, dtype=complex) / np.linalg.norm(tgt)
    nl = len(skeleton) + 1

    def layer(th):
        M = np.array([[1.0 + 0j]])
        for q in reversed(range(n)):                    # kron order: qubit n-1 ... qubit 0 (little-endian index)
            M = np.kron(M, _u3(*th[3 * q: 3 * q + 3]))
        return M

    def cx(a, b):
        P = np.zeros((dim, dim))
        for x in range(dim):
            y = x ^ (1 << b) if (x >> a) & 1 else x
            P[y, x] = 1.0
        return P

    cxs = [cx(a, b) for a, b in skeleton]

    def state(th):
        th = th.reshape(nl, 3 * n)
        v = np.zeros(dim, dtype=complex)
        v[0] = 1.0
        v = layer(th[0]) @ v
        for k, C in enumerate(cxs):
            v = layer(th[k + 1]) @ (C @ v)
        return v

    best = 0.0
    for _ in range(restarts):
        x0 = rng.uniform(0, 2 * np.pi, nl * 3 * n)
        r = minimize(lambda th: -abs(np.vdot(tgt, state(th))) ** 2, x0, method="BFGS", options={"maxiter": 2000})
        best = max(best, -float(r.fun))
    return best


def robust_certificate(pub, tol: float) -> dict:
    """Lower bound on the two-qubit gates of EVERY state within fidelity 1 - tol of the target (see the module doc):
    -> {"lb", "connected", "mixed": [robustly mixed qubits], "edge_thr", "mixed_thr", "tol", "proof"}."""
    n = pub["n"]
    amp = {int(k): complex(re, im) for k, re, im in pub["amplitudes"]}
    nrm = sum(abs(a) ** 2 for a in amp.values())
    st = float(np.sqrt(tol))
    edge_thr, mixed_thr = 6 * st + ROBUST_MARGIN, st + ROBUST_MARGIN
    one = [_marginal(amp, [q], nrm) for q in range(n)]
    mixed = [q for q in range(n) if float(np.linalg.eigvalsh(one[q]).min()) > mixed_thr]
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for i in range(n):
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            d = _marginal(amp, [i, j], nrm) - np.kron(one[j], one[i])
            if float(np.abs(np.linalg.eigvalsh(d)).sum()) > edge_thr:     # trace norm of a Hermitian difference
                parent[find(i)] = find(j)
    connected = n >= 2 and len({find(q) for q in range(n)}) == 1
    lb_conn, lb_mix = (n - 1 if connected else 0), (len(mixed) + 1) // 2
    lb = max(lb_conn, lb_mix)
    proof = (f"robust for the contract tolerance {tol:g} (every state with fidelity >= 1 - {tol:g}): "
             + (f"pairs with ||rho_ij - rho_i (x) rho_j||_1 > {edge_thr:.3g} connect all qubits, so the two-qubit-gate graph "
                f"must be connected (n - 1 = {n - 1})" if lb == lb_conn and lb > 0 else
                f"{len(mixed)} qubits have lambda_min(rho_q) > {mixed_thr:.3g}, each must be touched by a two-qubit gate "
                f"(ceil({len(mixed)}/2) = {lb_mix})"))
    return {"lb": lb, "connected": connected, "mixed": mixed, "edge_thr": edge_thr, "mixed_thr": mixed_thr, "tol": tol,
            "proof": proof}


def _b_probe_bounds(args):
    """One probe function: MC lower bound (exact search from deg - 1, one time limit) and an upper-bound XAG
    (SAT at k = 6, 5, ... downwards until a k is UNSAT or times out)."""
    import base64
    import time
    from ..core.aig import AIG
    from ..core.satutil import solve_with_timeout
    from ..core.xag import _decode, _encode, anf_degree, exact_mc
    row, pub, per_k = args
    aig = AIG.from_aiger(base64.b64decode(pub["aiger_b64"]))
    n = aig.num_inputs
    tt = aig.truth_tables()[0]
    deg = anf_degree(tt, n)
    t0 = time.time()
    x, k, proven = exact_mc(tt, n, time.monotonic() + per_k)
    lb, ub_x = k, x
    mc_exact = x is not None and proven
    if not mc_exact:
        for kk in range(6, k - 1, -1):                       # every 6-input function has an XAG with <= 6 ANDs
            cls, A, Bv, O, terms = _encode(tt, n, kk)
            st, model = solve_with_timeout(cls, per_k, want_model=True)
            if st != "sat":
                break
            ub_x = _decode(model, n, kk, A, Bv, O, terms)
            if kk == lb:
                mc_exact = True
    return row, pub, n, deg, lb, mc_exact, ub_x, time.time() - t0


def run_B(log=print, per_k: float = 600.0) -> list[dict]:
    """Probe functions (single output, n <= 6): multiplicative complexity by SAT (core/xag.py).
    Lower bound: Toffoli count >= MC(f) (a circuit with t Toffoli-like gates is an XAG with t ANDs); if the exact
    search times out at k, MC >= k is still proven (every smaller k UNSAT, and k >= deg - 1).
    Upper bound (tof@inf): Toffoli count of the verified circuit compiled from the smallest XAG found (<= 2 ANDs - 1)."""
    import multiprocessing as mp
    from ..baselines.tools_b import xag_oracle
    from ..categories.B.instances import verify
    from ..core.costs import costs
    jobs = [(row, load_public("B", row["hash"]), per_k) for row in load_index("B") if row["family"] == "probe_small"]
    out = []
    with mp.get_context("spawn").Pool(min(8, len(jobs))) as pool:
        for row, pub, n, deg, lb, mc_exact, ub_x, dt in pool.imap_unordered(_b_probe_bounds, jobs):
            proof_lb = (f"MC(f) = {lb} by SAT (every smaller AND count UNSAT or below deg(f) - 1 = {deg - 1})" if mc_exact else
                        f"MC(f) >= {lb}: every AND count below {lb} is UNSAT or below deg(f) - 1 = {deg - 1}")
            bitflip = pub["task"] == "oracle_bitflip_clean"
            for tr in pub["tracks"]:
                if tr.startswith("tof@"):     # 10-23: the MC bound holds for bit-flip oracles only (phase: ab = one CZ)
                    out.append({"instance_id": row["id"], "hash": row["hash"], "track": tr,
                                "kind": "lower_bound" if bitflip else "unproven_bound", "value": lb, "proven": bitflip,
                                "mc_exact": mc_exact, "proof": ("Toffoli count >= multiplicative complexity (bit-flip oracle: the "
                                                                "permutation part is an XAG with one AND per Toffoli); " if bitflip else
                                                                "NOT a bound for a phase oracle (quadratic phases are free CZ); ")
                                + proof_lb})
            if ub_x is not None:
                c = xag_oracle(ub_x, "bitflip" if pub["task"] == "oracle_bitflip_clean" else "phase", pub["n_outputs"])
                v = verify(pub, "tof@inf", c)
                if v.status == "pass":
                    out.append({"instance_id": row["id"], "hash": row["hash"], "track": "tof@inf", "kind": "upper_bound",
                                "value": costs(c)["toffoli_count"], "proven": True, "verified": True, "ands": ub_x.num_ands,
                                "proof": f"verified circuit compiled from an XAG with {ub_x.num_ands} ANDs (<= 2 x ANDs - 1 Toffoli)",
                                "circuit": c.to_json()})
            log(f"[optimal B] {row['id']} n={n} deg={deg} MC{'=' if mc_exact else '>='}{lb} "
                f"ub_ands={ub_x.num_ands if ub_x is not None else None} ({dt:.0f}s)")
    return out


def run_D(log=print) -> list[dict]:
    """D lower bounds (10-24 merge, C5): proven records only from robust_certificate (valid for every state the
    contract accepts); the exact-target tests give numerical references. Upper bounds are constructions."""
    from ..contracts.state import EXACT_TOL
    out = []
    for row in load_index("D"):
        pub = load_public("D", row["hash"])
        n = pub["n"]
        cert = robust_certificate(pub, EXACT_TOL)
        base = {"instance_id": row["id"], "hash": row["hash"], "track": "cx", "tolerance": EXACT_TOL,
                "certificate": {k: cert[k] for k in ("edge_thr", "mixed_thr", "connected", "mixed")}}
        lb = cert["lb"]
        mixed = _marginals_mixed(pub)
        if row["family"] == "dense" and n == 2 and lb >= 1:
            out.append({**base, "kind": "optimal", "value": 1, "proven": True,
                        "proof": cert["proof"] + "; <= 1: Schmidt decomposition gives 1 CX"})
            continue
        if row["family"] == "dense" and n == 3 and mixed:
            if lb >= 2:
                out.append({**base, "kind": "lower_bound", "value": lb, "proven": True, "proof": cert["proof"]})
            else:
                out.append({**base, "kind": "unproven_bound", "value": 2, "proven": False,
                            "proof": "no qubit factorises for the exact target, but not robustly within the contract "
                                     "tolerance: numerical reference, NOT a proven lower bound"})
            out.append({**base, "kind": "upper_bound", "value": 3, "proven": True,
                        "proof": "Znidaric, Giraud & Georgeot, PRA 77, 032320 (2008): any 3-qubit state with at most 3 CNOTs"})
            import itertools
            tgt = np.zeros(8, dtype=complex)
            for k, re_, im_ in pub["amplitudes"]:
                tgt[int(k)] = complex(re_, im_)
            tgt /= np.linalg.norm(tgt)
            rng = np.random.default_rng(int(row["hash"][7:15], 16))
            # up to local unitaries a CX's direction is irrelevant (CX(b,a) = (H x H) CX(a,b) (H x H)) and two CX on the
            # same pair act on two qubits only (the third would stay a product): 6 ordered pairs of distinct pairs remain
            pairs = [(0, 1), (0, 2), (1, 2)]
            skeletons = [(p1, p2) for p1 in pairs for p2 in pairs if p1 != p2]
            best2 = max(max_fidelity_with_cx(tgt, 3, list(sk), 6, rng) for sk in skeletons)
            if best2 < 1 - 1e-6:
                out.append({**base, "kind": "numerical_optimum", "value": 3,
                            "proven": False, "proof": f"no 2-CX circuit found above fidelity {best2:.6f} (6 skeletons up to local "
                                                      "equivalence, 6 BFGS restarts each); 3 CX reachable; numerical evidence, not a proof"})
            continue
        if lb > 0:
            out.append({**base, "kind": "lower_bound", "value": lb, "proven": True, "proof": cert["proof"]})
        if mixed and _correlation_graph_connected(pub) and lb < n - 1:   # exact-target test only: a reference
            out.append({**base, "kind": "unproven_bound", "value": n - 1, "proven": False,
                        "proof": "the exact target is entangled across every bipartition (1e-9 tests), but not robustly within "
                                 "the contract tolerance: numerical reference, NOT a proven lower bound"})
        elif mixed and lb < n - 1:   # 10-23: mixed single-qubit marginals alone do not prove n - 1 (two Bell pairs: 2 CX)
            out.append({**base, "kind": "unproven_bound", "value": n - 1, "proven": False,
                        "proof": "all single-qubit marginals mixed, but entanglement across every bipartition "
                                 "was not shown: NOT a proven lower bound"})
    return out


def run(category: str, log=print) -> dict:
    recs = {"B": run_B, "D": run_D}[category](log)
    p = data_root() / "optimal" / f"{category}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    log(f"[optimal {category}] {len(recs)} records")
    return {"records": len(recs)}
