"""Unit tests for rtl_legalizer/audit.py and rtl_legalizer/layout_gen.py."""

import os
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from rtl_legalizer import audit, layout_gen  # noqa: E402

DIE_W, DIE_H = 1000, 800


class TestCheckLayout:
    def test_clean_layout_passes(self):
        macros = [(0, 0, 10, 10), (10, 0, 10, 10), (0, 10, 10, 10)]
        res = audit.check_layout(macros, macros, DIE_W, DIE_H)
        assert res.passed

    def test_touching_edges_do_not_overlap(self):
        # Strict AABB: shared edges are legal.
        macros = [
            (0, 0, 10, 10), (10, 0, 10, 10),   # touch on x
            (0, 10, 10, 10),                   # touch on y
        ]
        res = audit.check_layout(macros, macros, DIE_W, DIE_H)
        assert res.overlaps == []
        assert res.passed

    def test_overlap_detected_with_pair(self):
        in_macros = [(0, 0, 10, 10), (5, 0, 10, 10)]
        res = audit.check_layout(in_macros, in_macros, DIE_W, DIE_H)
        assert res.overlaps == [(0, 1)]
        assert not res.passed

    def test_identical_boxes_overlap(self):
        m = [(20, 20, 10, 10), (20, 20, 10, 10)]
        res = audit.check_layout(m, m, DIE_W, DIE_H)
        assert res.overlaps == [(0, 1)]

    def test_negative_x_violates_containment(self):
        m = [(-1, 0, 10, 10)]
        res = audit.check_layout(m, m, DIE_W, DIE_H)
        assert [v[1] for v in res.boundary_violations] == ["x"]

    def test_right_edge_outside_die(self):
        m = [(995, 0, 10, 10)]
        res = audit.check_layout(m, m, DIE_W, DIE_H)
        assert res.boundary_violations == [(0, "x", "x=995 x+w=1005 die_w=1000")]

    def test_bottom_edge_outside_die(self):
        m = [(0, 795, 10, 10)]
        res = audit.check_layout(m, m, DIE_W, DIE_H)
        assert [v[1] for v in res.boundary_violations] == ["y"]

    def test_size_mismatch_detected(self):
        in_macros = [(0, 0, 10, 10)]
        out_macros = [(5, 5, 9, 10)]
        res = audit.check_layout(in_macros, out_macros, DIE_W, DIE_H)
        assert res.size_mismatches == [(0, "width", 10, 9)]
        assert not res.passed

    def test_macro_count_mismatch_is_structural_error(self):
        res = audit.check_layout([(0, 0, 1, 1)], [], DIE_W, DIE_H)
        assert res.errors
        assert not res.passed

    def test_wrapped_32bit_coordinate_flagged(self):
        # A "negative" stored coordinate is a huge unsigned word; the sum
        # must not wrap back into the die and hide the violation.
        m = [(0xFFFFFFFF, 0, 10, 10)]
        res = audit.check_layout(m, m, DIE_W, DIE_H)
        assert res.boundary_violations


