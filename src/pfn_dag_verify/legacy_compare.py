import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from .generative import generate_group
from .oracle import GridOracle
from .query_bank import FIXED_SENSITIVITY_BANK
from .registry import sha256_file


def _load_legacy(path: Path):
    spec = importlib.util.spec_from_file_location("pfn_dag_legacy_stage1_for_compare", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    original_argv = sys.argv
    sys.argv = [str(path)]
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = original_argv
    return module


def compare(
    legacy_file: Path,
    queries: np.ndarray,
    n_contexts: int = 8,
    bank_role: str = "primary",
    legacy_label: str | None = None,
):
    if n_contexts < 1:
        raise ValueError("legacy comparison requires at least one context")
    legacy = _load_legacy(legacy_file)
    current = GridOracle(queries=queries, quadrature=15)
    old = legacy.GridOracle("AL40", quad=15, queries=queries)
    rng = np.random.default_rng(810777)
    ell_errors = []
    f0_errors = []
    f1_errors = []
    for _ in range(n_contexts):
        group = generate_group(rng, n_continuations=2)
        context = np.concatenate([group.core, group.reference], axis=0)
        new_bundle = current.evaluate(context)
        old_bundle = old.eval_context(context)
        ell_errors.append(abs(new_bundle.ell - float(old_bundle["ell"])))
        f0_errors.append(float(np.max(np.abs(new_bundle.f0 - old_bundle["q2"]))))
        f1_errors.append(float(np.max(np.abs(new_bundle.f1 - old_bundle["q1"]))))
    errors = np.asarray([ell_errors, f0_errors, f1_errors], dtype=np.float64)
    if errors.size == 0 or not np.isfinite(errors).all():
        raise FloatingPointError("legacy comparison produced empty or non-finite errors")
    max_ell, max_f0, max_f1 = [float(np.max(row)) for row in errors]
    return {
        "schema_version": 1,
        "producer_sha256": sha256_file(Path(__file__)),
        "legacy_file": legacy_label or str(legacy_file.resolve()),
        "legacy_sha256": sha256_file(legacy_file),
        "n_contexts": n_contexts,
        "queries": queries.tolist(),
        "bank_role": bank_role,
        "max_ell_error": max_ell,
        "max_f0_error": max_f0,
        "max_f1_error": max_f1,
        "pass": bool(max(max_ell, max_f0, max_f1) <= 1e-10),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-file", type=Path, required=True)
    parser.add_argument("--query-bank", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bank", choices=("primary", "sensitivity"), default="primary")
    args = parser.parse_args(argv)
    if args.bank == "primary":
        bank = np.asarray(json.loads(args.query_bank.read_text())["selected_queries"], dtype=float)
    else:
        bank = FIXED_SENSITIVITY_BANK
    try:
        legacy_label = args.legacy_file.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        legacy_label = str(args.legacy_file.resolve())
    result = compare(
        args.legacy_file,
        bank,
        bank_role=args.bank,
        legacy_label=legacy_label,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    if not result["pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
