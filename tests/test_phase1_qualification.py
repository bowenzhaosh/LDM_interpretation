import json
from pathlib import Path

import numpy as np
import pytest

import pfn_dag_verify.phase1_qualification as qualification
from pfn_dag_verify.phase1_ordering import (
    _sha256_file,
    _sha256_json,
    production_qualification_protocol,
)
from pfn_dag_verify.storage import write_json_atomic, write_numeric_npz_atomic


ROOT = Path(__file__).resolve().parents[1]


def _write_shard(run_dir: Path, bank_index: int, fail_first_candidate: bool) -> None:
    run_dir.mkdir(parents=True)
    config_path = ROOT / "config" / f"phase1_ordering_qualification_bank{bank_index}.json"
    config = production_qualification_protocol(bank_index)
    identity_object = {
        "config_sha256": _sha256_file(config_path),
        "fleet_sha256": config["fleet_sha256"],
        "source_inventory": {"test": f"bank-{bank_index}"},
        "git_commit": "test-qualification-commit",
        "execution_contract": {"test": True},
    }
    identity = _sha256_json(identity_object)
    identity_bytes = np.frombuffer(bytes.fromhex(identity), dtype=np.uint8)
    partial = {
        "attempt_identity_sha256": np.tile(
            identity_bytes, (2, 1)
        ),
        "completed": np.ones((2, 160), dtype=np.int8),
        "keep_full": np.ones((2, 3, 160), dtype=np.float64),
        "keep_ablated": np.ones((2, 3, 160), dtype=np.float64),
        "ess_full_atoms": np.ones((2, 160), dtype=np.float64),
        "ess_ablated_atoms": np.ones((2, 160), dtype=np.float64),
        "full_probability_sum_error": np.zeros((2, 3, 160), dtype=np.float64),
        "ablated_probability_sum_error": np.zeros((2, 3, 160), dtype=np.float64),
        "full_probability_minimum": np.full((2, 3, 160), 1e-4, dtype=np.float64),
        "ablated_probability_minimum": np.full((2, 3, 160), 1e-4, dtype=np.float64),
        "js_full": np.zeros((2, 2, 160), dtype=np.float64),
        "js_ablated": np.zeros((2, 2, 160), dtype=np.float64),
        "abs_logp_change_full": np.zeros((2, 2, 160), dtype=np.float64),
        "abs_logp_change_ablated": np.zeros((2, 2, 160), dtype=np.float64),
    }
    if fail_first_candidate and bank_index == 0:
        partial["js_full"][0, 0, 0] = 0.001
    raw_path = run_dir / "calibration_raw.npz"
    write_numeric_npz_atomic(
        raw_path,
        prior_codes=np.array([0, 1], dtype=np.int64),
        candidates=np.array([8192, 16384], dtype=np.int64),
        reference_truncation=np.array([32768], dtype=np.int64),
        **partial,
    )
    for prior_index, prior in enumerate(("C", "N")):
        write_numeric_npz_atomic(
            run_dir / f"partial_{prior}.npz",
            **{name: value[prior_index] for name, value in partial.items()},
        )
    running_path = run_dir / "RUNNING.json"
    write_json_atomic(
        running_path, {"identity": identity_object, "identity_sha256": identity}
    )
    atom_bank = {
        "schema_version": 1,
        "seed": config["atom_seed"],
        "count": config["atom_count"],
        "shape": [config["atom_count"], 4, 4],
        "dtype": "<f8",
        "sha256": f"{bank_index + 11:064x}",
        "determinism_canary": {
            "seed": config["atom_determinism_canary_seed"],
            "count": config["atom_determinism_canary_count"],
            "shape": [config["atom_determinism_canary_count"], 4, 4],
            "dtype": "<f8",
            "sha256": "a" * 64,
        },
    }
    atom_bank_path = run_dir / "ATOM_BANK.json"
    write_json_atomic(atom_bank_path, atom_bank)
    summary_path = run_dir / "calibration_summary.json"
    summary = {
        "stage": "phase1_ordering_cross_bank_qualification",
        "completion_state": "INCOMPLETE_WITHOUT_VERIFIED_COMPLETE_MARKER",
        "attempt_identity_sha256": identity,
        "git": {"commit": "test-qualification-commit", "dirty": False},
        "config_sha256": _sha256_file(config_path),
        "raw_sha256": _sha256_file(raw_path),
        "atom_seed": config["atom_seed"],
        "atom_bank": atom_bank,
        "calibration_stream_seeds": {
            "C": config["calibration_seed_root"],
            "N": config["calibration_seed_root"] + 10_000,
        },
        "candidate_results": [
            {"truncation": 8192, "compared_with": 32768},
            {"truncation": 16384, "compared_with": 32768},
        ],
        "decision": "CALIBRATION_PASS",
    }
    write_json_atomic(summary_path, summary)
    payloads = [
        running_path,
        atom_bank_path,
        raw_path,
        summary_path,
        run_dir / "partial_C.npz",
        run_dir / "partial_N.npz",
    ]
    write_json_atomic(
        run_dir / "COMPLETE.json",
        {
            "identity": identity_object,
            "identity_sha256": identity,
            "decision": summary["decision"],
            "artifacts": {
                path.name: {"sha256": _sha256_file(path), "bytes": path.stat().st_size}
                for path in payloads
            },
        },
    )


def _refresh_artifact_hashes(run_dir: Path) -> None:
    complete_path = run_dir / "COMPLETE.json"
    complete = json.loads(complete_path.read_text())
    for name in complete["artifacts"]:
        path = run_dir / name
        complete["artifacts"][name] = {
            "sha256": _sha256_file(path),
            "bytes": path.stat().st_size,
        }
    write_json_atomic(complete_path, complete)


