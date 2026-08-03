import argparse
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
from scipy.special import expit

from .generative import (
    ContextGroup,
    generate_group,
    sample_context,
    sample_valid_sigma,
    sigma_to_params,
)
from .model import (
    configure_determinism,
    load_registered_checkpoint,
    predict_probabilities,
)
from .oracle import GridOracle
from .provenance import (
    derive_seed,
    enforce_cost_gate,
    evaluation_root,
    load_locked_query_banks,
    repository_root,
    validate_locked_validations,
    verify_panel_lock,
    verify_run_lock,
)
from .registry import (
    expanded_checkpoint_record,
    load_checkpoint_registry,
    sha256_file,
)
from .storage import load_numeric_npz, write_json_atomic, write_numeric_npz_atomic


def _peak_rss_bytes():
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def _select_interior_groups(
    *,
    commit_sha: str,
    query_banks: np.ndarray,
    n_groups: int,
    n_continuations: int,
    max_core_candidates: int,
    max_blocks_per_core: int,
    min_within_group_sd: float,
):
    primary_oracle = GridOracle(query_banks[0], quadrature=15)
    alternate_oracle = GridOracle(query_banks[1], quadrature=15)
    required_blocks = n_continuations + 1
    selected = []
    core_sigma = []
    core_graph = []
    core_params = []
    core_context = []
    core_seed = []
    core_reason = []  # 0 accepted, 1 insufficient blocks, 2 insufficient ell variation
    core_acceptance_rank = []
    block_context = []
    block_core_index = []
    block_index = []
    block_seed = []
    block_ell = []
    block_js_primary = []
    block_js_alternate = []
    block_reason = []  # 0 eligible, 1 noninterior, 2 primary JS, 3 alternate JS
    block_eligible_rank = []

    for core_index in range(max_core_candidates):
        this_core_seed = derive_seed(commit_sha, f"core-candidate:{core_index}")
        core_rng = np.random.default_rng(this_core_seed)
        covariance = sample_valid_sigma(core_rng)
        graph = int(core_rng.integers(0, 2))
        parameters = sigma_to_params(covariance, graph)
        core = sample_context(core_rng, graph, parameters, 20)
        core_sigma.append(covariance)
        core_graph.append(graph)
        core_params.append([parameters.beta, parameters.b_root, parameters.b_effect])
        core_context.append(core)
        core_seed.append(this_core_seed)
        passing_blocks = []
        passing_ells = []

        for candidate_index in range(max_blocks_per_core):
            this_block_seed = derive_seed(
                commit_sha, f"core-candidate:{core_index}:block:{candidate_index}"
            )
            block_rng = np.random.default_rng(this_block_seed)
            block = sample_context(block_rng, graph, parameters, 10)
            context = np.concatenate([core, block], axis=0)
            ell = primary_oracle.log_evidence(context)
            weight = float(expit(ell))
            js_primary = -1.0
            js_alternate = -1.0
            reason = 1
            if 0.05 <= weight <= 0.95:
                primary_bundle = primary_oracle.evaluate(context)
                if abs(primary_bundle.ell - ell) > 1e-10:
                    raise AssertionError("selection evidence changed during endpoint evaluation")
                js_primary = primary_bundle.js
                if js_primary >= 0.1:
                    alternate_bundle = alternate_oracle.evaluate(context)
                    if abs(alternate_bundle.ell - ell) > 1e-10:
                        raise AssertionError("query banks disagree on selection evidence")
                    js_alternate = alternate_bundle.js
                    reason = 0 if js_alternate >= 0.1 else 3
                else:
                    reason = 2
            block_context.append(block)
            block_core_index.append(core_index)
            block_index.append(candidate_index)
            block_seed.append(this_block_seed)
            block_ell.append(ell)
            block_js_primary.append(js_primary)
            block_js_alternate.append(js_alternate)
            block_reason.append(reason)
            if reason == 0:
                eligible_rank = len(passing_blocks)
                block_eligible_rank.append(eligible_rank)
                passing_blocks.append(block)
                passing_ells.append(ell)
            else:
                block_eligible_rank.append(-1)
            if len(passing_blocks) == required_blocks:
                break

        if len(passing_blocks) < required_blocks:
            reason = 1
            rank = -1
        elif float(np.std(passing_ells[1:])) < min_within_group_sd:
            reason = 2
            rank = -1
        else:
            reason = 0
            rank = len(selected)
            selected.append(
                ContextGroup(
                    sigma=covariance,
                    graph=graph,
                    params=parameters,
                    core=core,
                    reference=passing_blocks[0],
                    continuations=np.stack(passing_blocks[1:], axis=0),
                )
            )
        core_reason.append(reason)
        core_acceptance_rank.append(rank)
        if len(selected) == n_groups:
            break

    if len(selected) != n_groups:
        raise RuntimeError(
            f"INCONCLUSIVE_IDENTIFIABILITY: accepted {len(selected)} of {n_groups} "
            f"groups within {max_core_candidates} core candidates"
        )
    accepted_ids = np.flatnonzero(np.asarray(core_reason) == 0)
    accepted_ranks = np.asarray(core_acceptance_rank)[accepted_ids]
    if not np.array_equal(accepted_ranks, np.arange(n_groups)):
        raise AssertionError("accepted cores are not the first ranked passing cores")
    if len(np.unique(core_seed)) != len(core_seed) or len(np.unique(block_seed)) != len(block_seed):
        raise AssertionError("candidate seed collision")
    selection = {
        "selection_mode": np.asarray(1, dtype=np.int8),
        "selection_max_core_candidates": np.asarray(max_core_candidates, dtype=np.int32),
        "selection_max_blocks_per_core": np.asarray(max_blocks_per_core, dtype=np.int32),
        "selection_min_within_group_sd": np.asarray(min_within_group_sd, dtype=np.float64),
        "candidate_core_sigma": np.stack(core_sigma),
        "candidate_core_graph": np.asarray(core_graph, dtype=np.int8),
        "candidate_core_params": np.asarray(core_params, dtype=np.float64),
        "candidate_core_context": np.stack(core_context),
        "candidate_core_seed": np.asarray(core_seed, dtype=np.uint64),
        "candidate_core_reason": np.asarray(core_reason, dtype=np.int8),
        "candidate_core_acceptance_rank": np.asarray(core_acceptance_rank, dtype=np.int32),
        "candidate_block_context": np.stack(block_context),
        "candidate_block_core_index": np.asarray(block_core_index, dtype=np.int32),
        "candidate_block_index": np.asarray(block_index, dtype=np.int16),
        "candidate_block_seed": np.asarray(block_seed, dtype=np.uint64),
        "candidate_block_ell": np.asarray(block_ell, dtype=np.float64),
        "candidate_block_js_primary": np.asarray(block_js_primary, dtype=np.float64),
        "candidate_block_js_alternate": np.asarray(block_js_alternate, dtype=np.float64),
        "candidate_block_reason": np.asarray(block_reason, dtype=np.int8),
        "candidate_block_eligible_rank": np.asarray(block_eligible_rank, dtype=np.int16),
    }
    return selected, selection


