import argparse
import json
from pathlib import Path

from .provenance import (
    REQUIRED_VALIDATIONS,
    expected_run_lock_files,
    repository_root,
    validate_locked_validations,
)
from .registry import sha256_file
from .storage import write_json_atomic


def build_run_lock(root: Path):
    validate_locked_validations(root)
    files = {}
    for relative in sorted(expected_run_lock_files(root)):
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        files[relative] = sha256_file(path)
    return {
        "schema_version": 1,
        "files": files,
        "required_validations": sorted(REQUIRED_VALIDATIONS),
        "settings": {
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
        },
        "claim_scope": "selected identifiable-interior AL40 replace-10 regime",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=repository_root() / "config/run_lock.json")
    args = parser.parse_args(argv)
    root = repository_root()
    lock = build_run_lock(root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(args.out, lock)
    print(json.dumps({"files": len(lock["files"]), "out": str(args.out)}, sort_keys=True))


if __name__ == "__main__":
    main()
