"""Phase B verification suite: determinism, cross-simulator equivalence,
golden-file regression, and the A7 sweep findings (documented limitations).

Heavy runs use the default 168-macro mockup configuration; the Verilator
binary must be the default build (`make -C rtl_legalizer/verilator`).
"""

import os
import re
import shutil
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from rtl_legalizer import audit, golden_model as gm, layout_gen  # noqa: E402

RTL_DIR = os.path.join(PROJECT_ROOT, "rtl_legalizer")
SIM = os.path.join(RTL_DIR, "verilator", "legalizer_sim")
GOLDEN_DIR = os.path.join(PROJECT_ROOT, "tests", "data", "golden")

RTL_SOURCES = ["collision_check.v", "iter_div.v", "lfsr32.v", "sa_cost.v",
               "sa_engine.v", "legalizer_fsm.v", "sa_legalizer_top.v",
               "legalizer_tb.v"]


def run_icarus_legalizer(input_hex, tmp_path, timeout=600):
    """Compile once per call, run legalizer_tb in tmp_path. Returns (rc, out, words)."""
    shutil.copyfile(input_hex, str(tmp_path / "dummy_layout.hex"))
    sim_out = tmp_path / "sim.out"
    cmd = ["iverilog", "-o", str(sim_out), "-Plegalizer_tb.NUM_LINES=672"]
    cmd += [os.path.join(RTL_DIR, s) for s in RTL_SOURCES]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=RTL_DIR, timeout=timeout)
    assert res.returncode == 0, res.stderr
    res_sim = subprocess.run(["vvp", str(sim_out)], capture_output=True, text=True,
                             cwd=tmp_path, timeout=timeout)
    words = None
    out_file = tmp_path / "output_layout.hex"
    if out_file.exists():
        words = audit.read_hex_words(str(out_file))
    return res_sim.returncode, res_sim.stdout, words


def run_verilator_legalizer(input_hex, tmp_path):
    """Run the default Verilator binary in tmp_path. Returns (rc, out, words)."""
    assert os.path.isfile(SIM), "Verilator binary missing: make -C rtl_legalizer/verilator"
    shutil.copyfile(input_hex, str(tmp_path / "dummy_layout.hex"))
    res = subprocess.run([SIM, str(tmp_path / "out.hex")], capture_output=True,
                         text=True, cwd=tmp_path, timeout=300)
    words = None
    out_file = tmp_path / "out.hex"
    if out_file.exists():
        words = audit.read_hex_words(str(out_file))
    return res.returncode, res.stdout, words


GOLDEN_INPUT = os.path.join(GOLDEN_DIR, "golden_input_168.hex")


class TestDeterminism:
    def test_icarus_two_runs_identical(self, tmp_path):
        results = [run_icarus_legalizer(GOLDEN_INPUT, tmp_path) for _ in range(2)]
        words0, words1 = results[0][2], results[1][2]
        assert words0 == words1
        cycles = [re.search(r"complete in (\d+) clock cycles", r[1]).group(1)
                  for r in results]
        assert cycles[0] == cycles[1]

    def test_verilator_two_runs_identical(self, tmp_path):
        results = [run_verilator_legalizer(GOLDEN_INPUT, tmp_path) for _ in range(2)]
        assert results[0][2] == results[1][2]
        cycles = [re.search(r"Clock Cycles\s+: (\d+)", r[1]).group(1)
                  for r in results]
        assert cycles[0] == cycles[1]


class TestSimulatorEquivalence:
    def test_icarus_matches_verilator_on_mockup(self, tmp_path):
        rc_i, out_i, words_i = run_icarus_legalizer(GOLDEN_INPUT, tmp_path)
        assert rc_i == 0, out_i
        rc_v, out_v, words_v = run_verilator_legalizer(GOLDEN_INPUT, tmp_path)
        assert rc_v == 0, out_v

        assert words_i == words_v, "Icarus and Verilator outputs diverge"

        cost_i = re.search(r"Final Cost\s+: (\d+)", out_i).group(1)
        cost_v = re.search(r"Final Cost\s+: (\d+)", out_v).group(1)
        assert cost_i == cost_v

        cyc_i = int(re.search(r"complete in (\d+) clock cycles", out_i).group(1))
        cyc_v = int(re.search(r"Clock Cycles\s+: (\d+)", out_v).group(1))
        # The two harnesses count the start/done edges at slightly different
        # boundaries (one-cycle offset). RTL cycle behavior is identical, as
        # proven by the byte-identical outputs and matching SA metrics above.
        assert abs(cyc_i - cyc_v) <= 1, "cycle counts differ between simulators"