def generate_panel(
    *,
    commit_sha: str,
    query_banks: np.ndarray,
    n_groups: int,
    n_continuations: int,
    out_path: Path,
    interior_selected: bool = False,
    max_core_candidates: int = 2_000,
    max_blocks_per_core: int = 512,
    min_within_group_sd: float = 0.25,
    scientific: bool = False,
    run_lock_sha256: str | None = None,
):
    started = time.perf_counter()
    if interior_selected:
        groups, selection = _select_interior_groups(
            commit_sha=commit_sha,
            query_banks=query_banks,
            n_groups=n_groups,
            n_continuations=n_continuations,
            max_core_candidates=max_core_candidates,
            max_blocks_per_core=max_blocks_per_core,
            min_within_group_sd=min_within_group_sd,
        )
    else:
        rng = np.random.default_rng(derive_seed(commit_sha, "groups"))
        groups = [generate_group(rng, n_continuations=n_continuations) for _ in range(n_groups)]
        selection = {
            "selection_mode": np.asarray(0, dtype=np.int8),
            "selection_max_core_candidates": np.asarray(0, dtype=np.int32),
            "selection_max_blocks_per_core": np.asarray(0, dtype=np.int32),
            "selection_min_within_group_sd": np.asarray(0.0, dtype=np.float64),
            "candidate_core_sigma": np.empty((0, 2, 2), dtype=np.float64),
            "candidate_core_graph": np.empty(0, dtype=np.int8),
            "candidate_core_params": np.empty((0, 3), dtype=np.float64),
            "candidate_core_context": np.empty((0, 20, 2), dtype=np.float64),
            "candidate_core_seed": np.empty(0, dtype=np.uint64),
            "candidate_core_reason": np.empty(0, dtype=np.int8),
            "candidate_core_acceptance_rank": np.empty(0, dtype=np.int32),
            "candidate_block_context": np.empty((0, 10, 2), dtype=np.float64),
            "candidate_block_core_index": np.empty(0, dtype=np.int32),
            "candidate_block_index": np.empty(0, dtype=np.int16),
            "candidate_block_seed": np.empty(0, dtype=np.uint64),
            "candidate_block_ell": np.empty(0, dtype=np.float64),
            "candidate_block_js_primary": np.empty(0, dtype=np.float64),
            "candidate_block_js_alternate": np.empty(0, dtype=np.float64),
            "candidate_block_reason": np.empty(0, dtype=np.int8),
            "candidate_block_eligible_rank": np.empty(0, dtype=np.int16),
        }
    sigma = np.stack([group.sigma for group in groups])
    graph = np.asarray([group.graph for group in groups], dtype=np.int8)
    params = np.asarray(
        [[group.params.beta, group.params.b_root, group.params.b_effect] for group in groups],
        dtype=np.float64,
    )
    core = np.stack([group.core for group in groups])
    reference = np.stack([group.reference for group in groups])
    continuations = np.stack([group.continuations for group in groups])
    base_contexts = np.concatenate([core, reference], axis=1)
    target_contexts = np.concatenate(
        [
            np.broadcast_to(core[:, None, :, :], (n_groups, n_continuations, 20, 2)),
            continuations,
        ],
        axis=2,
    )

    bank_count, query_count = query_banks.shape
    shape_core = (bank_count, n_groups, query_count, 100)
    shape_target = (bank_count, n_groups, n_continuations, query_count, 100)
    f0_core = np.empty(shape_core, dtype=np.float64)
    f1_core = np.empty_like(f0_core)
    f0_base = np.empty_like(f0_core)
    f1_base = np.empty_like(f0_core)
    f0_target = np.empty(shape_target, dtype=np.float64)
    f1_target = np.empty_like(f0_target)
    js_core = np.empty((bank_count, n_groups), dtype=np.float64)
    js_base = np.empty_like(js_core)
    js_target = np.empty((bank_count, n_groups, n_continuations), dtype=np.float64)
    ell_core_by_bank = np.empty_like(js_core)
    ell_base_by_bank = np.empty_like(js_core)
    ell_target_by_bank = np.empty_like(js_target)

    for bank_index, bank in enumerate(query_banks):
        oracle = GridOracle(bank, quadrature=15)
        for group_index in range(n_groups):
            core_bundle = oracle.evaluate(core[group_index])
            base_bundle = oracle.evaluate(base_contexts[group_index])
            ell_core_by_bank[bank_index, group_index] = core_bundle.ell
            ell_base_by_bank[bank_index, group_index] = base_bundle.ell
            f0_core[bank_index, group_index] = core_bundle.f0
            f1_core[bank_index, group_index] = core_bundle.f1
            f0_base[bank_index, group_index] = base_bundle.f0
            f1_base[bank_index, group_index] = base_bundle.f1
            js_core[bank_index, group_index] = core_bundle.js
            js_base[bank_index, group_index] = base_bundle.js
            for continuation_index in range(n_continuations):
                target_bundle = oracle.evaluate(target_contexts[group_index, continuation_index])
                ell_target_by_bank[bank_index, group_index, continuation_index] = target_bundle.ell
                f0_target[bank_index, group_index, continuation_index] = target_bundle.f0
                f1_target[bank_index, group_index, continuation_index] = target_bundle.f1
                js_target[bank_index, group_index, continuation_index] = target_bundle.js
        del oracle

    if np.max(np.abs(ell_core_by_bank[0] - ell_core_by_bank[1])) > 1e-10:
        raise AssertionError("query bank changed core log evidence")
    if np.max(np.abs(ell_base_by_bank[0] - ell_base_by_bank[1])) > 1e-10:
        raise AssertionError("query bank changed base log evidence")
    if np.max(np.abs(ell_target_by_bank[0] - ell_target_by_bank[1])) > 1e-10:
        raise AssertionError("query bank changed target log evidence")
    ell_core = ell_core_by_bank[0]
    ell_base = ell_base_by_bank[0]
    ell_target = ell_target_by_bank[0]
    w_core = expit(ell_core)
    w_base = expit(ell_base)
    w_target = expit(ell_target)
    interior_core = (w_core >= 0.05) & (w_core <= 0.95)
    interior_base = (w_base >= 0.05) & (w_base <= 0.95)
    interior_target = (w_target >= 0.05) & (w_target <= 0.95)
    js_core_both = np.all(js_core >= 0.1, axis=0)
    js_base_both = np.all(js_base >= 0.1, axis=0)
    js_target_both = np.all(js_target >= 0.1, axis=0)
    eligible_replace = (
        interior_base[:, None]
        & interior_target
        & js_base_both[:, None]
        & js_target_both
    )
    eligible_append = (
        interior_core[:, None]
        & interior_target
        & js_core_both[:, None]
        & js_target_both
    )
    eligible_replace_groups = int(np.sum(np.sum(eligible_replace, axis=1) >= 4))
    eligible_append_groups = int(np.sum(np.sum(eligible_append, axis=1) >= 4))
    if scientific:
        if not interior_selected or run_lock_sha256 is None:
            raise ValueError("scientific panels require the locked selected-interior design")
        if eligible_replace.shape != (256, 8) or not eligible_replace.all():
            raise AssertionError("scientific replace cohort is not fully eligible")

    write_numeric_npz_atomic(
        out_path,
        sigma=sigma,
        graph=graph,
        params=params,
        core=core,
        reference=reference,
        continuations=continuations,
        query_banks=query_banks,
        ell_core=ell_core,
        ell_base=ell_base,
        ell_target=ell_target,
        f0_core=f0_core,
        f1_core=f1_core,
        f0_base=f0_base,
        f1_base=f1_base,
        f0_target=f0_target,
        f1_target=f1_target,
        js_core=js_core,
        js_base=js_base,
        js_target=js_target,
        eligible_replace=eligible_replace.astype(np.uint8),
        eligible_append=eligible_append.astype(np.uint8),
        commit_sha=np.frombuffer(commit_sha.encode(), dtype=np.uint8),
        evaluation_root=np.asarray(evaluation_root(commit_sha), dtype=np.uint64),
        scientific=np.asarray(int(scientific), dtype=np.int8),
        run_lock_sha256=np.frombuffer(
            bytes.fromhex(run_lock_sha256) if run_lock_sha256 is not None else bytes(32),
            dtype=np.uint8,
        ),
        **selection,
    )
    metadata = {
        "schema_version": 1,
        "commit_sha": commit_sha,
        "n_groups": n_groups,
        "n_continuations": n_continuations,
        "eligible_replace_groups": eligible_replace_groups,
        "eligible_append_groups": eligible_append_groups,
        "interior_selected": interior_selected,
        "scientific": scientific,
        "run_lock_sha256": run_lock_sha256,
        "evaluation_root": evaluation_root(commit_sha),
        "candidate_core_count": int(len(selection["candidate_core_seed"])),
        "candidate_block_count": int(len(selection["candidate_block_seed"])),
        "panel_sha256": sha256_file(out_path),
        "panel_bytes": out_path.stat().st_size,
        "wall_seconds": time.perf_counter() - started,
        "peak_rss_bytes": _peak_rss_bytes(),
    }
    write_json_atomic(out_path.with_suffix(".json"), metadata)
    return metadata


