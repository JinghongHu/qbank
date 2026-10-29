"""Category C routing contracts: positive and negative controls."""
import pytest

from qbank.categories.C import generate as G
from qbank.categories.C.instances import verify
from qbank.contracts.routing import check_routing_equiv, crosscheck_qcec
from qbank.core.circuit import Circuit

LINE = [[0, 1], [1, 2], [2, 3]]


def _orig():
    c = Circuit(3)
    c.append("h", [0])
    c.append("cx", [0, 2])
    c.append("rz", [2], [0.25])
    c.append("cx", [1, 2])
    return c


def test_valid_routing_passes_and_qcec_agrees():
    o = _orig()
    r = Circuit(4)
    r.append("h", [0])
    r.append("swap", [0, 1])          # logical 0 now at physical 1, next to logical 2 at physical 2
    r.append("cx", [1, 2])
    r.append("rz", [2], [0.25])
    r.append("cx", [0, 2])            # logical 1 sits at physical 0 after the swap
    v = check_routing_equiv(o, r, [0, 1, 2], [[0, 1], [1, 2], [0, 2], [2, 3]])
    assert v.status == "pass" and v.details["swaps"] == 1
    assert crosscheck_qcec(o, r, [0, 1, 2]).startswith("equivalent")


def test_missing_swap_fails():
    o = _orig()
    r = Circuit(4)
    r.append("h", [0])
    r.append("cx", [0, 2])
    assert check_routing_equiv(o, r, [0, 1, 2], LINE).status == "fail"


def test_wrong_parameter_and_wrong_order_fail():
    o = _orig()
    r = Circuit(4)
    r.append("h", [0])
    r.append("swap", [1, 2])
    r.append("cx", [0, 1])
    r.append("rz", [1], [0.5])        # wrong angle
    assert check_routing_equiv(o, r, [0, 1, 2], LINE).status == "fail"
    r2 = Circuit(4)
    r2.append("swap", [1, 2])
    r2.append("cx", [0, 1])           # cx before h on logical 0: violates the DAG
    r2.append("h", [0])
    assert check_routing_equiv(o, r2, [0, 1, 2], LINE).status == "fail"


def test_missing_gate_and_bad_layout_fail():
    o = _orig()
    r = Circuit(4)
    r.append("h", [0])
    assert "missing" in check_routing_equiv(o, r, [0, 1, 2], LINE).reason
    assert check_routing_equiv(o, r, [0, 0, 2], LINE).status == "fail"
    assert check_routing_equiv(o, r, [0, 1], LINE).status == "fail"


def test_commuting_blocks():
    o = Circuit(3)
    o.append("rzz", [0, 1], ["g"])
    o.append("rzz", [1, 2], ["g"])
    o.append("rx", [1], ["b"])
    blocks = [0, 0, 1]
    r = Circuit(3)                    # block-internal reorder: allowed only in the commuting contract
    r.append("rzz", [1, 2], ["g"])
    r.append("rzz", [0, 1], ["g"])
    r.append("rx", [1], ["b"])
    es = [[0, 1], [1, 2]]
    assert check_routing_equiv(o, r, [0, 1, 2], es).status == "fail"
    assert check_routing_equiv(o, r, [0, 1, 2], es, blocks).status == "pass"
    r2 = Circuit(3)                   # cross-block reorder on a qubit: rejected
    r2.append("rzz", [0, 1], ["g"])
    r2.append("rx", [1], ["b"])
    r2.append("rzz", [1, 2], ["g"])
    assert check_routing_equiv(o, r2, [0, 1, 2], es, blocks).status == "fail"


def test_instance_verify_rejects_wrong_width():
    p = G.gen("qaoa", "line", "train", "S", 3)
    pub = p.inst.public
    c = Circuit(pub["n_physical"] + 1)
    assert verify(pub, "swaps", c, list(range(pub["n_logical"]))).status == "fail"


@pytest.mark.parametrize("tool", ["qiskit LightSABRE (anytime)", "pytket LexiRoute", "mqt.qmap heuristic"])
def test_tools_pass_on_small_instance(tool):
    import time
    from qbank.baselines.tools_c import C_TOOLS
    pub = G.gen("trotter", "ring", "train", "S", 5).inst.public
    c = C_TOOLS[tool](pub, "swaps", 1, time.monotonic() + 3)[0]
    assert verify(pub, "swaps", c["circuit"], c["initial_layout"]).status == "pass"


def test_commuting_router_per_block():
    import time
    from qbank.baselines.tools_c import t_commuting
    pub = G.gen("qaoa", "line", "train", "S", 3).inst.public    # p >= 2 layers: exercises the multi-block path
    c = t_commuting(pub, "swaps_commuting", 1, time.monotonic() + 3)[0]
    assert verify(pub, "swaps_commuting", c["circuit"], c["initial_layout"]).status == "pass"
