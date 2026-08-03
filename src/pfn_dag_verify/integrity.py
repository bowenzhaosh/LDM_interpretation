import json
from pathlib import Path

from .evaluation import _validate_prediction_shard
from .provenance import repository_root, verify_panel_lock
from .registry import expanded_checkpoint_record, load_checkpoint_registry, sha256_file
from .storage import load_numeric_npz


EXPECTED_IDENTITIES = {
    (seed, step, bank)
    for seed in range(16)
    for step in (0, 12_000)
    for bank in (0, 1)
}


def verify_prediction_ledger(
    *, panel_path: Path, prediction_dir: Path
) -> tuple[dict, dict, list[Path]]:
    panel_path = panel_path.resolve()
    prediction_dir = prediction_dir.resolve()
    panel = load_numeric_npz(panel_path)
    commit, _ = verify_panel_lock(panel)
    panel_hash = sha256_file(panel_path)
    ledger_path = prediction_dir / "prediction_ledger.json"
    ledger = json.loads(ledger_path.read_text())
    if (
        ledger.get("schema_version") != 1
        or ledger.get("scientific") is not True
        or ledger.get("commit_sha") != commit
        or ledger.get("panel_sha256") != panel_hash
        or ledger.get("run_lock_sha256")
        != bytes(panel["run_lock_sha256"].tolist()).hex()
    ):
        raise ValueError("prediction ledger identity mismatch")
    registry_path = repository_root() / "config" / "checkpoint_registry.json"
    if ledger.get("registry_sha256") != sha256_file(registry_path):
        raise ValueError("prediction ledger registry hash mismatch")
    registry = load_checkpoint_registry(registry_path)
    records = ledger.get("records")
    if not isinstance(records, list) or len(records) != 64:
        raise ValueError("prediction ledger must contain exactly 64 records")
    observed = set()
    paths = []
    groups = panel["core"].shape[0]
    continuations = panel["continuations"].shape[1]
    for record in records:
        identity = (
            int(record.get("seed", -1)),
            int(record.get("step", -1)),
            int(record.get("bank_index", -1)),
        )
        if identity in observed:
            raise ValueError(f"duplicate prediction identity: {identity}")
        observed.add(identity)
        seed, step, bank_index = identity
        expected_name = f"pred_s{seed:02d}_step{step:05d}_bank{bank_index}.npz"
        if record.get("path") != expected_name:
            raise ValueError("prediction record path does not match its identity")
        path = prediction_dir / expected_name
        if (
            not path.is_file()
            or path.stat().st_size != int(record.get("size", -1))
            or sha256_file(path) != record.get("sha256")
        ):
            raise ValueError(f"prediction record content mismatch: {expected_name}")
        checkpoint = expanded_checkpoint_record(registry, seed, step)
        shard = load_numeric_npz(path)
        _validate_prediction_shard(
            shard,
            core_count=groups,
            continuation_count=continuations,
            queries=panel["query_banks"][bank_index],
            seed=seed,
            step=step,
            bank_index=bank_index,
            checkpoint_sha256=checkpoint["sha256"],
            panel_sha256=panel_hash,
            scientific=True,
        )
        paths.append(path)
    if observed != EXPECTED_IDENTITIES:
        raise ValueError("prediction ledger identities are incomplete")
    actual_names = {path.name for path in prediction_dir.glob("pred_*.npz")}
    expected_names = {path.name for path in paths}
    if actual_names != expected_names:
        raise ValueError("prediction directory contains a stale or missing shard")
    return panel, ledger, paths
