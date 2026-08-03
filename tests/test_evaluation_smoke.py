from pathlib import Path

import numpy as np

from pfn_dag_verify.evaluation import generate_panel
from pfn_dag_verify.query_bank import FIXED_SENSITIVITY_BANK
from pfn_dag_verify.storage import load_numeric_npz


def test_tiny_panel_has_replay_complete_shapes(tmp_path: Path):
    banks = np.stack(
        [
            np.array([-4.0, -3.5, -3.0, -2.5, 2.5, 3.0, 3.5, 4.0]),
            FIXED_SENSITIVITY_BANK,
        ]
    )
    path = tmp_path / "panel.npz"
    metadata = generate_panel(
        commit_sha="0123456789abcdef" * 4,
        query_banks=banks,
        n_groups=2,
        n_continuations=2,
        out_path=path,
    )
    panel = load_numeric_npz(path)
    assert panel["core"].shape == (2, 20, 2)
    assert panel["reference"].shape == (2, 10, 2)
    assert panel["continuations"].shape == (2, 2, 10, 2)
    assert panel["f0_target"].shape == (2, 2, 2, 8, 100)
    assert panel["eligible_replace"].shape == (2, 2)
    assert metadata["panel_sha256"]
