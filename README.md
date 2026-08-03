# PFN-DAG forensic verification

This repository is an independent, fail-closed rerun of the most essential PFN-DAG Phase-2 claim. It tests whether changes in a frozen PFN output coordinate track exact conditional evidence changes on a deliberately selected, identifiable-interior AL40 replace-10 regime.

It does not test whether a Transformer implements Bayes, whether attention is the relevant mechanism, whether evidence is sufficient, or whether the result generalizes beyond the 32 bundled checkpoint hashes.

## Scientific design

The primary panel contains 256 shared 20-row cores. For each core, the oracle-only selector retains the first nine 10-row blocks that satisfy exact posterior-interior and two-bank JS separation gates. The first block is the same-length baseline and the next eight are repeated continuations. Selection uses no PFN output.

The confirmatory response is

```text
delta_ell = ell(core union continuation) - ell(core union baseline)
delta_g   = g(core union continuation)   - g(core union baseline)
```

Inference uses a within-core slope and a crossed model-seed by core bootstrap. Both frozen query banks must agree. The only primary incompatibility endpoint is a slope interval wholly on the same side outside `[0.8, 1.2]` on both banks. Full gates and licensed wording are in `PREREG.md`.

## What is bundled

- independent generator, oracle, coordinate estimator, statistics, and decision code under `src/`;
- exact scalar fixtures and fail-closed regression tests under `tests/`;
- 32 content-addressed base AL40 checkpoints under `artifacts/checkpoints/`;
- four original training-code snapshots and the legacy Stage-1 oracle snapshot;
- frozen query-bank calibration metadata, both-bank validation records, and a measured selected-interior cost smoke;
- platform and installed-distribution fingerprints for the local macOS arm64 scientific runtime.

Checkpoint provenance is limited. The file hashes are exact and portable within this repository, but the complete online training-stream lineage was not available. Claims therefore apply to these files only.

## Environment

The executed scientific runtime is CPython 3.11.7 on macOS arm64 with deterministic CPU PyTorch. Direct requirements are listed in `environment/requirements-lock.txt`. `environment/installed-distributions.json` additionally fingerprints each installed distribution's `RECORD` file and the Python executable. This is a local-runtime lock, not a cross-platform container.

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -r environment/requirements-lock.txt
python -m pip install -e .
python -m pytest -q
```

## Rebuild validation artifacts

Run from the repository root with the locked Python interpreter.

```bash
python -m pfn_dag_verify.validation instrument --query-bank config/query_bank.json --bank primary --out artifacts/validation/instrument_primary.json
python -m pfn_dag_verify.validation instrument --query-bank config/query_bank.json --bank sensitivity --out artifacts/validation/instrument_sensitivity.json
STAGE1_SRC=artifacts/source_snapshots python -m pfn_dag_verify.legacy_compare --legacy-file artifacts/legacy/stage1_functional_law.py --query-bank config/query_bank.json --bank primary --out artifacts/validation/legacy_oracle_primary.json
STAGE1_SRC=artifacts/source_snapshots python -m pfn_dag_verify.legacy_compare --legacy-file artifacts/legacy/stage1_functional_law.py --query-bank config/query_bank.json --bank sensitivity --out artifacts/validation/legacy_oracle_sensitivity.json
python -m pfn_dag_verify.validation coverage --datasets-per-slope 500 --bootstraps 1000 --out artifacts/validation/bootstrap_coverage.json
python -m pfn_dag_verify.smoke --out artifacts/validation/smoke_budget.json
python -m pfn_dag_verify.run_lock_builder
```

The run lock hashes the plan, harness, query bank, checkpoint registry, runtime records, and all six required validation files. Commit the resulting tree before scientific evaluation. Every scientific stage rejects a dirty tree or a run-lock mismatch.

## Execute the scientific run

```bash
RUN="runs/scientific-$(git rev-parse --short HEAD)"
mkdir -p "$RUN"
python -m pfn_dag_verify.evaluation panel --out "$RUN/panel.npz"
python -m pfn_dag_verify.evaluation score --panel "$RUN/panel.npz" --out "$RUN/predictions"
python -m pfn_dag_verify.analysis derive --panel "$RUN/panel.npz" --predictions "$RUN/predictions" --out "$RUN/derived"
python -m pfn_dag_verify.seal --run-dir "$RUN"
python -m pfn_dag_verify.analysis summarize --run-dir "$RUN"
```

Scoring writes no scientific estimates. The summary can be computed only after all 64 prediction shards and all 64 derived shards pass semantic checks and the replay tree is sealed. A stale panel, checkpoint, query bank, shard, ledger, validation record, runtime, or commit causes a nonzero exit.

## Result status

The pre-run artifacts are locally verified. The final scientific claim ledger and raw replay bundle are added only after the preregistered one-shot run completes. External publication or a GitHub push is not performed automatically.
