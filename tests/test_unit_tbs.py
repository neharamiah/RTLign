"""Unit testbenches for the rtl_legalizer Verilog modules (Icarus).

- tb_collision_check.v: directed AABB corner matrix, self-checking.
- tb_sa_cost.v: directed cost scenarios with hand-computed expected values,
  replicating the exact unsigned/signed RTL arithmetic.
- tb_legalizer_fsm.v: generic greedy-sweep driver; this file supplies the
  input hex and asserts exact resolved coordinates (hand-computed).
"""

import os
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from rtl_legalizer import audit, layout_gen  # noqa: E402

RTL_DIR = os.path.join(PROJECT_ROOT, "rtl_legalizer")
DIE_W, DIE_H = 1000, 800


def run_icarus(tb_name, sources, tmp_path, params=None, timeout=120, sim_cwd=None):
    """Compile a TB with iverilog, run with vvp, return (rc, stdout, stderr).

    sim_cwd sets the vvp working directory (matters for TBs that read or
    write relative-path hex files); defaults to rtl_legalizer.
    """
    sim_out = tmp_path / "sim.out"
    cmd = ["iverilog", "-o", str(sim_out)]
    for name, value in (params or {}).items():
        cmd.append(f"-P{tb_name}.{name}={value}")
    cmd += [os.path.join(RTL_DIR, s) for s in sources]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=RTL_DIR, timeout=timeout)
    assert res.returncode == 0, f"iverilog failed: {res.stderr}"
    res_sim = subprocess.run(["vvp", str(sim_out)], capture_output=True, text=True,
                             cwd=sim_cwd or RTL_DIR, timeout=timeout)
    return res_sim.returncode, res_sim.stdout, res_sim.stderr


class TestCollisionCheck:
    def test_directed_corner_matrix(self, tmp_path):
        rc, out, err = run_icarus(
            "tb_collision_check", ["collision_check.v", "tb_collision_check.v"], tmp_path)
        assert rc == 0, f"stdout:\n{out}\nstderr:\n{err}"
        assert "ALL COLLISION CHECKS PASSED" in out


class TestSaCost:
    def test_directed_cost_scenarios(self, tmp_path):
        rc, out, err = run_icarus(
            "tb_sa_cost", ["sa_cost.v", "tb_sa_cost.v"], tmp_path)
        assert rc == 0, f"stdout:\n{out}\nstderr:\n{err}"
        assert "ALL COST CHECKS PASSED" in out


class TestLegalizerFSM:
    def run_fsm(self, macros, tmp_path, die_w=DIE_W, die_h=DIE_H):
        num_lines = 4 * len(macros)
        layout_gen.write_hex(macros, str(tmp_path / "dummy_layout.hex"))
        rc, out, err = run_icarus(
            "tb_legalizer_fsm", ["collision_check.v", "legalizer_fsm.v",
                                 "tb_legalizer_fsm.v"],
            tmp_path,
            params={"NUM_LINES": num_lines, "DIE_WIDTH": die_w, "DIE_HEIGHT": die_h},
            sim_cwd=tmp_path)
        assert rc == 0, f"TB failed (hang or audit):\n{out}\n{err}"
        assert "FSM DONE" in out
        return audit.to_macros(audit.read_hex_words(str(tmp_path / "out.hex")))

    def test_push_right_on_min_x_overlap(self, tmp_path):
        # overlap_x=20 < overlap_y=80 -> horizontal push to A's right edge.
        in_macros = [(100, 100, 300, 100), (380, 120, 100, 100)]
        out = self.run_fsm(in_macros, tmp_path)
        assert out == [(100, 100, 300, 100), (400, 120, 100, 100)]

    def test_push_up_on_min_y_overlap(self, tmp_path):
        # overlap_y=20 < overlap_x=50 -> vertical push to A's top edge.
        in_macros = [(100, 100, 300, 100), (150, 180, 50, 100)]
        out = self.run_fsm(in_macros, tmp_path)
        assert out == [(100, 100, 300, 100), (150, 200, 50, 100)]

    def test_vertical_push_even_when_b_left_of_a(self, tmp_path):
        # overlap_x=80 > overlap_y=60: the min-overlap axis is y, so the push
        # is vertical even though B sits left of A. y2(120) >= y1(100) ->
        # B.y = top1 = 200. Pins the "push along minimum-overlap axis" rule.
        in_macros = [(500, 100, 200, 100), (480, 120, 100, 60)]
        out = self.run_fsm(in_macros, tmp_path)
        assert out == [(500, 100, 200, 100), (480, 200, 100, 60)]

    def test_push_down_when_b_above_a(self, tmp_path):
        # Tie (overlap_x == overlap_y == 50): first pair has ptr_b[2]=1, so
        # the even-pass tie-break picks vertical. B above A -> pushed down to
        # y1 - h2 = 500 - 150 = 350.
        in_macros = [(100, 500, 200, 100), (120, 400, 50, 150)]
        out = self.run_fsm(in_macros, tmp_path)
        assert out == [(100, 500, 200, 100), (120, 350, 50, 150)]

    def test_die_edge_wrap_to_left_of_a(self, tmp_path):
        # Push right would exceed the die (980+100 > 1000) -> B wraps to
        # x1 - w2 = 900 - 100 = 800, touching A's left edge.
        in_macros = [(900, 100, 80, 100), (950, 120, 100, 100)]
        out = self.run_fsm(in_macros, tmp_path)
        assert out == [(900, 100, 80, 100), (800, 120, 100, 100)]

    def test_three_macro_chain_resolves_clean(self, tmp_path):
        # Hand-traced: (A,B) is a tie -> vertical (ptr_b[2]=1 on first pair);
        # (A,C) vertical push; (B,C) horizontal left-push. All pairs end
        # edge-touching, which is legal.
        in_macros = [(100, 100, 200, 100), (250, 120, 100, 50), (180, 140, 80, 80)]
        out = self.run_fsm(in_macros, tmp_path)
        assert out == [(100, 100, 200, 100), (250, 200, 100, 50), (170, 200, 80, 80)]
        res = audit.check_layout(in_macros, out, DIE_W, DIE_H)
        assert res.passed

    def test_single_macro_terminates(self, tmp_path):
        # NUM_MACROS == 1: last_base - 4 wraps, so the sweep reads far out of
        # bounds. It must still terminate and leave the macro untouched.
        in_macros = [(100, 100, 200, 100)]
        out = self.run_fsm(in_macros, tmp_path)
        assert out == in_macros

    def test_unresolvable_pair_terminates(self, tmp_path):
        # Two die-wide macros whose heights overflow the die cannot be
        # separated on any axis. The FSM must still assert done (the layout
        # stays overlapping; the audit layer reports it).
        in_macros = [(0, 0, 1000, 500), (0, 200, 1000, 500)]
        self.run_fsm(in_macros, tmp_path)  # hangs forever before the fix