def _contexts_from_panel(panel):
    core = panel["core"]
    base = np.concatenate([panel["core"], panel["reference"]], axis=1)
    target = np.concatenate(
        [
            np.broadcast_to(
                panel["core"][:, None, :, :],
                (
                    panel["core"].shape[0],
                    panel["continuations"].shape[1],
                    panel["core"].shape[1],
                    2,
                ),
            ),
            panel["continuations"],
        ],
        axis=2,
    )
    return core, base, target


def golden_replay(panel: dict, registry: dict, *, fleet_guard: bool = True):
    core, base, target = _contexts_from_panel(panel)
    sample = target.reshape(-1, target.shape[2], 2)[:64]
    if sample.shape[0] < 4:
        raise ValueError("golden replay needs at least four target contexts")
    commit = bytes(panel["commit_sha"].tolist()).decode("ascii")
    permutation = np.random.default_rng(
        derive_seed(commit, "guard:row-permutation")
    ).permutation(sample.shape[1])
    identities = (
        [(seed, step) for seed in range(16) for step in (0, 12_000)]
        if fleet_guard
        else [(0, 0)]
    )
    max_batch_error = 0.0
    max_permutation_error = 0.0
    records = []
    for seed, step in identities:
        record = expanded_checkpoint_record(registry, seed, step)
        model = load_registered_checkpoint(record)
        for bank_index, queries in enumerate(panel["query_banks"]):
            first = predict_probabilities(model, sample, queries, batch_size=64)
            second = predict_probabilities(model, sample, queries, batch_size=64)
            if not np.array_equal(first, second):
                raise AssertionError("production replay was not byte-identical")
            batch_one = predict_probabilities(model, sample, queries, batch_size=1)
            batch_error = float(np.max(np.abs(batch_one - first)))
            shuffled = predict_probabilities(
                model, sample[:, permutation], queries, batch_size=64
            )
            permutation_error = float(np.max(np.abs(first - shuffled)))
            max_batch_error = max(max_batch_error, batch_error)
            max_permutation_error = max(max_permutation_error, permutation_error)
            records.append(
                {
                    "seed": seed,
                    "step": step,
                    "bank_index": bank_index,
                    "max_batch_size_error": batch_error,
                    "max_row_permutation_error": permutation_error,
                }
            )
        del model
    if max_batch_error > 1e-6:
        raise AssertionError("fleet batch-size guard exceeded the locked tolerance")
    if max_permutation_error > 1e-6:
        raise AssertionError("fleet row-permutation guard exceeded the locked tolerance")
    return {
        "byte_identical": True,
        "max_batch_size_error": max_batch_error,
        "max_row_permutation_error": max_permutation_error,
        "identities_checked": len(identities),
        "banks_checked": 2,
        "contexts_checked": int(sample.shape[0]),
        "records": records,
        "unused_core_shape": list(core.shape),
        "unused_base_shape": list(base.shape),
    }