class TestHexIO:
    def test_read_hex_words_strips_comments(self, tmp_path):
        p = tmp_path / "w.hex"
        p.write_text(
            "// 0x00000000:\n"
            "0000000A // X coord\n"
            "00000014 // Y coord\n"
            "0000000a // Width\n"
            "0000000a // Height\n"
            "\n"
        )
        assert audit.read_hex_words(str(p)) == [10, 20, 10, 10]

    def test_to_macros_groups_fours(self):
        assert audit.to_macros([1, 2, 3, 4, 5, 6, 7, 8]) == [(1, 2, 3, 4), (5, 6, 7, 8)]
        with pytest.raises(ValueError):
            audit.to_macros([1, 2, 3])

    def test_roundtrip_write_and_read(self, tmp_path):
        macros = [(100, 200, 30, 40)]
        p = tmp_path / "rt.hex"
        layout_gen.write_hex(macros, str(p))
        assert audit.to_macros(audit.read_hex_words(str(p))) == macros

    def test_audit_layout_cli_exit_codes(self, tmp_path):
        in_hex = tmp_path / "in.hex"
        layout_gen.write_hex([(0, 0, 10, 10), (5, 0, 10, 10)], str(in_hex))
        out_hex = tmp_path / "out.hex"
        layout_gen.write_hex([(0, 0, 10, 10), (10, 0, 10, 10)], str(out_hex))
        rc = subprocess.run(
            [sys.executable, os.path.join(PROJECT_ROOT, "rtl_legalizer", "audit.py"),
             str(in_hex), str(out_hex), "--die-width", "1000", "--die-height", "800"],
            capture_output=True, text=True)
        assert rc.returncode == 0
        assert "AUDIT PASS" in rc.stdout

        bad_hex = tmp_path / "bad.hex"
        layout_gen.write_hex([(0, 0, 10, 10), (5, 0, 10, 10)], str(bad_hex))
        rc = subprocess.run(
            [sys.executable, os.path.join(PROJECT_ROOT, "rtl_legalizer", "audit.py"),
             str(in_hex), str(bad_hex), "--die-width", "1000", "--die-height", "800"],
            capture_output=True, text=True)
        assert rc.returncode == 1
        assert "AUDIT FAIL" in rc.stdout


class TestLayoutGen:
    @pytest.mark.parametrize("mode", layout_gen.MODES)
    @pytest.mark.parametrize("n", [1, 2, 8, 24])
    def test_word_count_is_four_per_macro(self, mode, n):
        macros = layout_gen.gen_layout(mode, n, seed=1, die_w=DIE_W, die_h=DIE_H)
        expected = 1 if mode == "single" else n
        assert len(macros) == expected

    def test_deterministic_for_same_seed(self):
        a = layout_gen.gen_layout("dense", 8, seed=7, die_w=DIE_W, die_h=DIE_H)
        b = layout_gen.gen_layout("dense", 8, seed=7, die_w=DIE_W, die_h=DIE_H)
        assert a == b

    def test_legal_mode_has_no_overlaps(self):
        macros = layout_gen.gen_layout("legal", 24, seed=3, die_w=DIE_W, die_h=DIE_H)
        res = audit.check_layout(macros, macros, DIE_W, DIE_H)
        assert res.overlaps == []
        assert res.boundary_violations == []

    def test_pair_overlap_overlaps(self):
        macros = layout_gen.gen_layout("pair_overlap", 2, seed=5, die_w=DIE_W, die_h=DIE_H)
        res = audit.check_layout(macros, macros, DIE_W, DIE_H)
        assert res.overlaps == [(0, 1)]

    def test_chain_neighbors_overlap(self):
        macros = layout_gen.gen_layout("chain", 8, seed=2, die_w=DIE_W, die_h=DIE_H)
        res = audit.check_layout(macros, macros, DIE_W, DIE_H)
        pairs = set(res.overlaps)
        assert (0, 1) in pairs or (1, 2) in pairs

    def test_dense_has_many_overlaps(self):
        macros = layout_gen.gen_layout("dense", 8, seed=4, die_w=DIE_W, die_h=DIE_H)
        res = audit.check_layout(macros, macros, DIE_W, DIE_H)
        assert len(res.overlaps) >= 4

    def test_out_of_bounds_has_boundary_violations(self):
        macros = layout_gen.gen_layout("out_of_bounds", 8, seed=6, die_w=DIE_W, die_h=DIE_H)
        res = audit.check_layout(macros, macros, DIE_W, DIE_H)
        assert res.boundary_violations

    def test_wide_macro_exceeds_die(self):
        macros = layout_gen.gen_layout("wide_macro", 4, seed=8, die_w=DIE_W, die_h=DIE_H)
        assert any(w > DIE_W for (_, _, w, _) in macros)

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError):
            layout_gen.gen_layout("nope", 4, seed=1)
