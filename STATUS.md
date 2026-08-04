# PFN-DAG scientific status

*Maintained as the current authoritative status of this repository. Historical
attempt records are immutable; this file is updated only at completed gates.*

## Current state (2026-08-04)

- **Branch / HEAD:** `main` at commit `88d8dfc` (clean tree).
- **Result tags present:**
  - `phase1-ordering-confirmation-v1-fix2` (attempt source tag)
  - `phase1-ordering-confirmation-v1-fix2-results` (FIX2 result archive)
  - `phase1-ordering-qualification-v3-result`, `...-verifier-fix1`
  - `mapping-qualification-attempt-v1` and earlier lineage tags.
- **Phase-2 induced-coordinate readout:** `FAILED_NATIVE_MAPPING`
  (`MAPPING_QUALIFICATION_PREREG.md`). The current coordinate cannot support
  either a positive or a negative Bayesian-composition mechanism claim. No
  further induced-coordinate composition slopes, probes, steering, BIC, or
  TabPFN bridge runs are licensed until a prospectively qualified instrument
  exists.

## Phase-1 lineage (historical, immutable)

1. Oracle calibration `e679e74` — selected 8,192 atoms under the version-1
   (later rejected) ablated estimator. Retained only as historical lineage.
2. Cross-bank qualification `cdd541c` — rejected 8,192, selected 16,384 under
   the version-1 ablated estimator. Also superseded as a flawed estimator.
3. Qualification v2 — frozen, deliberately not executed (quadrature audit).
4. **Qualification v3 `fc0b8eb` + verifier fix `04429ae`** — PASSED
   finite-panel truncation and quadrature gates at 16,384 retained atoms
   against the 32,768 reference, 32/128 production vs 64/256 reference
   quadrature. This is the only admissible qualification.
5. **Confirmation FIX2 `9c6a373` → result `bcccc95`** — executed all seven
   stages, independent raw recomputation passed, but returned
   **`INCONCLUSIVE_PHASE1_INSTRUMENT`**.
   - Blocking failure: prior-proposal oracle convergence. Full-oracle ESS
     median 16.38, min 1.01, 34.05% of rows below 10 (3,000,000 atoms).
   - 3M-versus-1.5M oracle changes violated the frozen ±0.0005-nat gates:
     C ablated `-0.002751`, control-subtracted ablated `-0.001623`,
     C full `-0.015597`.
   - FIX2 establishes neither PFN ordering use nor an undertraining effect.
     Its favorable descriptive model-side signal is not confirmatory and cannot
     be retroactively rescued.

## Licensed next stage

The next licensed experiment is an **outcome-blind oracle-precision pilot** on
the existing archived 400-row nested oracle panel
(`campaigns/phase1_ordering_20260803/ordering_confirmation_v1_fix2_run1/join/nested_half_raw.npz`,
whose 400 contexts are the frozen `panel/inputs/C_d0_b*` + `N_d0_b*` rows with
draw 0 and stream index < 200). The pilot develops and validates two
independent posterior-targeted oracle estimators (annealed SMC primary;
defensive adaptive importance sampling independent), first on fixtures and
synthetic calibration contexts, then on the frozen 400-row panel. It is
outcome-blind: it never loads PFN checkpoints, reads PFN predictions, or uses
model deficits / FIX2 endpoints to choose methods, hyperparameters, gates, or
particle counts.

- Design doc: `ORACLE_PRECISION_PILOT_DESIGN.md`.
- Audit record: `ORACLE_PRECISION_PILOT_AUDIT.md`.
- Preregistration: `ORACLE_PRECISION_PILOT_PREREG.md` (not yet written).
- Terminal taxonomy: `QUALIFIED_ORACLE`, `FAILED_ORACLE_PRECISION`,
  `FAILED_ORACLE_METHOD_AGREEMENT`, `INCONCLUSIVE_IMPLEMENTATION`,
  `INTERRUPTED_ATTEMPT`.

A scientific confirmation may resume only if the pilot qualifies the oracle to
the frozen numerical standard (including the inherited ±0.0005-nat gates on
the direct and control-subtracted oracle changes).

## Prohibited claims (until a later experiment directly establishes them)

- "the architecture knows Bayes";
- "training erases Bayesian composition";
- "the model reads evidence but refuses to use it";
- "the model is a consistent-but-miscalibrated Bayesian";
- "a decodable direction is a causal mechanism";
- "PFNs generally exploit causal ordering."