def _validate_probabilities(name: str, value: np.ndarray, shape: tuple[int, ...]) -> None:
    if value.shape != shape or value.dtype != np.float32:
        raise ValueError(f"{name} has the wrong shape or dtype")
    if not np.isfinite(value).all() or np.any(value < 0) or np.any(value > 1):
        raise ValueError(f"{name} is not a finite probability tensor")
    if not np.allclose(value.sum(axis=-1), 1.0, atol=1e-6, rtol=0):
        raise ValueError(f"{name} does not normalize")
    if not np.any(value > 0):
        raise ValueError(f"{name} is an all-zero arm")


def _validate_prediction_shard(
    shard: dict,
    *,
    core_count: int,
    continuation_count: int,
    queries: np.ndarray,
    seed: int,
    step: int,
    bank_index: int,
    checkpoint_sha256: str,
    panel_sha256: str,
    scientific: bool,
) -> None:
    required = {
        "p_core",
        "p_base",
        "p_target",
        "query_bank",
        "checkpoint_sha256",
        "panel_sha256",
        "seed",
        "step",
        "bank_index",
        "scientific",
    }
    if set(shard) != required:
        raise ValueError(f"prediction shard schema mismatch: {sorted(set(shard) ^ required)}")
    base_shape = (core_count, len(queries), 100)
    _validate_probabilities("p_core", shard["p_core"], base_shape)
    _validate_probabilities("p_base", shard["p_base"], base_shape)
    _validate_probabilities(
        "p_target",
        shard["p_target"],
        (core_count, continuation_count, len(queries), 100),
    )
    if not np.array_equal(shard["query_bank"], queries):
        raise ValueError("prediction query bank mismatch")
    if bytes(shard["checkpoint_sha256"].tolist()).hex() != checkpoint_sha256:
        raise ValueError("prediction checkpoint hash mismatch")
    if bytes(shard["panel_sha256"].tolist()).hex() != panel_sha256:
        raise ValueError("prediction panel hash mismatch")
    if (
        int(shard["seed"]) != seed
        or int(shard["step"]) != step
        or int(shard["bank_index"]) != bank_index
        or int(shard["scientific"]) != int(scientific)
    ):
        raise ValueError("prediction shard identity mismatch")


