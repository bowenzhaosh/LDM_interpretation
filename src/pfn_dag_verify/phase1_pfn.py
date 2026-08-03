"""Fail-closed native-head scorer for the frozen Phase-1 PFN fleet.

This process accepts panel inputs only. It never accepts or opens labels,
outcomes, observed bins, oracle predictions, or scientific endpoints.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import torch

from .phase1_confirm_common import (
    acquire_empty_output,
    attempt_identity,
    load_json,
    repo_root,
    sha256_file,
    validate_checkpoint_registry,
)
from .phase1_panel import INPUT_ARRAYS, ROW_KEYS, _digest_rows
from .storage import write_json_atomic, write_numeric_npz_atomic


PREDICTION_ARRAYS = (
    "schema_version",
    "attempt_identity_sha256",
    *ROW_KEYS,
    "row_key_sha256",
    "input_row_sha256",
    "model_seed",
    "checkpoint_step",
    "log_probability",
)


def _load_model_module(path: Path) -> ModuleType:
    os.environ["D4_SCALE"] = "base"
    spec = importlib.util.spec_from_file_location("phase1_frozen_d4_model", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load model definition: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    constants = {
        "D_DIM": 4,
        "D_MODEL": 256,
        "D_FF": 512,
        "N_HEADS": 4,
        "N_LAYERS": 2,
        "N_BINS": 100,
        "NULL_TOK": 2,
    }
    if any(getattr(module, name, None) != value for name, value in constants.items()):
        raise RuntimeError("frozen PFN4 architecture constants mismatch")
    return module


def _checkpoint_record(
    registry: dict[str, Any], prior: str, seed: int, step: int
) -> dict[str, Any]:
    matches = [
        row
        for row in registry.get("records", [])
        if (
            row.get("prior"),
            int(row.get("seed", -1)),
            int(row.get("checkpoint_step", -1)),
        )
        == (prior, seed, step)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"checkpoint registry tuple is not unique: {prior} {seed} {step}"
        )
    return matches[0]


def load_checkpoint(
    config: dict[str, Any],
    prior: str,
    seed: int,
    step: int,
    device: torch.device,
    registry: dict[str, Any] | None = None,
) -> tuple[torch.nn.Module, dict[str, Any]]:
    if registry is None:
        registry = validate_checkpoint_registry(config, verify_remote_files=True)
    model_path = (repo_root() / str(config["model_definition"])).resolve()
    if sha256_file(model_path) != config["model_definition_sha256"]:
        raise RuntimeError("model-definition hash mismatch")
    if registry.get("model_definition_sha256") != config["model_definition_sha256"]:
        raise RuntimeError("registry/model-definition mismatch")
    record = _checkpoint_record(registry, prior, seed, step)
    checkpoint_root = Path(str(registry["remote_root"])).resolve()
    checkpoint_path = (checkpoint_root / str(record["filename"])).resolve(strict=True)
    if checkpoint_root not in checkpoint_path.parents:
        raise RuntimeError("checkpoint escapes the registered root")
    payload = checkpoint_path.read_bytes()
    if len(payload) != int(record["bytes"]):
        raise RuntimeError(f"checkpoint byte-count mismatch: {checkpoint_path}")
    if hashlib.sha256(payload).hexdigest() != record["sha256"]:
        raise RuntimeError(f"checkpoint hash mismatch: {checkpoint_path}")
    module = _load_model_module(model_path)
    model = module.PFN4()
    if sum(parameter.numel() for parameter in model.parameters()) != 1_082_980:
        raise RuntimeError("PFN4 parameter count mismatch")
    state = torch.load(io.BytesIO(payload), map_location="cpu", weights_only=True)
    if not isinstance(state, dict) or len(state) != 31:
        raise RuntimeError(
            "checkpoint is not the exact plain 31-tensor state dictionary"
        )
    if any(
        not isinstance(value, torch.Tensor) or value.dtype != torch.float32
        for value in state.values()
    ):
        raise RuntimeError(
            "checkpoint contains a non-float32 or non-tensor state value"
        )
    if any(not torch.isfinite(value).all() for value in state.values()):
        raise RuntimeError("checkpoint contains a non-finite state value")
    model.load_state_dict(state, strict=True)
    model.eval().to(device)
    return model, {**record, "resolved_path": str(checkpoint_path)}


def _infer(
    model: torch.nn.Module,
    contexts: np.ndarray,
    queries: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    if contexts.shape != (len(contexts), 30, 4) or queries.shape != (len(contexts), 3):
        raise RuntimeError("PFN scorer input shape mismatch")
    if not np.isfinite(contexts).all() or not np.isfinite(queries).all():
        raise RuntimeError("PFN scorer received non-finite input")
    outputs: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, len(contexts), batch_size):
            stop = min(len(contexts), start + batch_size)
            context = torch.as_tensor(
                contexts[start:stop], dtype=torch.float32, device=device
            )
            query = torch.as_tensor(
                queries[start:stop, None, :], dtype=torch.float32, device=device
            )
            token = torch.full((stop - start,), 2, dtype=torch.long, device=device)
            logits = model(context, query, token)
            if (
                logits.shape != (stop - start, 1, 100)
                or not torch.isfinite(logits).all()
            ):
                raise RuntimeError("PFN emitted invalid native logits")
            log_probability = torch.log_softmax(logits[:, 0, :], dim=-1)
            if not torch.isfinite(log_probability).all():
                raise RuntimeError("PFN emitted invalid native log-probabilities")
            outputs.append(log_probability.cpu().numpy().astype(np.float64))
    joined = np.concatenate(outputs, axis=0)
    if joined.shape != (len(contexts), 100):
        raise RuntimeError("PFN output row-count mismatch")
    normalization = np.abs(np.exp(joined).sum(axis=1) - 1.0)
    if float(normalization.max()) > 1e-6:
        raise RuntimeError("PFN log-probability normalization failure")
    return joined


def _verify_inputs_marker(
    panel_dir: Path, identity: dict[str, Any], identity_sha256: str
) -> dict[str, dict[str, Any]]:
    marker = load_json(panel_dir / "INPUTS_COMPLETE.json")
    if (
        marker.get("identity") != identity
        or marker.get("identity_sha256") != identity_sha256
    ):
        raise RuntimeError("panel-input attempt identity mismatch")
    artifacts = marker.get("artifacts")
    expected = {
        f"{prior}_d{draw}_b{bank}.npz"
        for prior in ("C", "N")
        for draw in range(3)
        for bank in range(3)
    }
    if not isinstance(artifacts, dict) or set(artifacts) != expected:
        raise RuntimeError("panel-input artifact inventory mismatch")
    for name, record in artifacts.items():
        path = panel_dir / "inputs" / name
        if (
            path.stat().st_size != int(record["bytes"])
            or sha256_file(path) != record["sha256"]
        ):
            raise RuntimeError(f"panel-input artifact mismatch: {name}")
    return artifacts


def _load_input_shard(
    path: Path,
    identity_sha256: str,
    prior: str,
    draw: int,
    bank: int,
    config: dict[str, Any],
) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        if tuple(archive.files) != INPUT_ARRAYS:
            raise RuntimeError(f"panel-input schema mismatch: {path}")
        arrays = {name: archive[name].copy() for name in archive.files}
    n = 356 if bank < 2 else 355
    if arrays["contexts"].shape != (n, 30, 4) or arrays["queries"].shape != (n, 3):
        raise RuntimeError(f"panel-input shape mismatch: {path}")
    expected_identity = np.frombuffer(bytes.fromhex(identity_sha256), dtype=np.uint8)
    if not np.array_equal(arrays["attempt_identity_sha256"], expected_identity):
        raise RuntimeError(f"panel-input identity mismatch: {path}")
    prior_code = 0 if prior == "C" else 1
    expected_seed = int(config["evaluation_seeds"][prior][draw])
    expected_atom = int(config["atom_banks"][bank]["seed"])
    checks = {
        "prior_code": prior_code,
        "draw_index": draw,
        "evaluation_seed": expected_seed,
        "atom_bank_index": bank,
        "atom_seed": expected_atom,
    }
    if any(not np.all(arrays[name] == value) for name, value in checks.items()):
        raise RuntimeError(f"panel-input metadata mismatch: {path}")
    expected_indices = np.arange(bank, 1067, 3, dtype=np.int64)
    if not np.array_equal(arrays["stream_index"], expected_indices):
        raise RuntimeError(f"panel-input stream-index mismatch: {path}")
    if not np.array_equal(arrays["shard_local_index"], np.arange(n)):
        raise RuntimeError(f"panel-input local-index mismatch: {path}")
    if not np.array_equal(arrays["row_key_sha256"], _digest_rows(arrays, ROW_KEYS)):
        raise RuntimeError(f"panel-input row-key hash mismatch: {path}")
    if not np.array_equal(
        arrays["input_row_sha256"],
        _digest_rows(arrays, (*ROW_KEYS, "contexts", "queries")),
    ):
        raise RuntimeError(f"panel-input row-content hash mismatch: {path}")
    forbidden = {"outcomes", "outcome_bins", "sigmas", "true_orderings"}
    if forbidden & set(arrays):
        raise RuntimeError("PFN scorer received forbidden label arrays")
    return arrays


def _replay_guard(
    model: torch.nn.Module,
    shards: list[dict[str, np.ndarray]],
    config: dict[str, Any],
    device: torch.device,
) -> dict[str, float | int | bool]:
    take = int(config["pfn_replay_rows_per_stratum"])
    contexts = np.concatenate([shard["contexts"][:take] for shard in shards])
    queries = np.concatenate([shard["queries"][:take] for shard in shards])
    batch_size = int(config["pfn_batch_size"])
    batched = _infer(model, contexts, queries, batch_size, device)
    singleton = _infer(model, contexts, queries, 1, device)
    reverse = np.arange(len(contexts) - 1, -1, -1)
    reversed_output = _infer(
        model, contexts[reverse], queries[reverse], batch_size, device
    )[reverse]
    permutation = np.roll(np.arange(30), int(config["pfn_context_permutation_roll"]))
    permuted = _infer(model, contexts[:, permutation], queries, batch_size, device)
    batch_error = float(
        max(
            np.max(np.abs(batched - singleton)),
            np.max(np.abs(batched - reversed_output)),
        )
    )
    context_error = float(np.max(np.abs(batched - permuted)))
    passed = bool(
        batch_error <= float(config["pfn_batch_logp_atol"])
        and context_error <= float(config["pfn_context_permutation_logp_atol"])
    )
    return {
        "rows": len(contexts),
        "singleton_and_reverse_batch_max_abs_logp_error": batch_error,
        "context_roll_max_abs_logp_error": context_error,
        "pass": passed,
    }


def score_fleet(
    config_path: Path, panel_dir: Path, output_dir: Path, device_name: str = "cuda"
) -> dict[str, Any]:
    device = torch.device(device_name)
    identity, identity_sha256, config, git = attempt_identity(
        config_path.resolve(),
        [Path(__file__), Path(__file__).with_name("phase1_panel.py")],
        device=device,
    )
    _verify_inputs_marker(panel_dir.resolve(), identity, identity_sha256)
    lease = acquire_empty_output(output_dir, identity_sha256)
    output_dir = output_dir.resolve()
    running_path = output_dir / "RUNNING.json"
    write_json_atomic(
        running_path, {"identity": identity, "identity_sha256": identity_sha256}
    )
    registry = validate_checkpoint_registry(config, verify_remote_files=False)
    records = registry.get("records", [])
    expected_tuples = {
        (prior, seed, step)
        for prior in ("C", "N")
        for seed in range(3)
        for step in (20_000, 60_000, 120_000)
    }
    observed_tuples = {
        (str(row["prior"]), int(row["seed"]), int(row["checkpoint_step"]))
        for row in records
    }
    if observed_tuples != expected_tuples or len(records) != 18:
        raise RuntimeError("checkpoint registry is not the exact frozen fleet")
    marker_hashes: dict[str, str] = {}
    replay: dict[str, Any] = {}
    for prior, seed, step in sorted(expected_tuples):
        model, checkpoint = load_checkpoint(
            config, prior, seed, step, device, registry=registry
        )
        shards: list[dict[str, np.ndarray]] = []
        identities: list[tuple[int, int, Path]] = []
        for draw in range(3):
            for bank in range(3):
                input_path = panel_dir / "inputs" / f"{prior}_d{draw}_b{bank}.npz"
                shards.append(
                    _load_input_shard(
                        input_path, identity_sha256, prior, draw, bank, config
                    )
                )
                identities.append((draw, bank, input_path))
        guard = _replay_guard(model, shards, config, device)
        replay[f"{prior}_s{seed}_t{step}"] = guard
        if not guard["pass"]:
            raise RuntimeError(
                f"PFN replay guard failed: {prior} seed {seed} step {step}"
            )
        for shard, (draw, bank, input_path) in zip(shards, identities, strict=True):
            log_probability = _infer(
                model,
                shard["contexts"],
                shard["queries"],
                int(config["pfn_batch_size"]),
                device,
            )
            n = len(log_probability)
            raw = {
                "schema_version": np.array([1], dtype=np.int64),
                "attempt_identity_sha256": np.frombuffer(
                    bytes.fromhex(identity_sha256), dtype=np.uint8
                ).copy(),
                **{name: shard[name].copy() for name in ROW_KEYS},
                "row_key_sha256": shard["row_key_sha256"].copy(),
                "input_row_sha256": shard["input_row_sha256"].copy(),
                "model_seed": np.full(n, seed, dtype=np.int64),
                "checkpoint_step": np.full(n, step, dtype=np.int64),
                "log_probability": log_probability,
            }
            if tuple(raw) != PREDICTION_ARRAYS:
                raise RuntimeError("PFN prediction schema drift")
            shard_dir = output_dir / f"{prior}_s{seed}_t{step}" / f"d{draw}_b{bank}"
            raw_path = shard_dir / "prediction_raw.npz"
            write_numeric_npz_atomic(raw_path, **raw)
            summary = {
                "schema_version": 1,
                "stage": "phase1_native_pfn_prediction",
                "completion_state": "INCOMPLETE_WITHOUT_VERIFIED_COMPLETE_MARKER",
                "identity_sha256": identity_sha256,
                "git": git,
                "prior": prior,
                "model_seed": seed,
                "checkpoint_step": step,
                "draw_index": draw,
                "atom_bank_index": bank,
                "rows": n,
                "input_sha256": sha256_file(input_path),
                "checkpoint": checkpoint,
                "convention": "native_float32_log_softmax_cast_float64_no_floor",
                "raw_sha256": sha256_file(raw_path),
            }
            summary_path = shard_dir / "prediction_summary.json"
            write_json_atomic(summary_path, summary)
            complete_path = shard_dir / "COMPLETE.json"
            write_json_atomic(
                complete_path,
                {
                    "identity_sha256": identity_sha256,
                    "identity_tuple": [prior, seed, step, draw, bank],
                    "artifacts": {
                        path.name: {
                            "sha256": sha256_file(path),
                            "bytes": path.stat().st_size,
                        }
                        for path in (raw_path, summary_path)
                    },
                },
            )
            marker_hashes[str(complete_path.relative_to(output_dir))] = sha256_file(
                complete_path
            )
        del model
        torch.cuda.empty_cache()
    if len(marker_hashes) != 162:
        raise RuntimeError("PFN scorer did not produce exactly 162 prediction shards")
    summary = {
        "schema_version": 1,
        "stage": "phase1_native_pfn_fleet",
        "completion_state": "INCOMPLETE_WITHOUT_VERIFIED_COMPLETE_MARKER",
        "identity": identity,
        "identity_sha256": identity_sha256,
        "git": git,
        "prediction_shards": len(marker_hashes),
        "checkpoint_count": 18,
        "replay": replay,
        "marker_hashes": marker_hashes,
    }
    summary_path = output_dir / "pfn_fleet_summary.json"
    write_json_atomic(summary_path, summary)
    end_identity, end_sha256, _, _ = attempt_identity(
        config_path.resolve(),
        [Path(__file__), Path(__file__).with_name("phase1_panel.py")],
        device=device,
    )
    if end_identity != identity or end_sha256 != identity_sha256:
        raise RuntimeError("confirmation attempt identity changed during PFN scoring")
    complete_path = output_dir / "COMPLETE.json"
    write_json_atomic(
        complete_path,
        {
            "identity": identity,
            "identity_sha256": identity_sha256,
            "decision": "PFN_FLEET_COMPLETE",
            "artifacts": {
                "RUNNING.json": {
                    "sha256": sha256_file(running_path),
                    "bytes": running_path.stat().st_size,
                },
                "pfn_fleet_summary.json": {
                    "sha256": sha256_file(summary_path),
                    "bytes": summary_path.stat().st_size,
                },
            },
            "leaf_marker_hashes": marker_hashes,
        },
    )
    lease.unlink()
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    arguments = parser.parse_args(argv)
    result = score_fleet(
        arguments.config, arguments.panel, arguments.out, arguments.device
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
