"""Staged validation of the Python golden model against the RTL.

Stage 1: cost_model   vs sa_cost.v        (directed + real-scale vectors)
Stage 2: greedy model vs legalizer_fsm.v  (random layouts, exact words)
Stage 3: sa_model     vs sa_engine.v      (full trajectory + final metrics)

All comparisons are exact (word-for-word / integer equality), not tolerance
based: the model replicates the RTL arithmetic bit for bit.
"""

import os
import re
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from rtl_legalizer import audit, golden_model as gm, layout_gen  # noqa: E402

RTL_DIR = os.path.join(PROJECT_ROOT, "rtl_legalizer")
GOLDEN_DIR = os.path.join(PROJECT_ROOT, "tests", "data", "golden")


def compile_and_run(tb_name, sources, tmp_path, params=None, sim_cwd=None, timeout=300):
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


class TestStage1Cost:
    def test_directed_scenarios_match_tb_sa_cost_values(self):
        # The four hand-computed scenarios from tb_sa_cost.v (RTL-validated).
        cases = [
            ([(100, 200, 50, 60), (300, 400, 100, 100)], (91780, 445, 90000, 0)),
        ]
        # Negative-x and overflow scenarios use 32-bit patterns.
        nx = [(0xFFFFFFCE, 200, 100, 100), (300, 400, 100, 100)]
        cases.append((nx, (32600, 550, 30000, 50)))
        ro = [(950, 100, 100, 50), (0, 0, 10, 10)]
        cases.append((ro, (162360, 1115, 157500, 50)))
        ny = [(100, 0xFFFFFFD8, 100, 50), (0, 0, 10, 10)]
        cases.append((ny, (2820, 125, 2000, 40)))

        for macros, expected in cases:
            words = [v for m in macros for v in m]
            # tb_sa_cost.v config: die 1000x1000, AREA_SCALE_SHIFT=0.
            got = gm.cost_model(words, die_width=1000, die_height=1000,
                                area_scale_shift=0)
            assert got == expected, f"{macros}: {got} != {expected}"

    def test_real_scale_vector_matches_sa_cost(self, tmp_path):
        src = os.path.join(GOLDEN_DIR, "golden_input_168.hex")
        words = audit.read_hex_words(src)
        layout_gen.write_hex(audit.to_macros(words), str(tmp_path / "dummy_layout.hex"))
        rc, out, err = compile_and_run(
            "tb_cost_vectors", ["sa_cost.v", "tb_cost_vectors.v"], tmp_path,
            params={"NUM_LINES": 672}, sim_cwd=tmp_path)
        assert rc == 0, err
        m = re.search(r"COST (\d+) (\d+) (\d+) (\d+)", out)
        assert m, f"no COST line in:\n{out}"
        rtl_vals = tuple(int(g) for g in m.groups())
        assert gm.cost_model(words) == rtl_vals

    def test_out_of_bounds_real_scale_vector(self, tmp_path):
        macros = layout_gen.gen_layout("out_of_bounds", 24, seed=9)
        words = [v for m in macros for v in m]
        layout_gen.write_hex(macros, str(tmp_path / "dummy_layout.hex"))
        rc, out, err = compile_and_run(
            "tb_cost_vectors", ["sa_cost.v", "tb_cost_vectors.v"], tmp_path,
            params={"NUM_LINES": 96}, sim_cwd=tmp_path)
        assert rc == 0, err
        m = re.search(r"COST (\d+) (\d+) (\d+) (\d+)", out)
        assert m, out
        rtl_vals = tuple(int(g) for g in m.groups())
        assert gm.cost_model(words) == rtl_vals