def score_checkpoints(
    *,
    panel_path: Path,
    registry_path: Path | None,
    out_dir: Path,
    seeds: list[int] | None = None,
    steps: list[int] | None = None,
    scientific: bool = True,
):
    started = time.perf_counter()
    panel = load_numeric_npz(panel_path)
    root = repository_root()
    if scientific:
        verify_panel_lock(panel)
        locked_registry = (root / "config" / "checkpoint_registry.json").resolve()
        if registry_path is not None and registry_path.resolve() != locked_registry:
            raise ValueError("scientific scoring must use the locked checkpoint registry")
        registry_path = locked_registry
        seeds = list(range(16))
        steps = [0, 12_000]
        validations = validate_locked_validations(root, query_banks=panel["query_banks"])
        enforce_cost_gate(validations["artifacts/validation/smoke_budget.json"])
    elif registry_path is None or seeds is None or steps is None:
        raise ValueError("smoke scoring requires an explicit registry, seeds, and steps")
    assert registry_path is not None and seeds is not None and steps is not None
    registry = load_checkpoint_registry(registry_path)
    golden = golden_replay(panel, registry, fleet_guard=scientific)
    core, base, target = _contexts_from_panel(panel)
    target_flat = target.reshape(-1, target.shape[2], 2)
    out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    computed = 0
    panel_hash = sha256_file(panel_path)
    for seed in seeds:
        for step in steps:
            record = expanded_checkpoint_record(registry, seed, step)
            model = load_registered_checkpoint(record)
            for bank_index, queries in enumerate(panel["query_banks"]):
                path = out_dir / f"pred_s{seed:02d}_step{step:05d}_bank{bank_index}.npz"
                if path.exists():
                    existing = load_numeric_npz(path)
                    _validate_prediction_shard(
                        existing,
                        core_count=len(core),
                        continuation_count=target.shape[1],
                        queries=queries,
                        seed=seed,
                        step=step,
                        bank_index=bank_index,
                        checkpoint_sha256=record["sha256"],
                        panel_sha256=panel_hash,
                        scientific=scientific,
                    )
                else:
                    p_core = predict_probabilities(model, core, queries, batch_size=64)
                    p_base = predict_probabilities(model, base, queries, batch_size=64)
                    p_target = predict_probabilities(model, target_flat, queries, batch_size=64)
                    p_target = p_target.reshape(
                        len(core), target.shape[1], len(queries), 100
                    )
                    write_numeric_npz_atomic(
                        path,
                        p_core=p_core,
                        p_base=p_base,
                        p_target=p_target,
                        query_bank=np.asarray(queries, dtype=np.float64),
                        checkpoint_sha256=np.frombuffer(
                            bytes.fromhex(record["sha256"]), dtype=np.uint8
                        ),
                        panel_sha256=np.frombuffer(
                            bytes.fromhex(panel_hash), dtype=np.uint8
                        ),
                        seed=np.asarray(seed, dtype=np.int16),
                        step=np.asarray(step, dtype=np.int32),
                        bank_index=np.asarray(bank_index, dtype=np.int8),
                        scientific=np.asarray(int(scientific), dtype=np.int8),
                    )
                    _validate_prediction_shard(
                        load_numeric_npz(path),
                        core_count=len(core),
                        continuation_count=target.shape[1],
                        queries=queries,
                        seed=seed,
                        step=step,
                        bank_index=bank_index,
                        checkpoint_sha256=record["sha256"],
                        panel_sha256=panel_hash,
                        scientific=scientific,
                    )
                    computed += 1
                records.append(
                    {
                        "seed": seed,
                        "step": step,
                        "bank_index": bank_index,
                        "path": path.name,
                        "size": path.stat().st_size,
                        "sha256": sha256_file(path),
                    }
                )
            del model
    expected_identities = {
        (seed, step, bank) for seed in seeds for step in steps for bank in (0, 1)
    }
    observed_identities = {
        (record["seed"], record["step"], record["bank_index"]) for record in records
    }
    if observed_identities != expected_identities or len(records) != len(expected_identities):
        raise AssertionError("prediction fleet is incomplete or duplicated")
    if scientific and len(records) != 64:
        raise AssertionError("scientific scoring must produce exactly 64 shards")
    expected_names = {record["path"] for record in records}
    actual_names = {path.name for path in out_dir.glob("pred_*.npz")}
    if actual_names != expected_names:
        raise ValueError("prediction directory contains a stale or missing shard")
    ledger = {
        "schema_version": 1,
        "scientific": scientific,
        "commit_sha": bytes(panel["commit_sha"].tolist()).decode("ascii"),
        "panel": panel_path.name,
        "panel_sha256": panel_hash,
        "run_lock_sha256": bytes(panel["run_lock_sha256"].tolist()).hex(),
        "registry_sha256": sha256_file(registry_path),
        "golden": golden,
        "records": records,
        "computed_shards": computed,
        "wall_seconds": time.perf_counter() - started,
        "peak_rss_bytes": _peak_rss_bytes(),
    }
    write_json_atomic(out_dir / "prediction_ledger.json", ledger)
    return ledger