class TestGoldenRegression:
    def test_verilator_matches_golden_output(self, tmp_path):
        rc, out, words = run_verilator_legalizer(GOLDEN_INPUT, tmp_path)
        assert rc == 0, out
        golden = audit.read_hex_words(os.path.join(GOLDEN_DIR, "golden_output_168.hex"))
        assert words == golden

        metrics = open(os.path.join(GOLDEN_DIR, "golden_metrics.txt")).read()
        golden_cost = re.search(r"Final Cost\s+: (\d+)", metrics).group(1)
        run_cost = re.search(r"Final Cost\s+: (\d+)", out).group(1)
        assert run_cost == golden_cost


class TestSweepFindings:
    """A7 sweep results, encoded as documented behavior of the current RTL."""

    def test_easy_modes_fully_legal(self):
        for mode in ("single", "legal"):
            for n in (2, 8, 24, 64, 168):
                for seed in range(3):
                    macros = layout_gen.gen_layout(mode, n, seed=seed)
                    words = [v & 0xFFFFFFFF for m in macros for v in m]
                    out, _ = gm.legalize_model(words)
                    res = audit.check_layout(audit.to_macros(words), audit.to_macros(out))
                    assert res.passed, f"{mode}/n={n}/seed={seed}: {res.summary_lines()}"

    def test_wide_macro_containment_unfixable(self):
        # A macro wider than the die can never satisfy containment; the RTL
        # clamps it to x=0 and the audit flags it. Documented limitation.
        macros = layout_gen.gen_layout("wide_macro", 8, seed=0)
        words = [v & 0xFFFFFFFF for m in macros for v in m]
        out, _ = gm.legalize_model(words)
        res = audit.check_layout(audit.to_macros(words), audit.to_macros(out))
        assert res.boundary_violations
        assert all(axis == "x" for _, axis, _ in res.boundary_violations)
        assert not res.size_mismatches

    def test_dense_layout_residual_overlaps_known_limitation(self, tmp_path):
        # The 8-sweep greedy cap cannot untangle dense clusters. RTL-confirmed
        # on seed 0: with the SA legality scan (SA no longer wanders into
        # overlapping states), the pipeline leaves exactly 3 overlaps on this
        # input and the hardened testbench exits non-zero ($fatal). If a
        # future RTL change fixes convergence, this test should be updated to
        # require zero overlaps instead.
        macros = layout_gen.gen_layout("dense", 24, seed=0)
        words = [v & 0xFFFFFFFF for m in macros for v in m]
        out, _ = gm.legalize_model(words)
        res = audit.check_layout(audit.to_macros(words), audit.to_macros(out))
        assert len(res.overlaps) == 3
        assert not res.boundary_violations and not res.size_mismatches

    def test_dense_residual_overlaps_confirmed_on_rtl(self, tmp_path):
        macros = layout_gen.gen_layout("dense", 24, seed=0)
        words = [v & 0xFFFFFFFF for m in macros for v in m]
        layout_gen.write_hex(audit.to_macros(words), str(tmp_path / "dummy_layout.hex"))
        sim_out = tmp_path / "sim.out"
        cmd = ["iverilog", "-o", str(sim_out), "-Plegalizer_tb.NUM_LINES=96"]
        cmd += [os.path.join(RTL_DIR, s) for s in RTL_SOURCES]
        res_c = subprocess.run(cmd, capture_output=True, text=True, cwd=RTL_DIR)
        assert res_c.returncode == 0, res_c.stderr
        res_r = subprocess.run(["vvp", str(sim_out)], capture_output=True,
                               text=True, cwd=tmp_path, timeout=600)
        assert res_r.returncode == 1, "expected $fatal on residual overlaps"
        assert "AUDIT FAIL: 3 overlaps remain" in res_r.stdout
        assert "AUDIT PASS: All macro sizes preserved." in res_r.stdout
