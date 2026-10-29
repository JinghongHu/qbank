"""SAT solving with a hard time limit: CaDiCaL (fast, but not interruptible through pysat) runs in a forked child
process that is killed at the deadline.

The child is created with os.fork (not multiprocessing): baseline jobs run inside daemonic multiprocessing workers,
which multiprocessing forbids to have children ("daemonic processes are not allowed to have children"); a plain fork
has no such restriction. The result comes back through a pipe; the child also arms an alarm so that it cannot outlive
its parent.
"""
from __future__ import annotations

import os
import pickle
import select
import signal
import time


def solve_with_timeout(clauses, time_limit: float, solver: str = "cadical195", want_model: bool = False):
    """Returns ("sat", model|None) | ("unsat", None) | ("timeout", None). A crashed child counts as "timeout"."""
    if time_limit <= 0:
        return "timeout", None
    r, w = os.pipe()
    pid = os.fork()
    if pid == 0:                                              # child
        code = 0
        try:
            os.close(r)
            signal.alarm(int(time_limit) + 30)
            from pysat.solvers import Solver
            with Solver(name=solver, bootstrap_with=clauses) as s:
                res = s.solve()
                model = s.get_model() if (res and want_model) else None
            data = pickle.dumps((bool(res), model))
            view = memoryview(data)
            while view:
                n = os.write(w, view)
                view = view[n:]
            os.close(w)
        except BaseException:
            code = 1
        finally:
            os._exit(code)
    os.close(w)
    deadline = time.monotonic() + time_limit
    chunks = []
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            ready, _, _ = select.select([r], [], [], remaining)
            if not ready:
                raise TimeoutError
            chunk = os.read(r, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
    except TimeoutError:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(pid, 0)
        os.close(r)
        return "timeout", None
    os.close(r)
    os.waitpid(pid, 0)
    if not chunks:
        return "timeout", None
    sat, model = pickle.loads(b"".join(chunks))
    return ("sat" if sat else "unsat"), model


def solve_budget(clauses, conflicts: int, solver: str = "cadical195", want_model: bool = False):
    """Deterministic resource bound (v1.2): in-process solve with a conflict budget instead of a wall-clock limit.
    Returns ("sat", model|None) | ("unsat", None) | ("budget", None). The same clauses and budget give the same answer
    on every machine and under any load."""
    from pysat.solvers import Solver
    with Solver(name=solver, bootstrap_with=clauses) as s:
        s.conf_budget(int(conflicts))
        r = s.solve_limited()
        if r is None:
            return "budget", None
        return ("sat", s.get_model() if want_model else None) if r else ("unsat", None)
