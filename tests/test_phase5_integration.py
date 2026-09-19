"""
Integration tests for Phase 5 ML Predictor and Evaluation Pipeline.
"""

import os
import sys
import tempfile
import pytest
import subprocess
import networkx as nx
import pandas as pd

from ml_predictor.hex_to_def import read_hex_coordinates, inject_coords_into_def
from ml_predictor.predict import resolve_topological_coordinates, get_die_bounds

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPredictCLIValidation:
    def test_missing_required_flags_exits_with_error(self):
        """run_predict.py requires --def_file and --lef_file."""
        cmd = [sys.executable, os.path.join(PROJECT_ROOT, "run_predict.py")]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        assert "--def_file" in output or "required" in output


class TestTopologicalResolution:
    def test_resolve_coordinates_within_die(self):
        """Verify that topological resolution creates valid coordinates inside die bounds."""
        G = nx.DiGraph()
        G.add_edge("m0", "m1")
        G.add_edge("m1", "m2")

        df = pd.DataFrame(
            [
                {"width": 200, "height": 300},
                {"width": 250, "height": 350},
                {"width": 150, "height": 200},
            ],
            index=["m0", "m1", "m2"]
        )

        coords = resolve_topological_coordinates(G, df, ["m0", "m1", "m2"], die_width=2000, die_height=2000, spacing=50)
        assert len(coords) == 3
        # Check that x, y are >= 0 and within die bounds
        for x, y, w, h in coords:
            assert x >= 0
            assert y >= 0
            assert x + w <= 2000
            assert y + h <= 2000


class TestHexToDefNameMatching:
    def test_name_based_injection(self):
        """Verify targeted macro injection leaves other components untouched."""
        sample_def = """VERSION 5.8 ;
DESIGN test ;
COMPONENTS 4 ;
    - m0 MACRO1 + FIXED ( 10 20 ) N ;
    - cell_std1 INV_X1 + PLACED ( 100 200 ) N ;
    - m1 MACRO2 + UNPLACED ;
    - cell_std2 NAND_X1 + PLACED ( 300 400 ) FS ;
END COMPONENTS
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            def_in = os.path.join(tmpdir, "in.def")
            def_out = os.path.join(tmpdir, "out.def")
            with open(def_in, "w") as f:
                f.write(sample_def)

            coords = [(500, 600), (700, 800)]
            names = ["m0", "m1"]

            inject_coords_into_def(def_in, coords, def_out, names=names)

            with open(def_out, "r") as f:
                content = f.read()

            # m0 should be updated and converted to PLACED
            assert "- m0 MACRO1 + PLACED ( 500 600 ) N ;" in content
            # m1 should be placed
            assert "- m1 MACRO2 + PLACED ( 700 800 ) N" in content
            # Standard cells must be preserved unchanged
            assert "- cell_std1 INV_X1 + PLACED ( 100 200 ) N ;" in content
            assert "- cell_std2 NAND_X1 + PLACED ( 300 400 ) FS ;" in content

    def test_sequential_fallback(self):
        """Verify sequential mode works when no names are provided."""
        sample_def = """VERSION 5.8 ;
DESIGN test ;
COMPONENTS 2 ;
    - inst_a CELL1 + PLACED ( 10 20 ) N ;
    - inst_b CELL2 + PLACED ( 30 40 ) N ;
END COMPONENTS
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            def_in = os.path.join(tmpdir, "in.def")
            def_out = os.path.join(tmpdir, "out.def")
            with open(def_in, "w") as f:
                f.write(sample_def)

            coords = [(111, 222), (333, 444)]
            inject_coords_into_def(def_in, coords, def_out, names=None)

            with open(def_out, "r") as f:
                content = f.read()

            assert "( 111 222 )" in content
            assert "( 333 444 )" in content
