import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

from .registry import sha256_file
from .query_bank import FIXED_SENSITIVITY_BANK


REQUIRED_VALIDATIONS = {
    "artifacts/validation/instrument_primary.json",
    "artifacts/validation/instrument_sensitivity.json",
    "artifacts/validation/legacy_oracle_primary.json",
    "artifacts/validation/legacy_oracle_sensitivity.json",
    "artifacts/validation/bootstrap_coverage.json",
    "artifacts/validation/smoke_budget.json",
}


def expected_run_lock_files(root: Path | None = None) -> set[str]:
    root = repository_root() if root is None else Path(root).resolve()
    fixed = {
        "PREREG.md",
        "HARNESS.md",
        "AUDIT.md",
        "README.md",
        "SOURCE_ORIGIN.md",
        "pyproject.toml",
        "config/query_bank.json",
        "config/checkpoint_registry.json",
        "environment/requirements-lock.txt",
        "environment/runtime.json",
        "environment/installed-distributions.json",
        *REQUIRED_VALIDATIONS,
    }
    runtime_code = {
        path.relative_to(root).as_posix()
        for parent in (root / "src", root / "tests")
        for path in parent.rglob("*.py")
    }
    return fixed | runtime_code

EVALUATION_DOMAIN = "pfn-dag-essential-evaluation-v2"
WALL_CAP_SECONDS = 45 * 60
MEMORY_CAP_BYTES = 16 * 2**30
RAW_CAP_BYTES = 2 * 2**30


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def evaluation_root(commit_sha: str) -> int:
    """Return the preregistered unsigned 64-bit evaluation root."""
    if len(commit_sha) < 7:
        raise ValueError("commit_sha is required")
    payload = (commit_sha + EVALUATION_DOMAIN).encode("ascii")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)


def derive_seed(commit_sha: str, label: str) -> int:
    """Derive a labeled unsigned 64-bit child from the locked root."""
    if not label:
        raise ValueError("seed label is required")
    root = evaluation_root(commit_sha).to_bytes(8, "big", signed=False)
    payload = root + label.encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)


def clean_head(repo: str | Path) -> str:
    repo = Path(repo)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if dirty:
        raise RuntimeError("scientific evaluation requires a clean committed worktree")
    return head


def load_run_lock(repo: str | Path | None = None) -> tuple[Path, dict]:
    root = repository_root() if repo is None else Path(repo).resolve()
    path = root / "config" / "run_lock.json"
    if not path.is_file():
        raise FileNotFoundError("scientific run lock is missing")
    lock = json.loads(path.read_text())
    if lock.get("schema_version") != 1:
        raise ValueError("unsupported run-lock schema")
    return path, lock


def load_locked_query_banks(repo: str | Path | None = None) -> np.ndarray:
    root = repository_root() if repo is None else Path(repo).resolve()
    path = root / "config" / "query_bank.json"
    value = json.loads(path.read_text())
    required = {
        "schema_version": 1,
        "seed": 820001,
        "n_contexts": 512,
        "quadrature": 15,
        "oracle_grid_size": 3097,
    }
    for key, expected in required.items():
        if value.get(key) != expected:
            raise ValueError(f"locked query-bank metadata mismatch: {key}")
    primary = np.asarray(value.get("selected_queries"), dtype=np.float64)
    candidate = np.asarray(value.get("candidate_queries"), dtype=np.float64)
    trace = np.asarray(value.get("objective_trace"), dtype=np.float64)
    if primary.shape != (8,) or candidate.shape != (17,) or trace.shape != (4,):
        raise ValueError("locked query-bank arrays have the wrong shape")
    if not np.isfinite(primary).all() or not np.isfinite(candidate).all() or not np.isfinite(trace).all():
        raise ValueError("locked query-bank metadata is non-finite")
    if not np.all(np.diff(trace) > 0):
        raise ValueError("locked query-bank objective trace is not strictly increasing")
    if value.get("identifiable_fraction") != 511 / 512:
        raise ValueError("locked query-bank calibration fraction mismatch")
    context_hash = value.get("context_sha256", "")
    if len(context_hash) != 64 or any(character not in "0123456789abcdef" for character in context_hash):
        raise ValueError("locked calibration context hash is malformed")
    sensitivity = np.asarray(FIXED_SENSITIVITY_BANK, dtype=np.float64)
    if sensitivity.shape != (8,) or np.array_equal(primary, sensitivity):
        raise ValueError("primary and sensitivity query-bank arms must be distinct")
    return np.stack([primary, sensitivity], axis=0)


