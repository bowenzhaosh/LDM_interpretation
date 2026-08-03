import argparse
import json
import tempfile
import time
from pathlib import Path

from .analysis import _derive_one
from .evaluation import (
    _peak_rss_bytes,
    configure_determinism,
    generate_panel,
    score_checkpoints,
)
from .provenance import (
    MEMORY_CAP_BYTES,
    RAW_CAP_BYTES,
    WALL_CAP_SECONDS,
    load_locked_query_banks,
    repository_root,
)
from .storage import load_numeric_npz, write_json_atomic, write_numeric_npz_atomic
from .registry import sha256_file


SMOKE_COMMIT = "5b0c0e" * 6 + "5b0c"


def run_smoke(out_path: Path) -> dict:
    configure_determinism(0)
    root = repository_root()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="pfn-dag-smoke-v3-") as temporary:
        run_dir = Path(temporary)
        panel_path = run_dir / "panel.npz"
        panel_metadata = generate_panel(
            commit_sha=SMOKE_COMMIT,
            query_banks=load_locked_query_banks(root),
            n_groups=8,
            n_continuations=8,
            out_path=panel_path,
            interior_selected=True,
            max_core_candidates=2_000,
            max_blocks_per_core=512,
            min_within_group_sd=0.25,
            scientific=False,
        )
        panel = load_numeric_npz(panel_path)
        if panel["eligible_replace"].shape != (8, 8) or not panel[
            "eligible_replace"
        ].astype(bool).all():
            raise AssertionError("smoke selected-interior panel is not fully eligible")

        prediction_dir = run_dir / "predictions"
        prediction_ledger = score_checkpoints(
            panel_path=panel_path,
            registry_path=root / "config" / "checkpoint_registry.json",
            out_dir=prediction_dir,
            seeds=[0],
            steps=[0, 12_000],
            scientific=False,
        )
        derive_started = time.perf_counter()
        derived_dir = run_dir / "derived"
        derived_dir.mkdir()
        derived_bytes = 0
        for record in prediction_ledger["records"]:
            prediction = load_numeric_npz(prediction_dir / record["path"])
            derived = _derive_one(panel, prediction, int(prediction["bank_index"]))
            path = derived_dir / record["path"].replace("pred_", "derived_")
            write_numeric_npz_atomic(path, **derived)
            derived_bytes += path.stat().st_size
        derive_wall = time.perf_counter() - derive_started

        panel_bytes = panel_path.stat().st_size
        panel_bytes += panel_path.with_suffix(".json").stat().st_size
        prediction_bytes = sum(
            (prediction_dir / record["path"]).stat().st_size
            for record in prediction_ledger["records"]
        )
        prediction_bytes += (prediction_dir / "prediction_ledger.json").stat().st_size

        group_ratio = 256 / 8
        shard_ratio = 64 / len(prediction_ledger["records"])
        inference_ratio = group_ratio * shard_ratio
        projected_panel_wall = panel_metadata["wall_seconds"] * group_ratio * 1.25
        projected_score_wall = prediction_ledger["wall_seconds"] * inference_ratio * 1.25
        projected_derive_wall = derive_wall * inference_ratio * 1.25
        projected_wall = (
            projected_panel_wall + projected_score_wall + projected_derive_wall
        )
        projected_raw = int(
            1.25
            * (
                panel_bytes * group_ratio
                + prediction_bytes * inference_ratio
                + derived_bytes * inference_ratio
                + 10 * 2**20
            )
        )
        projected_peak = int(
            max(
                _peak_rss_bytes() * 4,
                panel_bytes * group_ratio * 3,
                512 * 2**20,
            )
        )
        result = {
            "schema_version": 1,
            "producer_sha256": sha256_file(Path(__file__)),
            "smoke_stream_label": "smoke-v3",
            "smoke_kind": "interior-selected-end-to-end-v3",
            "smoke_commit": SMOKE_COMMIT,
            "smoke_groups": 8,
            "smoke_continuations": 8,
            "max_core_candidates": 2000,
            "max_blocks_per_core": 512,
            "min_within_group_sd": 0.25,
            "candidate_core_count": panel_metadata["candidate_core_count"],
            "candidate_block_count": panel_metadata["candidate_block_count"],
            "eligible_replace_rows": int(panel["eligible_replace"].sum()),
            "prediction_shards": len(prediction_ledger["records"]),
            "components": {
                "panel_wall_seconds": panel_metadata["wall_seconds"],
                "score_wall_seconds": prediction_ledger["wall_seconds"],
                "derive_wall_seconds": derive_wall,
                "panel_bytes": panel_bytes,
                "prediction_bytes": prediction_bytes,
                "derived_bytes": derived_bytes,
                "measured_peak_rss_bytes": _peak_rss_bytes(),
            },
            "projection_multipliers": {
                "group_ratio": group_ratio,
                "shard_ratio": shard_ratio,
                "safety_factor": 1.25,
            },
            "projected_wall_seconds": projected_wall,
            "projected_peak_rss_bytes": projected_peak,
            "projected_raw_bytes": projected_raw,
            "wall_cap_seconds": WALL_CAP_SECONDS,
            "memory_cap_bytes": MEMORY_CAP_BYTES,
            "raw_cap_bytes": RAW_CAP_BYTES,
            "measurement_wall_seconds": time.perf_counter() - started,
        }
        result["pass"] = bool(
            result["eligible_replace_rows"] == 64
            and result["prediction_shards"] == 4
            and projected_wall <= WALL_CAP_SECONDS
            and projected_peak <= MEMORY_CAP_BYTES
            and projected_raw <= RAW_CAP_BYTES
        )
    write_json_atomic(out_path, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_smoke(args.out)
    print(json.dumps(result, sort_keys=True))
    if not result["pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
