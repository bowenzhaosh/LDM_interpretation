# PFN-DAG forensic verification

This repository is an independent, fail-closed rerun of the most essential PFN-DAG Phase-2 claim. It tests whether changes in a frozen PFN output coordinate track exact conditional evidence changes on a deliberately selected, identifiable-interior AL40 replace-10 regime.

It does not test whether a Transformer implements Bayes, whether attention is the relevant mechanism, whether evidence is sufficient, or whether the result generalizes beyond the 32 bundled checkpoint hashes.

## Current verification status

- Phase-2 induced-coordinate claims remain unadjudicated. The native mapping
  qualification failed its preregistered gate, so that readout cannot support
  either a positive or a negative mechanism claim.
- The separate Phase-1 oracle qualification passed its finite-panel version-3
  gates at truncation 16,384. Raw arrays, manifests, independent verification,
  and replay metadata are archived under
  `campaigns/phase1_ordering_20260803/oracle_qualification_v3/` and tagged
  `phase1-ordering-qualification-v3-result`.
- The first confirmatory rerun targets the narrower output-level claim that the
  archived d4 fleet eventually exploits predictive information associated
  with causal ordering. Its preregistration, checkpoint registry, held Slurm
  launcher, numerical-clearance rules, and independent raw verifier are frozen
  by `phase1-ordering-confirmation-v1-fix1`. The original v1 attempt failed
  before any checkpoint scoring because a harness guard required bitwise
  covariance symmetry; its complete failure record is archived under
  `campaigns/phase1_ordering_20260803/ordering_confirmation_v1_attempt1_failed/`.
  No result is claimed until the repaired attempt completes and its raw archive
  passes post-run audit.

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
- frozen query-bank calibration metadata, both-bank validation records, a full-fleet fixed-production-shape validation, and a measured selected-interior cost smoke;
- platform and installed-distribution fingerprints for the local macOS arm64 scientific runtime.

Checkpoint provenance is limited. The file hashes are exact and portable within this repository, but the complete online training-stream lineage was not available. Claims therefore apply to these files only.

## Environment

The executed scientific runtime is CPython 3.11.7 on macOS arm64 with deterministic CPU PyTorch. Direct requirements are listed in `environment/requirements-lock.txt`. `environment/installed-distributions.json` additionally fingerprints each installed distribution's `RECORD` file and the Python executable. This is a local-runtime lock, not a cross-platform container. Archive verification uses a fresh source clone and the same locked local interpreter; it does not claim reconstruction on a new machine.

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
python -m pfn_dag_verify.validation batch-shape --query-bank config/query_bank.json --registry config/checkpoint_registry.json --out artifacts/validation/batch_shape.json
python -m pfn_dag_verify.smoke --out artifacts/validation/smoke_budget.json
python -m pytest -q
# After AUDIT.md records all five dispositions as READY_V3
python -m pfn_dag_verify.readiness_builder
python -m pfn_dag_verify.run_lock_builder
```

The readiness builder removes caller-supplied pytest selectors, collects the explicit `tests/` tree, requires every collected test to pass, and binds the output hash. The runtime check verifies the Python binary, imported package origins, and every non-cache payload listed by the locked NumPy, SciPy, scikit-learn, and PyTorch distributions. The run lock hashes the plan, harness, query bank, checkpoint registry, runtime records, all seven required validation files, per-lens audit evidence, and the machine-readable `READY_V3` attestation. Commit the resulting tree before scientific evaluation. Every scientific stage rejects a dirty tree or a run-lock mismatch.

## Qualify the native output coordinate first

The sealed version-3 science run found that synthetic mixture fixtures pass while native PFN predictions do not yet have a validated scalar coordinate. `MAPPING_QUALIFICATION_PREREG.md` defines the prospective bridge test. It is intentionally evidence-blind: it saves and checks coordinate/KL agreement, endpoint-segment residuals, two-bank agreement, and raw inference replay tensors, but never computes an evidence-response slope or reconstruction score.

After committing a clean tree, run the one-shot qualification:

```bash
python -m pfn_dag_verify.mapping_qualification panel
python -m pfn_dag_verify.mapping_qualification score
python -m pfn_dag_verify.mapping_qualification verify
python -m pfn_dag_verify.qualification_seal seal
```

Panel creation atomically records the first attempt as the annotated Git tag `mapping-qualification-attempt-v1` before drawing data. A failed gate returns `FAILED_NATIVE_MAPPING` and makes `score` exit 2. That is a completed scientific result, not a crashed job. `verify` still validates a failed artifact from raw arrays. The sealing command creates a content-addressed tar with the complete raw run, exact source/checkpoint Git bundle, attempt tag, replay instructions, and a verified fresh-source replay in the same locked local runtime.

Do not generate another induced-coordinate scientific panel unless this qualification returns `QUALIFIED`. A failure says that this readout cannot presently adjudicate Bayesian compatibility. It does not say that the checkpoints are non-Bayesian.

## Execute the scientific run

```bash
RUN="runs/scientific-$(git rev-parse --short=7 HEAD)"
mkdir -p "$RUN"
python -m pfn_dag_verify.evaluation panel --out "$RUN/panel.npz"
python -m pfn_dag_verify.evaluation score --panel "$RUN/panel.npz" --out "$RUN/predictions"
python -m pfn_dag_verify.analysis derive --panel "$RUN/panel.npz" --predictions "$RUN/predictions" --out "$RUN/derived"
python -m pfn_dag_verify.seal --run-dir "$RUN"
python -m pfn_dag_verify.analysis summarize --run-dir "$RUN"
```

Scoring first writes `pre_score_guard.json`, which records all full-fleet production-shape checks even when a guard fails. It writes no scientific estimates. `score_progress.json` begins with that persisted guard cost, and it and `derive_progress.json` accumulate resource use across safely resumed shard attempts. The canonical summary can be computed only after all 64 prediction shards and all 64 derived shards pass semantic checks and the replay tree is sealed. The sealed tar includes an exact-commit Git bundle and Gitless restoration instructions. Restored archives use the separate `analysis replay` command, which writes a noncanonical replay summary and cannot issue `LOCALLY_VERIFIED`. The smoke storage projection includes the measured Git bundle and tracked repository tree; final sealing enforces the actual tar-file size. A stale panel, checkpoint, query bank, shard, ledger, validation record, runtime, archive, or commit causes a nonzero exit.

## Result status

The version-2 stream at commit `d0b049d` stopped at its pre-score batch guard and produced no prediction shard or scientific verdict. Version 3 requires a new commit-derived stream. The final scientific claim ledger and raw replay bundle are added only after that one-shot run completes. External publication or a GitHub push is not performed automatically.
