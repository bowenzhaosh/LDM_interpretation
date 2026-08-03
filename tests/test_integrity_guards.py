import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pytest

import pfn_dag_verify.evaluation as evaluation
from pfn_dag_verify.analysis import _bootstrap_nmae, _nmae
from pfn_dag_verify.evaluation import _validate_prediction_shard
from pfn_dag_verify.provenance import derive_seed, evaluation_root
from pfn_dag_verify.registry import sha256_file
from pfn_dag_verify.seal import _canonical_tree_hash, _create_archive, _verify_archive


TEST_COMMIT = "0123456789abcdef0123456789abcdef01234567"


def test_seed_chain_matches_locked_two_stage_vectors_and_keeps_high_bit():
    root = int.from_bytes(
        hashlib.sha256(
            (TEST_COMMIT + "pfn-dag-essential-evaluation-v2").encode("ascii")
        ).digest()[:8],
        "big",
    )
    assert evaluation_root(TEST_COMMIT) == root == 4_849_711_420_112_403_902
    assert derive_seed(TEST_COMMIT, "groups") == 2_118_269_529_734_854_837
    assert (
        derive_seed(TEST_COMMIT, "bootstrap:replace:slope")
        == 13_438_655_072_475_084_798
    )
    assert derive_seed(TEST_COMMIT, "permutation:replace") > 2**63


def _valid_prediction_shard():
    probabilities = np.full((2, 8, 100), 0.01, dtype=np.float32)
    return {
        "p_core": probabilities.copy(),
        "p_base": probabilities.copy(),
        "p_target": np.broadcast_to(probabilities[:, None], (2, 3, 8, 100)).copy(),
        "query_bank": np.arange(8, dtype=np.float64),
        "checkpoint_sha256": np.frombuffer(bytes.fromhex("11" * 32), dtype=np.uint8),
        "panel_sha256": np.frombuffer(bytes.fromhex("22" * 32), dtype=np.uint8),
        "seed": np.asarray(4, dtype=np.int16),
        "step": np.asarray(12_000, dtype=np.int32),
        "bank_index": np.asarray(1, dtype=np.int8),
        "scientific": np.asarray(1, dtype=np.int8),
    }


def _check_prediction(shard):
    _validate_prediction_shard(
        shard,
        core_count=2,
        continuation_count=3,
        queries=np.arange(8, dtype=np.float64),
        seed=4,
        step=12_000,
        bank_index=1,
        checkpoint_sha256="11" * 32,
        panel_sha256="22" * 32,
        scientific=True,
    )


def test_prediction_resume_schema_fails_closed_on_every_load_bearing_identity():
    shard = _valid_prediction_shard()
    _check_prediction(shard)
    mutations = []
    wrong_target = _valid_prediction_shard()
    wrong_target["p_target"][:] = 0
    mutations.append(wrong_target)
    wrong_query = _valid_prediction_shard()
    wrong_query["query_bank"] = wrong_query["query_bank"][::-1]
    mutations.append(wrong_query)
    wrong_panel = _valid_prediction_shard()
    wrong_panel["panel_sha256"] = np.zeros(32, dtype=np.uint8)
    mutations.append(wrong_panel)
    wrong_checkpoint = _valid_prediction_shard()
    wrong_checkpoint["checkpoint_sha256"] = np.zeros(32, dtype=np.uint8)
    mutations.append(wrong_checkpoint)
    wrong_shape = _valid_prediction_shard()
    wrong_shape["p_base"] = wrong_shape["p_base"][:1]
    mutations.append(wrong_shape)
    wrong_identity = _valid_prediction_shard()
    wrong_identity["step"] = np.asarray(0, dtype=np.int32)
    mutations.append(wrong_identity)
    for mutation in mutations:
        with pytest.raises(ValueError):
            _check_prediction(mutation)


class _FakeOracle:
    def __init__(self, queries, quadrature):
        pass

    @staticmethod
    def log_evidence(context):
        return float(context[-1, 0])

    def evaluate(self, context):
        return SimpleNamespace(ell=self.log_evidence(context), js=0.2)


