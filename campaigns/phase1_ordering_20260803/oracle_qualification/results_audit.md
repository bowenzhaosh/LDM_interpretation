# Cross-bank oracle qualification results audit

Verdict: **CAVEATED QUALIFICATION PASS**

The stored raw diagnostic arrays, partial files, completion markers, and joined
result were independently rechecked. The frozen lowest-passing-candidate rule
selects 16,384 atoms against the 32,768-atom finite reference.

## Recomputed result

- 8,192 has zero JS exceedances and 16 predictor-family observed-bin
  log-probability exceedance cells. Those cells arise from eight unique `N`
  contexts measured under both the full and ablated predictors.
- 16,384 has zero exceedances in all 24 of its candidate-specific families
  under the registered 48-family multiplicity correction.
- For 16,384, the worst p95 JS is `3.43036394221233e-7`, the worst p95 absolute
  log-probability change is `0.0007094641693139669` nats, and the largest
  individual absolute log-probability change is `0.00871138` nats, below the
  strict `0.009` boundary.
- The zero-exceedance Bonferroni-adjusted one-sided 95% per-family
  Clopper-Pearson upper bound is `0.04201037701571053` for this finite panel.

## Integrity checks

The audit found no mismatch in completion-marker hashes, attempt identities,
tagged source inventories, raw-to-partial slices, or the joined raw stack. All
33 original bank/run/output/joined files checked before the accounting files
were added matched their cluster copies byte-for-byte. Slurm accounting records
jobs 158858, 158859, and 158860 as `COMPLETED` with exit `0:0` on `a100-2207`.
The independent verifier recomputes the selection without importing the
qualification runner or joiner.

## Limits and required wording

This is a truncation qualification on three fixed atom-bank/context-panel pairs.
It does not prove convergence to an exact oracle, population-wide tail control,
oracle correctness, or any PFN scientific endpoint. The archived arrays contain
derived JS and log-probability-change values rather than the underlying 100-bin
candidate/reference predictions and outcome bins, so an independent verifier
can recompute the gate but cannot reconstruct those two metrics from first
principles without rerunning the qualification.

The three jobs share the locked runtime fingerprint and reproduce the same
4,096-atom canary while producing three distinct registered full-bank hashes.
The full 3M arrays were not retained. Their hashes therefore remain tied to the
pinned-runtime generation records rather than rehashable archived bytes. The
GPU monitor inventories all six node devices and cannot identify the one UUID
assigned to each job; Slurm accounting still proves one A100 allocation per
job.

The source-only preregistration contains a stale later sentence naming 8,192,
despite its dedicated qualification rule selecting the lowest passing
candidate. The original source tag remains unchanged. A separate prospective
confirmation amendment resolves this conflict in favor of the algorithmic
selection rule before any confirmatory panel is generated.

These caveats do not change the mechanical selection of 16,384. They restrict
what the qualification itself licenses us to claim.
