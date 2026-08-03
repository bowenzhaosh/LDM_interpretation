"""Hash-gated join for Phase-1 cross-bank oracle qualification shards."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from .phase1_ordering import (
    _acquire_attempt_lease,
    _git_provenance,
    _load_json,
    _predictor_convergence_row,
    _sha256_file,
    _sha256_json,
    production_qualification_protocol,
)
from .storage import write_json_atomic, write_numeric_npz_atomic


EXPECTED_ARTIFACTS = {
    "ATOM_BANK.json",
    "RUNNING.json",
    "calibration_raw.npz",
    "calibration_summary.json",
    "partial_C.npz",
    "partial_N.npz",
}

FORBIDDEN_RAW_ARRAYS = {
    "contexts",
    "queries",
    "outcomes",
    "outcome_bins",
    "true_orderings",
    "full_probability",
    "ablated_probability",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise RuntimeError(f"invalid SHA-256 for {label}")
    try:
        bytes.fromhex(value)
    except ValueError as error:
        raise RuntimeError(f"invalid SHA-256 for {label}") from error
    return value


def _verify_marker(
    run_dir: Path,
) -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, Any], str]:
    if (run_dir / "ATTEMPT.lock").exists() or (run_dir / "RECOVERY.lock").exists():
        raise RuntimeError(f"qualification shard still has a live lock: {run_dir}")
    complete = _load_json(run_dir / "COMPLETE.json")
    artifacts = complete.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != EXPECTED_ARTIFACTS:
        raise RuntimeError(f"qualification artifact inventory mismatch: {run_dir}")
    for name, metadata in artifacts.items():
        path = run_dir / name
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != int(metadata["bytes"]):
            raise RuntimeError(f"qualification artifact size mismatch: {path}")
        if _sha256_file(path) != str(metadata["sha256"]):
            raise RuntimeError(f"qualification artifact hash mismatch: {path}")
    summary = _load_json(run_dir / "calibration_summary.json")
    running = _load_json(run_dir / "RUNNING.json")
    complete_identity = complete.get("identity")
    running_identity = running.get("identity")
    if not isinstance(complete_identity, dict) or not isinstance(running_identity, dict):
        raise RuntimeError(f"qualification attempt identity object missing: {run_dir}")
    if complete_identity != running_identity:
        raise RuntimeError(f"qualification attempt identity object mismatch: {run_dir}")
    identity_sha256 = _sha256_json(complete_identity)
    if (
        complete.get("identity_sha256") != identity_sha256
        or running.get("identity_sha256") != identity_sha256
        or summary.get("attempt_identity_sha256") != identity_sha256
    ):
        raise RuntimeError(f"qualification attempt identity mismatch: {run_dir}")
    if summary.get("stage") != "phase1_ordering_cross_bank_qualification":
        raise RuntimeError(f"wrong qualification stage: {run_dir}")
    if summary.get("completion_state") != "INCOMPLETE_WITHOUT_VERIFIED_COMPLETE_MARKER":
        raise RuntimeError(f"unsafe qualification completion state: {run_dir}")
    if summary.get("git", {}).get("dirty") is not False:
        raise RuntimeError(f"dirty qualification source: {run_dir}")
    if complete.get("decision") != summary.get("decision"):
        raise RuntimeError(f"qualification marker decision mismatch: {run_dir}")
    atom_bank = _load_json(run_dir / "ATOM_BANK.json")
    if summary.get("atom_bank") != atom_bank:
        raise RuntimeError(f"qualification atom-bank record mismatch: {run_dir}")
    with np.load(run_dir / "calibration_raw.npz", allow_pickle=False) as archive:
        if FORBIDDEN_RAW_ARRAYS & set(archive.files):
            raise RuntimeError(f"qualification leaked forbidden arrays: {run_dir}")
        raw = {name: archive[name].copy() for name in archive.files}
    return summary, raw, complete_identity, identity_sha256


def _verify_shard(
    run_dir: Path, bank_index: int
) -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, Any]]:
    config_path = _repo_root() / "config" / f"phase1_ordering_qualification_bank{bank_index}.json"
    config = _load_json(config_path)
    if config != production_qualification_protocol(bank_index):
        raise RuntimeError(f"registered qualification config drift: bank {bank_index}")
    summary, raw, identity, identity_sha256 = _verify_marker(run_dir)
    if summary.get("config_sha256") != _sha256_file(config_path):
        raise RuntimeError(f"qualification config hash mismatch: bank {bank_index}")
    if summary.get("raw_sha256") != _sha256_file(run_dir / "calibration_raw.npz"):
        raise RuntimeError(f"qualification raw hash mismatch: bank {bank_index}")
    expected_shapes = {
        "completed": (2, 160),
        "js_full": (2, 2, 160),
        "js_ablated": (2, 2, 160),
        "abs_logp_change_full": (2, 2, 160),
        "abs_logp_change_ablated": (2, 2, 160),
        "attempt_identity_sha256": (2, 32),
    }
    for name, shape in expected_shapes.items():
        if name not in raw or raw[name].shape != shape:
            raise RuntimeError(f"qualification raw shape mismatch for {name}: bank {bank_index}")
    expected_identity_bytes = np.frombuffer(
        bytes.fromhex(identity_sha256), dtype=np.uint8
    )
    if not np.all(raw["attempt_identity_sha256"] == expected_identity_bytes[None, :]):
        raise RuntimeError(f"qualification raw identity mismatch: bank {bank_index}")
    if not np.all(raw["completed"] == 1):
        raise RuntimeError(f"incomplete qualification contexts: bank {bank_index}")
    if raw["candidates"].tolist() != [8192, 16384]:
        raise RuntimeError(f"qualification candidate mismatch: bank {bank_index}")
    if raw["reference_truncation"].tolist() != [32768]:
        raise RuntimeError(f"qualification reference mismatch: bank {bank_index}")
    if [row.get("compared_with") for row in summary["candidate_results"]] != [32768, 32768]:
        raise RuntimeError(f"qualification did not compare directly to reference: bank {bank_index}")
    numeric_names = [name for name in raw if name != "attempt_identity_sha256"]
    if not all(np.isfinite(raw[name]).all() for name in numeric_names):
        raise RuntimeError(f"non-finite qualification diagnostics: bank {bank_index}")
    if max(
        float(raw["full_probability_sum_error"].max()),
        float(raw["ablated_probability_sum_error"].max()),
    ) > float(config["thresholds"]["probability_sum_atol"]):
        raise RuntimeError(f"qualification normalization failure: bank {bank_index}")
    if min(
        float(raw["full_probability_minimum"].min()),
        float(raw["ablated_probability_minimum"].min()),
    ) < 0.0:
        raise RuntimeError(f"negative qualification probability: bank {bank_index}")
    if int(summary["atom_seed"]) != int(config["atom_seed"]):
        raise RuntimeError(f"qualification atom-seed mismatch: bank {bank_index}")
    if summary["calibration_stream_seeds"] != {
        "C": int(config["calibration_seed_root"]),
        "N": int(config["calibration_seed_root"]) + 10_000,
    }:
        raise RuntimeError(f"qualification context-seed mismatch: bank {bank_index}")
    if identity.get("config_sha256") != _sha256_file(config_path):
        raise RuntimeError(f"qualification identity/config mismatch: bank {bank_index}")
    if identity.get("fleet_sha256") != str(config["fleet_sha256"]):
        raise RuntimeError(f"qualification identity/fleet mismatch: bank {bank_index}")
    if identity.get("git_commit") != summary["git"]["commit"]:
        raise RuntimeError(f"qualification identity/commit mismatch: bank {bank_index}")
    atom_bank = summary["atom_bank"]
    expected_bank = {
        "seed": int(config["atom_seed"]),
        "count": int(config["atom_count"]),
        "shape": [int(config["atom_count"]), 4, 4],
        "dtype": np.dtype(np.float64).str,
    }
    if any(atom_bank.get(name) != value for name, value in expected_bank.items()):
        raise RuntimeError(f"qualification atom-bank metadata mismatch: bank {bank_index}")
    _require_sha256(atom_bank.get("sha256"), f"bank {bank_index} atom bank")
    canary = atom_bank.get("determinism_canary")
    expected_canary = {
        "seed": int(config["atom_determinism_canary_seed"]),
        "count": int(config["atom_determinism_canary_count"]),
        "shape": [int(config["atom_determinism_canary_count"]), 4, 4],
        "dtype": np.dtype(np.float64).str,
    }
    if not isinstance(canary, dict) or any(
        canary.get(name) != value for name, value in expected_canary.items()
    ):
        raise RuntimeError(f"qualification atom-canary metadata mismatch: bank {bank_index}")
    _require_sha256(canary.get("sha256"), f"bank {bank_index} atom canary")
    partial_names = set(raw) - {"prior_codes", "candidates", "reference_truncation"}
    for prior_index, prior in enumerate(("C", "N")):
        with np.load(run_dir / f"partial_{prior}.npz", allow_pickle=False) as partial:
            if set(partial.files) != partial_names:
                raise RuntimeError(
                    f"qualification partial inventory mismatch: bank {bank_index} {prior}"
                )
            for name in partial.files:
                if not np.array_equal(partial[name], raw[name][prior_index], equal_nan=True):
                    raise RuntimeError(
                        f"qualification partial/raw mismatch: bank {bank_index} {prior} {name}"
                    )
    return summary, raw, config


def join_qualification(run_dirs: list[Path], output_dir: Path) -> dict[str, Any]:
    if len(run_dirs) != 3:
        raise ValueError("qualification join requires exactly three bank run directories")
    resolved = [path.resolve() for path in run_dirs]
    if len(set(resolved)) != 3:
        raise ValueError("qualification run directories must be unique")
    verified = [_verify_shard(path, index) for index, path in enumerate(resolved)]
    commits = {summary["git"]["commit"] for summary, _, _ in verified}
    if len(commits) != 1:
        raise RuntimeError("qualification shards used different source commits")
    canary_hashes = {
        summary["atom_bank"]["determinism_canary"]["sha256"]
        for summary, _, _ in verified
    }
    if len(canary_hashes) != 1:
        raise RuntimeError("qualification shards disagree on the atom determinism canary")
    atom_bank_hashes = [
        summary["atom_bank"]["sha256"] for summary, _, _ in verified
    ]
    if len(set(atom_bank_hashes)) != 3:
        raise RuntimeError("qualification requires three distinct full atom banks")

    source_paths = [
        Path(__file__).resolve(),
        Path(__file__).with_name("phase1_ordering.py").resolve(),
        Path(__file__).with_name("storage.py").resolve(),
        (_repo_root() / "PHASE1_ORDERING_PREREG.md").resolve(),
    ] + [
        (_repo_root() / "config" / f"phase1_ordering_qualification_bank{index}.json").resolve()
        for index in range(3)
    ]
    source_inventory = {str(path): _sha256_file(path) for path in source_paths}
    run_marker_hashes = {
        str(path): _sha256_file(path / "COMPLETE.json") for path in resolved
    }
    git = _git_provenance(True)
    if git["commit"] not in commits:
        raise RuntimeError("qualification join source differs from shard source")
    identity = {
        "git_commit": git["commit"],
        "source_inventory": source_inventory,
        "run_marker_hashes": run_marker_hashes,
        "atom_bank_sha256": atom_bank_hashes,
        "atom_determinism_canary_sha256": next(iter(canary_hashes)),
    }
    identity_sha256 = _sha256_json(identity)
    output_dir = output_dir.resolve()
    complete_path = output_dir / "COMPLETE.json"
    if complete_path.exists():
        raise FileExistsError(f"completed qualification join already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    lease_path = output_dir / "ATTEMPT.lock"
    _acquire_attempt_lease(lease_path, identity_sha256, False)
    if any(path != lease_path for path in output_dir.iterdir()):
        raise FileExistsError(f"nonempty qualification join directory: {output_dir}")

    reports: list[dict[str, Any]] = []
    selected: int | None = None
    for candidate_index, candidate in enumerate((8192, 16384)):
        candidate_pass = True
        bank_reports: list[dict[str, Any]] = []
        for bank_index, (_, raw, config) in enumerate(verified):
            prior_reports: dict[str, Any] = {}
            limits = config["qualification_zero_exceedance"]
            for prior_index, prior in enumerate(("C", "N")):
                predictor_reports: dict[str, Any] = {}
                for predictor in ("full", "ablated"):
                    js = raw[f"js_{predictor}"][prior_index, candidate_index]
                    logp = raw[f"abs_logp_change_{predictor}"][prior_index, candidate_index]
                    selected_aggregate = _predictor_convergence_row(
                        js, logp, config["thresholds"]
                    )
                    aggregate_pass = bool(selected_aggregate["pass"])
                    js_exceedances = int(
                        np.count_nonzero(js > float(limits["js_strict_p95_max"]))
                    )
                    logp_exceedances = int(
                        np.count_nonzero(
                            logp > float(limits["abs_logp_change_strict_p95_max"])
                        )
                    )
                    passed = aggregate_pass and js_exceedances == 0 and logp_exceedances == 0
                    candidate_pass = candidate_pass and passed
                    predictor_reports[predictor] = {
                        "aggregate": selected_aggregate,
                        "js_exceedances": js_exceedances,
                        "abs_logp_change_exceedances": logp_exceedances,
                        "pass": passed,
                    }
                prior_reports[prior] = predictor_reports
            bank_reports.append({"bank_index": bank_index, "priors": prior_reports})
        reports.append(
            {
                "candidate": candidate,
                "compared_with": 32768,
                "banks": bank_reports,
                "pass_all_banks": candidate_pass,
            }
        )
        if selected is None and candidate_pass:
            selected = candidate

    raw_path = output_dir / "qualification_raw.npz"
    write_numeric_npz_atomic(
        raw_path,
        bank_indices=np.arange(3, dtype=np.int64),
        candidates=np.array([8192, 16384], dtype=np.int64),
        js_full=np.stack([raw["js_full"] for _, raw, _ in verified]),
        js_ablated=np.stack([raw["js_ablated"] for _, raw, _ in verified]),
        abs_logp_change_full=np.stack(
            [raw["abs_logp_change_full"] for _, raw, _ in verified]
        ),
        abs_logp_change_ablated=np.stack(
            [raw["abs_logp_change_ablated"] for _, raw, _ in verified]
        ),
    )
    cp_upper = 1.0 - (0.05 / 48.0) ** (1.0 / 160.0)
    if not math.isclose(cp_upper, 0.04201037701571053, rel_tol=0.0, abs_tol=1e-15):
        raise RuntimeError("qualification Clopper-Pearson constant drift")
    summary = {
        "schema_version": 1,
        "stage": "phase1_ordering_cross_bank_qualification_join",
        "completion_state": "INCOMPLETE_WITHOUT_VERIFIED_COMPLETE_MARKER",
        "decision": "QUALIFICATION_PASS" if selected is not None else "QUALIFICATION_FAIL",
        "selected_truncation": selected,
        "candidate_reports": reports,
        "familywise_alpha": 0.05,
        "families": 48,
        "contexts_per_family": 160,
        "zero_exceedance_clopper_pearson_upper": cp_upper,
        "identity": identity,
        "identity_sha256": identity_sha256,
        "git": git,
        "raw_name": raw_path.name,
        "raw_sha256": _sha256_file(raw_path),
    }
    summary_path = output_dir / "qualification_summary.json"
    write_json_atomic(summary_path, summary)
    complete = {
        "identity": identity,
        "identity_sha256": identity_sha256,
        "decision": summary["decision"],
        "artifacts": {
            path.name: {"sha256": _sha256_file(path), "bytes": path.stat().st_size}
            for path in (raw_path, summary_path)
        },
    }
    write_json_atomic(complete_path, complete)
    lease_path.unlink()
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    summary = join_qualification(arguments.run, arguments.out)
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