def test_selected_cohort_uses_exactly_first_nine_passing_blocks(monkeypatch):
    monkeypatch.setattr(evaluation, "GridOracle", _FakeOracle)
    monkeypatch.setattr(evaluation, "sample_valid_sigma", lambda rng: np.eye(2))
    monkeypatch.setattr(
        evaluation,
        "sigma_to_params",
        lambda covariance, graph: SimpleNamespace(beta=0.1, b_root=1.0, b_effect=1.0),
    )

    def fake_context(rng, graph, parameters, rows):
        value = rng.uniform(-0.9, 0.9)
        result = np.zeros((rows, 2), dtype=np.float64)
        result[:, 0] = value
        return result

    monkeypatch.setattr(evaluation, "sample_context", fake_context)
    groups, selection = evaluation._select_interior_groups(
        commit_sha=TEST_COMMIT,
        query_banks=np.stack([np.arange(8), np.arange(8) + 0.5]),
        n_groups=2,
        n_continuations=8,
        max_core_candidates=20,
        max_blocks_per_core=20,
        min_within_group_sd=0.0,
    )
    accepted = np.flatnonzero(selection["candidate_core_reason"] == 0)
    np.testing.assert_array_equal(
        selection["candidate_core_acceptance_rank"][accepted], np.arange(2)
    )
    for index, core_id in enumerate(accepted):
        rows = np.flatnonzero(
            (selection["candidate_block_core_index"] == core_id)
            & (selection["candidate_block_reason"] == 0)
        )
        np.testing.assert_array_equal(
            selection["candidate_block_eligible_rank"][rows], np.arange(9)
        )
        np.testing.assert_array_equal(groups[index].reference, selection["candidate_block_context"][rows[0]])
        np.testing.assert_array_equal(
            groups[index].continuations, selection["candidate_block_context"][rows[1:]]
        )


def test_selected_cohort_cap_failure_is_nonzero(monkeypatch):
    monkeypatch.setattr(evaluation, "GridOracle", _FakeOracle)
    monkeypatch.setattr(evaluation, "sample_valid_sigma", lambda rng: np.eye(2))
    monkeypatch.setattr(
        evaluation,
        "sigma_to_params",
        lambda covariance, graph: SimpleNamespace(beta=0.1, b_root=1.0, b_effect=1.0),
    )
    monkeypatch.setattr(
        evaluation,
        "sample_context",
        lambda rng, graph, parameters, rows: np.zeros((rows, 2)),
    )
    with pytest.raises(RuntimeError, match="INCONCLUSIVE_IDENTIFIABILITY"):
        evaluation._select_interior_groups(
            commit_sha=TEST_COMMIT,
            query_banks=np.stack([np.arange(8), np.arange(8) + 0.5]),
            n_groups=1,
            n_continuations=8,
            max_core_candidates=1,
            max_blocks_per_core=8,
            min_within_group_sd=0.0,
        )


def test_content_tree_hash_is_order_sensitive_only_after_canonicalization():
    entries = [
        {"scope": "run", "path": "b", "size": 1, "sha256": "11" * 32},
        {"scope": "run", "path": "a", "size": 2, "sha256": "22" * 32},
    ]
    ordered = sorted(entries, key=lambda value: (value["scope"], value["path"]))
    first = _canonical_tree_hash(ordered)
    changed = [dict(value) for value in ordered]
    changed[0]["size"] += 1
    assert first != _canonical_tree_hash(changed)


def test_point_and_weighted_bootstrap_nmae_use_the_same_quantile_convention():
    x = np.array([[0.0, 1.0], [2.0, 100.0]])
    y = x[None, :, :] + 1.0
    mask = np.ones_like(x, dtype=bool)
    point = _nmae(x, y, mask)
    draws = _bootstrap_nmae(
        x,
        y,
        mask,
        np.random.default_rng(1),
        n_boot=1,
        resample_weights=(np.ones((1, 1), dtype=int), np.ones((1, 2), dtype=int)),
    )
    assert point == pytest.approx(0.5)
    assert draws[0] == pytest.approx(point, abs=1e-12)


def test_content_addressed_archive_contains_and_verifies_every_manifest_file(tmp_path):
    root = tmp_path / "repo"
    run_dir = root / "runs" / "one"
    run_dir.mkdir(parents=True)
    repository_file = root / "source.py"
    run_file = run_dir / "panel.npz"
    repository_file.write_bytes(b"source")
    run_file.write_bytes(b"raw")
    entries = [
        {
            "scope": "repository",
            "path": "source.py",
            "size": repository_file.stat().st_size,
            "sha256": sha256_file(repository_file),
        },
        {
            "scope": "run",
            "path": "panel.npz",
            "size": run_file.stat().st_size,
            "sha256": sha256_file(run_file),
        },
    ]
    entries.sort(key=lambda value: (value["scope"], value["path"]))
    manifest = {"content_tree_sha256": _canonical_tree_hash(entries), "files": entries}
    manifest_path = run_dir / "sealed_manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    archive = _create_archive(
        manifest_path=manifest_path,
        entries=entries,
        root=root,
        run_dir=run_dir,
    )
    assert archive.name == f"{manifest['content_tree_sha256']}.tar"
    _verify_archive(archive_path=archive, manifest_path=manifest_path, entries=entries)
    repository_file.write_bytes(b"changed")
    _verify_archive(archive_path=archive, manifest_path=manifest_path, entries=entries)