def main(argv=None):
    configure_determinism(0)
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    panel_parser = subparsers.add_parser("panel")
    panel_parser.add_argument("--out", type=Path, required=True)
    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("--panel", type=Path, required=True)
    score_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "panel":
        commit, lock_hash, lock = verify_run_lock()
        validations = validate_locked_validations()
        enforce_cost_gate(validations["artifacts/validation/smoke_budget.json"])
        settings = lock["settings"]
        metadata = generate_panel(
            commit_sha=commit,
            query_banks=load_locked_query_banks(),
            n_groups=settings["groups"],
            n_continuations=settings["continuations"],
            out_path=args.out,
            interior_selected=True,
            max_core_candidates=settings["max_core_candidates"],
            max_blocks_per_core=settings["max_blocks_per_core"],
            min_within_group_sd=settings["min_within_group_sd"],
            scientific=True,
            run_lock_sha256=lock_hash,
        )
        verify_panel_lock(load_numeric_npz(args.out))
        print(json.dumps(metadata, sort_keys=True))
    else:
        ledger = score_checkpoints(
            panel_path=args.panel,
            registry_path=None,
            out_dir=args.out,
            scientific=True,
        )
        print(
            json.dumps(
                {
                    "computed_shards": ledger["computed_shards"],
                    "records": len(ledger["records"]),
                    "wall_seconds": ledger["wall_seconds"],
                    "peak_rss_bytes": ledger["peak_rss_bytes"],
                    "golden": ledger["golden"],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