def verify_runtime(repo: str | Path | None = None) -> dict:
    root = repository_root() if repo is None else Path(repo).resolve()
    expected = json.loads((root / "environment" / "runtime.json").read_text())
    actual = {
        "implementation": platform.python_implementation(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy": importlib.metadata.version("numpy"),
        "scipy": importlib.metadata.version("scipy"),
        "scikit-learn": importlib.metadata.version("scikit-learn"),
        "torch": importlib.metadata.version("torch"),
    }
    for key, observed in actual.items():
        if str(expected.get(key)) != str(observed):
            raise RuntimeError(f"runtime fingerprint mismatch for {key}: {observed}")
    if expected.get("backend") != "cpu" or expected.get("deterministic_algorithms") is not True:
        raise RuntimeError("runtime lock does not require deterministic CPU execution")
    installed = json.loads(
        (root / "environment" / "installed-distributions.json").read_text()
    )
    executable = installed.get("python_executable", {})
    if (
        Path(sys.executable).stat().st_size != executable.get("size")
        or sha256_file(sys.executable) != executable.get("sha256")
    ):
        raise RuntimeError("Python executable does not match the installed-runtime lock")
    distributions = installed.get("distributions", {})
    for name in ("numpy", "scipy", "scikit-learn", "torch"):
        record = distributions.get(name, {})
        distribution = importlib.metadata.distribution(name)
        record_relative = next(
            item for item in distribution.files if str(item).endswith(".dist-info/RECORD")
        )
        record_path = Path(distribution.locate_file(record_relative))
        if (
            distribution.version != record.get("version")
            or record_path.stat().st_size != record.get("record_size")
            or sha256_file(record_path) != record.get("record_sha256")
        ):
            raise RuntimeError(f"installed distribution record mismatch: {name}")
    return actual


def _require_pair(values, name: str) -> tuple[float, float]:
    if not isinstance(values, list) or len(values) != 2:
        raise ValueError(f"{name} must be a two-element list")
    low, high = (float(values[0]), float(values[1]))
    if not np.isfinite([low, high]).all() or low > high:
        raise ValueError(f"{name} is not a finite ordered interval")
    return low, high


def validate_locked_validations(
    repo: str | Path | None = None,
    *,
    query_banks: np.ndarray | None = None,
) -> dict[str, dict]:
    root = repository_root() if repo is None else Path(repo).resolve()
    banks = load_locked_query_banks(root) if query_banks is None else np.asarray(query_banks)
    if banks.shape != (2, 8):
        raise ValueError("validation query banks must have shape (2, 8)")
    values = {}
    for relative in sorted(REQUIRED_VALIDATIONS):
        path = root / relative
        value = json.loads(path.read_text())
        if value.get("schema_version") != 1 or value.get("pass") is not True:
            raise ValueError(f"required validation did not pass: {relative}")
        values[relative] = value

    for index, role in enumerate(("primary", "sensitivity")):
        instrument = values[f"artifacts/validation/instrument_{role}.json"]
        if instrument.get("producer_sha256") != sha256_file(
            root / "src" / "pfn_dag_verify" / "validation.py"
        ):
            raise ValueError(f"instrument producer hash mismatch: {role}")
        if instrument.get("bank_role") != role:
            raise ValueError(f"instrument validation role mismatch: {role}")
        if instrument.get("quadrature") != 15 or instrument.get("unit_contexts") != 64:
            raise ValueError(f"instrument validation scope mismatch: {role}")
        np.testing.assert_array_equal(np.asarray(instrument.get("query_bank")), banks[index])
        if instrument.get("oracle_grid_size") != 3097:
            raise ValueError(f"instrument oracle grid mismatch: {role}")
        canary_low, canary_high = _require_pair(instrument.get("canary_interval"), "canary")
        numeric_limits = {
            "max_scalar_vector_ell_error": 1e-10,
            "max_scalar_vector_endpoint_error": 1e-10,
            "max_coordinate_weight_error": 1e-4,
            "max_kl_weight_error": 1e-3,
            "coordinate_kl_g_median": 0.01,
            "coordinate_kl_g_p95": 0.05,
            "max_tempered_slope_error": 0.02,
            "max_tempered_intercept_error": 0.02,
            "max_label_swap_error": 1e-10,
            "exact_reconstruction_residual": 1e-10,
        }
        numeric_pass = all(
            np.isfinite(float(instrument.get(key, np.inf)))
            and 0 <= float(instrument[key]) <= limit
            for key, limit in numeric_limits.items()
        )
        canary_pass = (
            canary_low >= -0.15
            and canary_high <= 0.15
            and canary_low <= 0 <= canary_high
        )
        recomputed_pass = bool(
            numeric_pass
            and canary_pass
            and instrument.get("degenerate_endpoint_fails_closed") is True
        )
        if not canary_pass:
            raise ValueError(f"instrument canary mismatch: {role}")
        if instrument.get("pass") is not recomputed_pass or not recomputed_pass:
            raise ValueError(f"instrument numeric thresholds failed: {role}")

        legacy = values[f"artifacts/validation/legacy_oracle_{role}.json"]
        if legacy.get("producer_sha256") != sha256_file(
            root / "src" / "pfn_dag_verify" / "legacy_compare.py"
        ):
            raise ValueError(f"legacy producer hash mismatch: {role}")
        if legacy.get("bank_role") != role or legacy.get("n_contexts") != 8:
            raise ValueError(f"legacy validation scope mismatch: {role}")
        np.testing.assert_array_equal(np.asarray(legacy.get("queries")), banks[index])
        legacy_path = root / str(legacy.get("legacy_file"))
        if not legacy_path.is_file() or sha256_file(legacy_path) != legacy.get("legacy_sha256"):
            raise ValueError(f"legacy source snapshot mismatch: {role}")
        legacy_errors = np.asarray(
            [
                legacy.get("max_ell_error", np.inf),
                legacy.get("max_f0_error", np.inf),
                legacy.get("max_f1_error", np.inf),
            ],
            dtype=np.float64,
        )
        legacy_pass = bool(
            np.isfinite(legacy_errors).all()
            and np.all(legacy_errors >= 0)
            and np.max(legacy_errors) <= 1e-10
        )
        if legacy.get("pass") is not legacy_pass or not legacy_pass:
            raise ValueError(f"legacy numeric thresholds failed: {role}")

    coverage = values["artifacts/validation/bootstrap_coverage.json"]
    if coverage.get("producer_sha256") != sha256_file(
        root / "src" / "pfn_dag_verify" / "validation.py"
    ):
        raise ValueError("bootstrap producer hash mismatch")
    if (
        coverage.get("datasets_per_slope") != 500
        or coverage.get("bootstraps_per_dataset") != 1000
        or coverage.get("groups") != 256
        or coverage.get("percentile_interval") != [0.02, 0.98]
        or coverage.get("validation_seed") != 850002
        or set(coverage.get("results", {})) != {"0.8", "1.0", "1.2"}
    ):
        raise ValueError("bootstrap validation scope mismatch")
    coverage_pass = True
    for value in coverage["results"].values():
        low, high = _require_pair(value.get("coverage_wilson_95"), "coverage Wilson")
        estimate = float(value.get("coverage", np.nan))
        width = float(value.get("mean_interval_width", np.nan))
        coverage_pass = coverage_pass and bool(
            np.isfinite([estimate, width]).all()
            and 0 <= estimate <= 1
            and width > 0
            and estimate >= 0.93
            and low <= 0.95 <= high
        )
    if coverage.get("pass") is not coverage_pass or not coverage_pass:
        raise ValueError("bootstrap numeric thresholds failed")

    smoke = values["artifacts/validation/smoke_budget.json"]
    if smoke.get("producer_sha256") != sha256_file(
        root / "src" / "pfn_dag_verify" / "smoke.py"
    ):
        raise ValueError("smoke producer hash mismatch")
    expected_smoke = {
        "smoke_kind": "interior-selected-end-to-end-v3",
        "smoke_stream_label": "smoke-v3",
        "smoke_groups": 8,
        "smoke_continuations": 8,
        "max_core_candidates": 2000,
        "max_blocks_per_core": 512,
        "min_within_group_sd": 0.25,
        "wall_cap_seconds": WALL_CAP_SECONDS,
        "memory_cap_bytes": MEMORY_CAP_BYTES,
        "raw_cap_bytes": RAW_CAP_BYTES,
    }
    for key, expected in expected_smoke.items():
        if smoke.get(key) != expected:
            raise ValueError(f"smoke-budget scope mismatch: {key}")
    enforce_cost_gate(smoke)
    smoke_pass = bool(
        smoke.get("eligible_replace_rows") == 64
        and smoke.get("prediction_shards") == 4
        and float(smoke["projected_wall_seconds"]) <= WALL_CAP_SECONDS
        and int(smoke["projected_peak_rss_bytes"]) <= MEMORY_CAP_BYTES
        and int(smoke["projected_raw_bytes"]) <= RAW_CAP_BYTES
    )
    if smoke.get("pass") is not smoke_pass or not smoke_pass:
        raise ValueError("smoke numeric thresholds failed")
    return values


def enforce_cost_gate(smoke: dict) -> None:
    projected = (
        float(smoke.get("projected_wall_seconds", float("inf"))),
        int(smoke.get("projected_peak_rss_bytes", MEMORY_CAP_BYTES + 1)),
        int(smoke.get("projected_raw_bytes", RAW_CAP_BYTES + 1)),
    )
    if not np.isfinite(projected[0]) or projected[0] > WALL_CAP_SECONDS:
        raise RuntimeError("BLOCKED_COST: projected wall-clock limit exceeded")
    if projected[1] > MEMORY_CAP_BYTES:
        raise RuntimeError("BLOCKED_COST: projected memory limit exceeded")
    if projected[2] > RAW_CAP_BYTES:
        raise RuntimeError("BLOCKED_COST: projected raw-storage limit exceeded")


def verify_run_lock(repo: str | Path | None = None) -> tuple[str, str, dict]:
    root = repository_root() if repo is None else Path(repo).resolve()
    if root != repository_root():
        raise ValueError("scientific stages must use the repository containing the package")
    head = clean_head(root)
    lock_path, lock = load_run_lock(root)
    files = lock.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("run lock has no file manifest")
    expected_files = expected_run_lock_files(root)
    if set(files) != expected_files:
        raise ValueError("run lock does not contain the exact audited source and guard set")
    for relative, expected_hash in files.items():
        path = root / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise ValueError(f"run-lock file mismatch: {relative}")
    if set(lock.get("required_validations", [])) != REQUIRED_VALIDATIONS:
        raise ValueError("run lock does not name the exact required validation set")
    settings = lock.get("settings", {})
    expected_settings = {
        "groups": 256,
        "continuations": 8,
        "max_core_candidates": 2000,
        "max_blocks_per_core": 512,
        "min_within_group_sd": 0.25,
        "bootstrap_replicates": 10000,
        "permutation_replicates": 2000,
        "interval_quantiles": [0.02, 0.98],
        "model_batch_size": 64,
        "smoke_stream": {"label": "smoke-v3", "groups": 8, "continuations": 8},
    }
    if settings != expected_settings:
        raise ValueError("run-lock settings differ from the scientific specification")
    load_locked_query_banks(root)
    verify_runtime(root)
    validate_locked_validations(root)
    return head, sha256_file(lock_path), lock


def decode_ascii(array) -> str:
    return bytes(array.tolist()).decode("ascii")


def verify_panel_lock(panel: dict, repo: str | Path | None = None) -> tuple[str, dict]:
    head, lock_hash, lock = verify_run_lock(repo)
    if decode_ascii(panel["commit_sha"]) != head:
        raise ValueError("panel commit does not match clean HEAD")
    if "run_lock_sha256" not in panel:
        raise ValueError("panel does not embed the run-lock hash")
    if bytes(panel["run_lock_sha256"].tolist()).hex() != lock_hash:
        raise ValueError("panel run-lock hash mismatch")
    if int(panel.get("scientific", np.asarray(0))) != 1:
        raise ValueError("panel is not marked scientific")
    settings = lock["settings"]
    expected_shape = (settings["groups"], settings["continuations"], 10, 2)
    if panel.get("continuations", np.empty(0)).shape != expected_shape:
        raise ValueError("scientific panel dimensions do not match the run lock")
    if int(panel.get("selection_mode", np.asarray(0))) != 1:
        raise ValueError("scientific panel did not use selected-interior sampling")
    if (
        int(panel.get("selection_max_core_candidates", -1))
        != settings["max_core_candidates"]
        or int(panel.get("selection_max_blocks_per_core", -1))
        != settings["max_blocks_per_core"]
        or float(panel.get("selection_min_within_group_sd", np.nan))
        != settings["min_within_group_sd"]
    ):
        raise ValueError("scientific selection settings do not match the run lock")
    if not np.array_equal(panel.get("query_banks"), load_locked_query_banks(repo)):
        raise ValueError("scientific panel query banks do not match the run lock")
    eligible = np.asarray(panel.get("eligible_replace"), dtype=bool)
    if eligible.shape != (settings["groups"], settings["continuations"]) or not eligible.all():
        raise ValueError("scientific replace panel is not fully eligible")
    reasons = np.asarray(panel.get("candidate_core_reason"))
    ranks = np.asarray(panel.get("candidate_core_acceptance_rank"))
    accepted_ids = np.flatnonzero(reasons == 0)
    if accepted_ids.size != settings["groups"] or not np.array_equal(
        ranks[accepted_ids], np.arange(settings["groups"])
    ):
        raise ValueError("scientific panel is not the first ranked accepted cohort")
    np.testing.assert_array_equal(panel["core"], panel["candidate_core_context"][accepted_ids])
    np.testing.assert_array_equal(panel["sigma"], panel["candidate_core_sigma"][accepted_ids])
    np.testing.assert_array_equal(panel["graph"], panel["candidate_core_graph"][accepted_ids])
    np.testing.assert_array_equal(panel["params"], panel["candidate_core_params"][accepted_ids])
    core_seeds = np.asarray(panel.get("candidate_core_seed"))
    if core_seeds.dtype != np.uint64 or not np.array_equal(
        core_seeds,
        np.asarray(
            [derive_seed(head, f"core-candidate:{index}") for index in range(len(core_seeds))],
            dtype=np.uint64,
        ),
    ):
        raise ValueError("scientific core child-seed record is invalid")
    block_core = np.asarray(panel.get("candidate_block_core_index"))
    block_index = np.asarray(panel.get("candidate_block_index"))
    block_seeds = np.asarray(panel.get("candidate_block_seed"))
    if block_seeds.dtype != np.uint64 or not np.array_equal(
        block_seeds,
        np.asarray(
            [
                derive_seed(head, f"core-candidate:{core}:block:{index}")
                for core, index in zip(block_core, block_index, strict=True)
            ],
            dtype=np.uint64,
        ),
    ):
        raise ValueError("scientific block child-seed record is invalid")
    block_reason = np.asarray(panel.get("candidate_block_reason"))
    block_rank = np.asarray(panel.get("candidate_block_eligible_rank"))
    block_context = np.asarray(panel.get("candidate_block_context"))
    for panel_index, core_id in enumerate(accepted_ids):
        rows = np.flatnonzero((block_core == core_id) & (block_reason == 0))
        order = rows[np.argsort(block_rank[rows])]
        if order.size != settings["continuations"] + 1 or not np.array_equal(
            block_rank[order], np.arange(settings["continuations"] + 1)
        ):
            raise ValueError("accepted core does not contain the first nine eligible blocks")
        np.testing.assert_array_equal(panel["reference"][panel_index], block_context[order[0]])
        np.testing.assert_array_equal(panel["continuations"][panel_index], block_context[order[1:]])
    return head, lock
