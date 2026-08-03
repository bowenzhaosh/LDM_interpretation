import ast
import json
from pathlib import Path

import numpy as np

from pfn_dag_verify.phase1_confirmation_verify import (
    _bootstrap as independent_bootstrap,
    _point_estimates as independent_points,
)
from pfn_dag_verify.phase1_join import (
    _bootstrap as joined_bootstrap,
    _point_estimates as joined_points,
)


ROOT = Path(__file__).resolve().parents[1]


def _config():
    return json.loads((ROOT / "config/phase1_ordering_confirmation.json").read_text())


def _rows():
    config = _config()
    values = {
        name: [] for name in ("row_id", "prior_code", "evaluation_seed", "atom_seed")
    }
    values.update({name: [] for name in ("ordering_value", "deficit", "gap")})
    row_id = 0
    for prior_code, prior in enumerate(("C", "N")):
        for evaluation_seed in config["evaluation_seeds"][prior]:
            for atom in config["atom_banks"]:
                n = 356 if atom["bank_index"] < 2 else 355
                for _ in range(n):
                    values["row_id"].append(row_id)
                    values["prior_code"].append(prior_code)
                    values["evaluation_seed"].append(evaluation_seed)
                    values["atom_seed"].append(atom["seed"])
                    values["ordering_value"].append(0.2 if prior_code == 0 else 0.0)
                    cell = np.empty((3, 3), dtype=np.float64)
                    for model in range(3):
                        cell[model] = (
                            prior_code + model * 0.01 + np.array([0.1, 0.2, 0.3])
                        )
                    values["deficit"].append(cell)
                    values["gap"].append(cell + 0.5)
                    row_id += 1
    return {name: np.asarray(value) for name, value in values.items()}


def test_independent_verifier_reproduces_join_statistics_after_storage_relabel():
    config = _config()
    rows = _rows()
    permutation = np.random.default_rng(91).permutation(len(rows["row_id"]))
    shuffled = {name: value[permutation] for name, value in rows.items()}
    joined_estimates = joined_points(rows)
    independent = independent_points(shuffled)
    for name in joined_estimates:
        assert np.allclose(joined_estimates[name], independent[name], rtol=0, atol=0)
    joined_boot, joined_hashes = joined_bootstrap(rows, config)
    independent_boot, independent_hashes = independent_bootstrap(shuffled, config)
    assert joined_hashes == independent_hashes
    for name in joined_boot:
        assert np.array_equal(joined_boot[name], independent_boot[name])


def test_independent_verifier_has_no_pipeline_imports():
    path = ROOT / "src/pfn_dag_verify/phase1_confirmation_verify.py"
    tree = ast.parse(path.read_text())
    forbidden = {
        "phase1_confirm_common",
        "phase1_join",
        "phase1_oracle_confirm",
        "phase1_pfn",
    }
    imported = {
        node.module.rsplit(".", 1)[-1]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imported.isdisjoint(forbidden)
