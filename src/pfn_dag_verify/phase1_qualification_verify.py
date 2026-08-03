"""Independent verifier for the frozen Phase-1 oracle qualification artifacts.

This module deliberately does not import the qualification runner or joiner.
It recomputes the scientific gate from sealed raw arrays and verifies executable
source against Git blobs from the recorded commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

import numpy as np


COMMIT = "cdd541c2ac7038b5cb8c7c6d3f1f6ac1811e4b88"
CANDIDATES = (8192, 16384)
REFERENCE = 32768
PRIORS = ("C", "N")
PREDICTORS = ("full", "ablated")
EXPECTED_SHARD_ARTIFACTS = {
    "ATOM_BANK.json",
    "RUNNING.json",
    "calibration_raw.npz",
    "calibration_summary.json",
    "partial_C.npz",
    "partial_N.npz",
}
EXPECTED_RAW = {
    "prior_codes": ((2,), np.dtype(np.int64)),
    "candidates": ((2,), np.dtype(np.int64)),
    "reference_truncation": ((1,), np.dtype(np.int64)),
    "attempt_identity_sha256": ((2, 32), np.dtype(np.uint8)),
    "completed": ((2, 160), np.dtype(np.int8)),
    "keep_full": ((2, 3, 160), np.dtype(np.float64)),
    "keep_ablated": ((2, 3, 160), np.dtype(np.float64)),
    "ess_full_atoms": ((2, 160), np.dtype(np.float64)),
    "ess_ablated_atoms": ((2, 160), np.dtype(np.float64)),
    "full_probability_sum_error": ((2, 3, 160), np.dtype(np.float64)),
    "ablated_probability_sum_error": ((2, 3, 160), np.dtype(np.float64)),
    "full_probability_minimum": ((2, 3, 160), np.dtype(np.float64)),
    "ablated_probability_minimum": ((2, 3, 160), np.dtype(np.float64)),
    "js_full": ((2, 2, 160), np.dtype(np.float64)),
    "js_ablated": ((2, 2, 160), np.dtype(np.float64)),
    "abs_logp_change_full": ((2, 2, 160), np.dtype(np.float64)),
    "abs_logp_change_ablated": ((2, 2, 160), np.dtype(np.float64)),
}
THRESHOLDS = {
    "median_js": 9e-5,
    "p95_js": 9e-4,
    "median_abs_logp_change": 0.0018,
    "p95_abs_logp_change": 0.009,
}
BASE_THRESHOLDS = {
    "median_js": 1e-4,
    "p95_js": 1e-3,
    "median_abs_logp_change": 0.002,
    "p95_abs_logp_change": 0.01,
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return _sha256_bytes(payload.encode())


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _git_blob(repo: Path, commit: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def _relative_source_path(absolute: str) -> str:
    marker = "/source/"
    if marker not in absolute:
        raise RuntimeError(f"source inventory path lacks checkout root: {absolute}")
    relative = absolute.split(marker, 1)[1]
    if not relative or relative.startswith("/") or ".." in Path(relative).parts:
        raise RuntimeError(f"unsafe source inventory path: {absolute}")
    return relative


def _verify_source_inventory(
    inventory: dict[str, Any], repo: Path, commit: str
) -> None:
    if not isinstance(inventory, dict) or not inventory:
        raise RuntimeError("missing source inventory")
    for absolute, expected in inventory.items():
        relative = _relative_source_path(str(absolute))
        observed = _sha256_bytes(_git_blob(repo, commit, relative))
        if observed != expected:
            raise RuntimeError(f"source inventory mismatch: {relative}")


def _verify_artifact_inventory(
    directory: Path, complete: dict[str, Any], expected_names: set[str]
) -> None:
    artifacts = complete.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != expected_names:
        raise RuntimeError(f"artifact inventory mismatch: {directory}")
    for name, record in artifacts.items():
        path = directory / name
        if not path.is_file():
            raise RuntimeError(f"missing artifact: {path}")
        if path.stat().st_size != int(record["bytes"]):
            raise RuntimeError(f"artifact size mismatch: {path}")
        if _sha256_file(path) != record["sha256"]:
            raise RuntimeError(f"artifact hash mismatch: {path}")


def _load_raw(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != set(EXPECTED_RAW):
            raise RuntimeError(f"raw inventory mismatch: {path}")
        raw = {name: archive[name].copy() for name in archive.files}
    for name, (shape, dtype) in EXPECTED_RAW.items():
        if raw[name].shape != shape or raw[name].dtype != dtype:
            raise RuntimeError(f"raw shape/dtype mismatch: {path}:{name}")
    return raw


def _metric_row(js: np.ndarray, logp: np.ndarray) -> dict[str, Any]:
    row = {
        "median_js": float(np.median(js)),
        "p95_js": float(np.quantile(js, 0.95)),
        "median_abs_logp_change": float(np.median(logp)),
        "p95_abs_logp_change": float(np.quantile(logp, 0.95)),
    }
    row["pass"] = bool(all(row[name] <= limit for name, limit in THRESHOLDS.items()))
    row["borderline"] = bool(
        any(
            THRESHOLDS[name] < row[name] <= 1.1 * BASE_THRESHOLDS[name]
            for name in THRESHOLDS
        )
    )
    return row


def _verify_shard(
    run_dir: Path, bank: int, repo: Path, commit: str
) -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, Any]]:
    complete = _load_json(run_dir / "COMPLETE.json")
    _verify_artifact_inventory(run_dir, complete, EXPECTED_SHARD_ARTIFACTS)
    running = _load_json(run_dir / "RUNNING.json")
    summary = _load_json(run_dir / "calibration_summary.json")
    identity = complete.get("identity")
    if not isinstance(identity, dict) or running.get("identity") != identity:
        raise RuntimeError(f"identity object mismatch: bank {bank}")
    digest = _sha256_json(identity)
    if (
        complete.get("identity_sha256") != digest
        or running.get("identity_sha256") != digest
        or summary.get("attempt_identity_sha256") != digest
    ):
        raise RuntimeError(f"identity digest mismatch: bank {bank}")
    if identity.get("git_commit") != commit:
        raise RuntimeError(f"identity commit mismatch: bank {bank}")
    _verify_source_inventory(identity.get("source_inventory"), repo, commit)
    if summary.get("git") != {"commit": commit, "dirty": False, "status": []}:
        raise RuntimeError(f"summary Git provenance mismatch: bank {bank}")
    if summary.get("stage") != "phase1_ordering_cross_bank_qualification":
        raise RuntimeError(f"stage mismatch: bank {bank}")
    if summary.get("scientific_endpoints_computed") is not False:
        raise RuntimeError(f"scientific endpoint barrier violated: bank {bank}")
    if summary.get("completion_state") != "INCOMPLETE_WITHOUT_VERIFIED_COMPLETE_MARKER":
        raise RuntimeError(f"completion-state mismatch: bank {bank}")
    if complete.get("decision") != summary.get("decision"):
        raise RuntimeError(f"decision marker mismatch: bank {bank}")

    config_relative = f"config/phase1_ordering_qualification_bank{bank}.json"
    config_blob = _git_blob(repo, commit, config_relative)
    config = json.loads(config_blob)
    if summary.get("config_sha256") != _sha256_bytes(config_blob):
        raise RuntimeError(f"config hash mismatch: bank {bank}")
    expected_config = {
        "qualification_bank_index": bank,
        "calibration_contexts_per_prior": 160,
        "calibration_seed_root": 880_903_000 + bank,
        "atom_count": 3_000_000,
        "atom_seed": 881_003_101 + bank,
        "atom_determinism_canary_seed": 881_103_999,
        "atom_determinism_canary_count": 4096,
        "truncation_candidates": list(CANDIDATES),
        "reference_truncation": REFERENCE,
    }
    if any(config.get(name) != value for name, value in expected_config.items()):
        raise RuntimeError(f"frozen config field mismatch: bank {bank}")
    limits = config.get("qualification_zero_exceedance")
    if limits != {
        "familywise_alpha": 0.05,
        "families": 48,
        "contexts_per_family": 160,
        "js_strict_p95_max": 0.0009,
        "abs_logp_change_strict_p95_max": 0.009,
        "bonferroni_clopper_pearson_upper": 0.04201037701571053,
    }:
        raise RuntimeError(f"qualification limits mismatch: bank {bank}")

    raw_path = run_dir / "calibration_raw.npz"
    if summary.get("raw_sha256") != _sha256_file(raw_path):
        raise RuntimeError(f"raw summary hash mismatch: bank {bank}")
    raw = _load_raw(raw_path)
    if raw["prior_codes"].tolist() != [0, 1]:
        raise RuntimeError(f"prior codes mismatch: bank {bank}")
    if raw["candidates"].tolist() != list(CANDIDATES):
        raise RuntimeError(f"candidates mismatch: bank {bank}")
    if raw["reference_truncation"].tolist() != [REFERENCE]:
        raise RuntimeError(f"reference mismatch: bank {bank}")
    if not np.all(raw["completed"] == 1):
        raise RuntimeError(f"incomplete raw contexts: bank {bank}")
    identity_bytes = np.frombuffer(bytes.fromhex(digest), dtype=np.uint8)
    if not np.all(raw["attempt_identity_sha256"] == identity_bytes[None, :]):
        raise RuntimeError(f"raw identity mismatch: bank {bank}")
    numeric = [name for name in raw if name != "attempt_identity_sha256"]
    if not all(np.isfinite(raw[name]).all() for name in numeric):
        raise RuntimeError(f"non-finite raw diagnostics: bank {bank}")
    if max(
        float(raw["full_probability_sum_error"].max()),
        float(raw["ablated_probability_sum_error"].max()),
    ) > 1e-8:
        raise RuntimeError(f"normalization failure: bank {bank}")
    if min(
        float(raw["full_probability_minimum"].min()),
        float(raw["ablated_probability_minimum"].min()),
    ) < 0.0:
        raise RuntimeError(f"negative probability: bank {bank}")

    partial_names = set(raw) - {"prior_codes", "candidates", "reference_truncation"}
    for prior_index, prior in enumerate(PRIORS):
        with np.load(run_dir / f"partial_{prior}.npz", allow_pickle=False) as partial:
            if set(partial.files) != partial_names:
                raise RuntimeError(f"partial inventory mismatch: bank {bank} {prior}")
            for name in partial.files:
                if not np.array_equal(partial[name], raw[name][prior_index]):
                    raise RuntimeError(f"partial/raw mismatch: bank {bank} {prior} {name}")

    atom_bank = _load_json(run_dir / "ATOM_BANK.json")
    if atom_bank != summary.get("atom_bank"):
        raise RuntimeError(f"atom marker/summary mismatch: bank {bank}")
    if (
        atom_bank.get("seed") != 881_003_101 + bank
        or atom_bank.get("count") != 3_000_000
        or atom_bank.get("shape") != [3_000_000, 4, 4]
        or atom_bank.get("dtype") != np.dtype(np.float64).str
    ):
        raise RuntimeError(f"atom metadata mismatch: bank {bank}")
    canary = atom_bank.get("determinism_canary", {})
    if (
        canary.get("seed") != 881_103_999
        or canary.get("count") != 4096
        or canary.get("shape") != [4096, 4, 4]
        or canary.get("dtype") != np.dtype(np.float64).str
    ):
        raise RuntimeError(f"canary metadata mismatch: bank {bank}")
    for label, value in (("atom", atom_bank.get("sha256")), ("canary", canary.get("sha256"))):
        if not isinstance(value, str) or len(value) != 64:
            raise RuntimeError(f"invalid {label} hash: bank {bank}")
        bytes.fromhex(value)
    return summary, raw, config


def verify_qualification(root: Path, repo: Path, commit: str = COMMIT) -> dict[str, Any]:
    root = root.resolve()
    repo = repo.resolve()
    verified = [
        _verify_shard(root / f"bank{bank}" / "run", bank, repo, commit)
        for bank in range(3)
    ]
    atom_hashes = [summary["atom_bank"]["sha256"] for summary, _, _ in verified]
    canary_hashes = {
        summary["atom_bank"]["determinism_canary"]["sha256"]
        for summary, _, _ in verified
    }
    if len(set(atom_hashes)) != 3 or len(canary_hashes) != 1:
        raise RuntimeError("atom-bank distinctness or determinism canary failed")

    reports: list[dict[str, Any]] = []
    selected: int | None = None
    for candidate_index, candidate in enumerate(CANDIDATES):
        candidate_pass = True
        bank_reports: list[dict[str, Any]] = []
        for bank, (_, raw, _) in enumerate(verified):
            prior_reports: dict[str, Any] = {}
            for prior_index, prior in enumerate(PRIORS):
                predictor_reports: dict[str, Any] = {}
                for predictor in PREDICTORS:
                    js = raw[f"js_{predictor}"][prior_index, candidate_index]
                    logp = raw[f"abs_logp_change_{predictor}"][prior_index, candidate_index]
                    aggregate = _metric_row(js, logp)
                    js_exceedances = int(np.count_nonzero(js > 0.0009))
                    logp_exceedances = int(np.count_nonzero(logp > 0.009))
                    passed = bool(
                        aggregate["pass"] and js_exceedances == 0 and logp_exceedances == 0
                    )
                    candidate_pass = candidate_pass and passed
                    predictor_reports[predictor] = {
                        "aggregate": aggregate,
                        "js_exceedances": js_exceedances,
                        "abs_logp_change_exceedances": logp_exceedances,
                        "pass": passed,
                    }
                prior_reports[prior] = predictor_reports
            bank_reports.append({"bank_index": bank, "priors": prior_reports})
        reports.append(
            {
                "candidate": candidate,
                "compared_with": REFERENCE,
                "banks": bank_reports,
                "pass_all_banks": candidate_pass,
            }
        )
        if selected is None and candidate_pass:
            selected = candidate

    joined = root / "joined"
    joined_complete = _load_json(joined / "COMPLETE.json")
    _verify_artifact_inventory(
        joined,
        joined_complete,
        {"qualification_raw.npz", "qualification_summary.json"},
    )
    joined_summary = _load_json(joined / "qualification_summary.json")
    identity = joined_complete.get("identity")
    if not isinstance(identity, dict) or joined_summary.get("identity") != identity:
        raise RuntimeError("joined identity object mismatch")
    digest = _sha256_json(identity)
    if (
        joined_complete.get("identity_sha256") != digest
        or joined_summary.get("identity_sha256") != digest
    ):
        raise RuntimeError("joined identity digest mismatch")
    if identity.get("git_commit") != commit or joined_summary.get("git", {}).get("commit") != commit:
        raise RuntimeError("joined commit mismatch")
    _verify_source_inventory(identity.get("source_inventory"), repo, commit)
    for bank in range(3):
        suffix = f"/bank{bank}/run"
        entries = [
            (path, value)
            for path, value in identity.get("run_marker_hashes", {}).items()
            if path.endswith(suffix)
        ]
        if len(entries) != 1:
            raise RuntimeError(f"joined run-marker identity mismatch: bank {bank}")
        if entries[0][1] != _sha256_file(root / f"bank{bank}" / "run" / "COMPLETE.json"):
            raise RuntimeError(f"joined run-marker hash mismatch: bank {bank}")
    if identity.get("atom_bank_sha256") != atom_hashes:
        raise RuntimeError("joined atom-bank hashes mismatch")
    if identity.get("atom_determinism_canary_sha256") != next(iter(canary_hashes)):
        raise RuntimeError("joined canary hash mismatch")
    expected_decision = "QUALIFICATION_PASS" if selected is not None else "QUALIFICATION_FAIL"
    if (
        joined_summary.get("decision") != expected_decision
        or joined_complete.get("decision") != expected_decision
        or joined_summary.get("selected_truncation") != selected
        or joined_summary.get("candidate_reports") != reports
    ):
        raise RuntimeError("joined scientific decision does not reproduce")
    cp_upper = 1.0 - (0.05 / 48.0) ** (1.0 / 160.0)
    if not math.isclose(
        joined_summary.get("zero_exceedance_clopper_pearson_upper"),
        cp_upper,
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise RuntimeError("joined Clopper-Pearson value mismatch")
    with np.load(joined / "qualification_raw.npz", allow_pickle=False) as archive:
        expected_joined_names = {
            "bank_indices",
            "candidates",
            "js_full",
            "js_ablated",
            "abs_logp_change_full",
            "abs_logp_change_ablated",
        }
        if set(archive.files) != expected_joined_names:
            raise RuntimeError("joined raw inventory mismatch")
        if archive["bank_indices"].tolist() != [0, 1, 2]:
            raise RuntimeError("joined bank indices mismatch")
        if archive["candidates"].tolist() != list(CANDIDATES):
            raise RuntimeError("joined candidates mismatch")
        for name in expected_joined_names - {"bank_indices", "candidates"}:
            expected = np.stack([raw[name] for _, raw, _ in verified])
            if not np.array_equal(archive[name], expected):
                raise RuntimeError(f"joined raw stack mismatch: {name}")

    worst: dict[str, Any] = {}
    for candidate_index, candidate in enumerate(CANDIDATES):
        cells = [
            cell
            for bank in reports[candidate_index]["banks"]
            for prior in bank["priors"].values()
            for cell in prior.values()
        ]
        worst[str(candidate)] = {
            "total_js_exceedances": sum(cell["js_exceedances"] for cell in cells),
            "total_abs_logp_change_exceedances": sum(
                cell["abs_logp_change_exceedances"] for cell in cells
            ),
            "worst_p95_js": max(cell["aggregate"]["p95_js"] for cell in cells),
            "worst_p95_abs_logp_change": max(
                cell["aggregate"]["p95_abs_logp_change"] for cell in cells
            ),
        }
    return {
        "schema_version": 1,
        "verification": "INDEPENDENT_RAW_RECOMPUTATION_PASS",
        "verifier_source_sha256": _sha256_file(Path(__file__).resolve()),
        "verifier_runtime": {
            "python_executable": sys.executable,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "source_commit": commit,
        "decision": expected_decision,
        "selected_truncation": selected,
        "reference_truncation": REFERENCE,
        "bank_atom_sha256": atom_hashes,
        "determinism_canary_sha256": next(iter(canary_hashes)),
        "zero_exceedance_clopper_pearson_upper": cp_upper,
        "candidate_summary": worst,
        "joined_complete_sha256": _sha256_file(joined / "COMPLETE.json"),
        "joined_raw_sha256": _sha256_file(joined / "qualification_raw.npz"),
        "joined_summary_sha256": _sha256_file(joined / "qualification_summary.json"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--commit", default=COMMIT)
    arguments = parser.parse_args(argv)
    result = verify_qualification(arguments.root, arguments.repo, arguments.commit)
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = arguments.out.with_suffix(arguments.out.suffix + ".tmp")
    temporary.write_text(payload)
    temporary.replace(arguments.out)
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