class TestStage2Greedy:
    @pytest.mark.parametrize("mode,seed", [
        ("chain", 1), ("dense", 2), ("pair_overlap", 3),
        ("out_of_bounds", 4), ("legal", 5), ("dense", 6),
    ])
    def test_greedy_matches_rtl_word_for_word(self, tmp_path, mode, seed):
        macros = layout_gen.gen_layout(mode, 8, seed=seed)
        words = [v for m in macros for v in m]
        layout_gen.write_hex(macros, str(tmp_path / "dummy_layout.hex"))
        rc, out, err = compile_and_run(
            "tb_legalizer_fsm",
            ["collision_check.v", "legalizer_fsm.v", "tb_legalizer_fsm.v"],
            tmp_path,
            params={"NUM_LINES": 32, "DIE_WIDTH": 200260, "DIE_HEIGHT": 201600},
            sim_cwd=tmp_path)
        assert rc == 0, f"{out}\n{err}"
        rtl_out = audit.read_hex_words(str(tmp_path / "out.hex"))
        assert gm.greedy_model(words) == rtl_out, f"{mode}/{seed} diverged"


class TestStage3SA:
    def test_sa_full_trajectory_matches_rtl(self, tmp_path):
        # 8-macro dense layout, 1000 iterations: selection stream, cost
        # sequence, and final metrics must all match the RTL trace exactly.
        # MET lines are legal iterations (Metropolis accept/reject); ILLEGAL
        # lines are candidates rejected by the RTL legality scan.
        macros = layout_gen.gen_layout("dense", 8, seed=42)
        layout_gen.write_hex(macros, str(tmp_path / "dummy_layout.hex"))
        rc, out, err = compile_and_run(
            "tb_sa_trace",
            ["collision_check.v", "iter_div.v", "lfsr32.v", "sa_cost.v",
             "sa_engine.v", "tb_sa_trace.v"],
            tmp_path, params={"NUM_LINES": 32}, sim_cwd=tmp_path)
        assert rc == 0, err

        lines = out.splitlines()
        final = next(l for l in lines if l.startswith("FINAL")).split()
        met = [l.split() for l in lines if l.startswith("MET")]
        illegal = [l.split() for l in lines if l.startswith("ILLEGAL")]

        words = [v for m in macros for v in m]
        track = []
        _, metrics = gm.sa_model(words, track=track)

        # The RTL interleaves MET/ILLEGAL lines in iteration order; the golden
        # side knows which iterations were illegal. Walk both streams.
        met_iter = iter(met)
        illegal_iter = iter(illegal)
        cost_mismatches = 0
        for entry in track:
            if entry[5]:  # legality-scan reject
                line = next(illegal_iter, None)
                if line is None or int(line[1]) != entry[4]:
                    cost_mismatches += 1
            else:
                line = next(met_iter, None)
                if line is None or int(line[4]) != entry[4]:
                    cost_mismatches += 1
        assert cost_mismatches == 0, f"{cost_mismatches} cost transitions diverged"
        assert metrics["illegal_rejects"] == len(illegal)
        assert metrics["final_cost"] == int(final[1])
        assert metrics["final_temp"] == int(final[2])
        assert metrics["total_iters"] == int(final[3])
        assert metrics["accepted_count"] == int(final[4])

    def test_full_pipeline_matches_rtl_on_mockup(self, tmp_path):
        # End-to-end: SA + greedy golden model vs legalizer_tb (Icarus,
        # default parameters, 168-macro mockup input).
        src = os.path.join(GOLDEN_DIR, "golden_input_168.hex")
        words = audit.read_hex_words(src)
        layout_gen.write_hex(audit.to_macros(words), str(tmp_path / "dummy_layout.hex"))
        rc, out, err = compile_and_run(
            "legalizer_tb",
            ["collision_check.v", "iter_div.v", "lfsr32.v", "sa_cost.v",
             "sa_engine.v", "legalizer_fsm.v", "sa_legalizer_top.v",
             "legalizer_tb.v"],
            tmp_path, params={"NUM_LINES": 672}, sim_cwd=tmp_path, timeout=600)
        assert rc == 0, f"{out}\n{err}"

        rtl_out = audit.read_hex_words(str(tmp_path / "output_layout.hex"))
        model_out, metrics = gm.legalize_model(words)
        assert model_out == rtl_out, "full pipeline memory diverged from model"

        m = re.search(r"Final Cost\s+: (\d+)", out)
        assert m and metrics["final_cost"] == int(m.group(1))
        m = re.search(r"Accepted Moves\s+: (\d+)", out)
        assert m and metrics["accepted_count"] == int(m.group(1))