def test_qualification_join_selects_first_globally_passing_candidate(
    tmp_path, monkeypatch
):
    run_dirs = [tmp_path / f"bank{index}" for index in range(3)]
    for index, run_dir in enumerate(run_dirs):
        _write_shard(run_dir, index, fail_first_candidate=False)
    monkeypatch.setattr(
        qualification,
        "_git_provenance",
        lambda require_clean: {
            "commit": "test-qualification-commit",
            "dirty": False,
            "status": [],
        },
    )
    summary = qualification.join_qualification(run_dirs, tmp_path / "joined")
    assert summary["decision"] == "QUALIFICATION_PASS"
    assert summary["selected_truncation"] == 8192
    assert (tmp_path / "joined" / "COMPLETE.json").is_file()
    assert not (tmp_path / "joined" / "ATTEMPT.lock").exists()


def test_one_tail_exceedance_disqualifies_only_the_affected_candidate(
    tmp_path, monkeypatch
):
    run_dirs = [tmp_path / f"bank{index}" for index in range(3)]
    for index, run_dir in enumerate(run_dirs):
        _write_shard(run_dir, index, fail_first_candidate=True)
    monkeypatch.setattr(
        qualification,
        "_git_provenance",
        lambda require_clean: {
            "commit": "test-qualification-commit",
            "dirty": False,
            "status": [],
        },
    )
    summary = qualification.join_qualification(run_dirs, tmp_path / "joined")
    assert summary["candidate_reports"][0]["pass_all_banks"] is False
    assert summary["candidate_reports"][1]["pass_all_banks"] is True
    assert summary["selected_truncation"] == 16384


def test_shard_without_required_identity_objects_is_rejected(tmp_path):
    run_dir = tmp_path / "bank0"
    _write_shard(run_dir, 0, fail_first_candidate=False)
    complete_path = run_dir / "COMPLETE.json"
    complete = json.loads(complete_path.read_text())
    del complete["identity"]
    write_json_atomic(complete_path, complete)
    running_path = run_dir / "RUNNING.json"
    running = json.loads(running_path.read_text())
    del running["identity"]
    write_json_atomic(running_path, running)
    _refresh_artifact_hashes(run_dir)
    with pytest.raises(RuntimeError, match="identity object missing"):
        qualification._verify_shard(run_dir, 0)


def test_shard_raw_payload_identity_mismatch_is_rejected(tmp_path):
    run_dir = tmp_path / "bank0"
    _write_shard(run_dir, 0, fail_first_candidate=False)
    raw_path = run_dir / "calibration_raw.npz"
    with np.load(raw_path, allow_pickle=False) as archive:
        raw = {name: archive[name].copy() for name in archive.files}
    raw["attempt_identity_sha256"][0, 0] ^= np.uint8(1)
    write_numeric_npz_atomic(raw_path, **raw)
    _refresh_artifact_hashes(run_dir)
    summary_path = run_dir / "calibration_summary.json"
    summary = json.loads(summary_path.read_text())
    summary["raw_sha256"] = _sha256_file(raw_path)
    write_json_atomic(summary_path, summary)
    _refresh_artifact_hashes(run_dir)
    with pytest.raises(RuntimeError, match="raw identity mismatch"):
        qualification._verify_shard(run_dir, 0)


def test_cross_node_atom_canary_disagreement_is_rejected(tmp_path, monkeypatch):
    run_dirs = [tmp_path / f"bank{index}" for index in range(3)]
    for index, run_dir in enumerate(run_dirs):
        _write_shard(run_dir, index, fail_first_candidate=False)
    run_dir = run_dirs[1]
    atom_path = run_dir / "ATOM_BANK.json"
    atom_bank = json.loads(atom_path.read_text())
    atom_bank["determinism_canary"]["sha256"] = "b" * 64
    write_json_atomic(atom_path, atom_bank)
    summary_path = run_dir / "calibration_summary.json"
    summary = json.loads(summary_path.read_text())
    summary["atom_bank"] = atom_bank
    write_json_atomic(summary_path, summary)
    _refresh_artifact_hashes(run_dir)
    monkeypatch.setattr(
        qualification,
        "_git_provenance",
        lambda require_clean: {
            "commit": "test-qualification-commit",
            "dirty": False,
            "status": [],
        },
    )
    with pytest.raises(RuntimeError, match="atom determinism canary"):
        qualification.join_qualification(run_dirs, tmp_path / "joined")


def test_duplicate_full_atom_banks_are_rejected(tmp_path, monkeypatch):
    run_dirs = [tmp_path / f"bank{index}" for index in range(3)]
    for index, run_dir in enumerate(run_dirs):
        _write_shard(run_dir, index, fail_first_candidate=False)
    first_bank = json.loads((run_dirs[0] / "ATOM_BANK.json").read_text())
    run_dir = run_dirs[1]
    atom_path = run_dir / "ATOM_BANK.json"
    atom_bank = json.loads(atom_path.read_text())
    atom_bank["sha256"] = first_bank["sha256"]
    write_json_atomic(atom_path, atom_bank)
    summary_path = run_dir / "calibration_summary.json"
    summary = json.loads(summary_path.read_text())
    summary["atom_bank"] = atom_bank
    write_json_atomic(summary_path, summary)
    _refresh_artifact_hashes(run_dir)
    monkeypatch.setattr(
        qualification,
        "_git_provenance",
        lambda require_clean: {
            "commit": "test-qualification-commit",
            "dirty": False,
            "status": [],
        },
    )
    with pytest.raises(RuntimeError, match="three distinct full atom banks"):
        qualification.join_qualification(run_dirs, tmp_path / "joined")
