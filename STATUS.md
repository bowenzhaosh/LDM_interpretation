# PFN-DAG scientific status

*Maintained as the current authoritative status of this repository. Historical
attempt records are immutable; this file is updated only at completed gates.*

## Current state (2026-08-04)

- **Branch / HEAD:** `main`. Attempt tag `phase1-oracle-precision-pilot-v1`
  (annotated) on the post-audit commit.
- **Phase-2 induced-coordinate readout:** `FAILED_NATIVE_MAPPING`. No
  induced-coordinate composition slopes, probes, steering, BIC, or TabPFN
  bridge runs are licensed until a prospectively qualified instrument exists.
- **Phase-1 FIX2 confirmation:** `INCONCLUSIVE_PHASE1_INSTRUMENT` (immutable).
  The prior-proposal oracle failed its convergence gate (full-oracle ESS median
  16.38 at 3M atoms). FIX2 establishes neither ordering use nor undertraining.

## Oracle-precision pilot (in progress)

The licensed next stage is the outcome-blind oracle-precision pilot on the
frozen 400-row nested panel.

**Estimators (frozen, attempt tag `phase1-oracle-precision-pilot-v1`):**

1. **Annealed SMC** (`src/pfn_dag_verify/pilot_smc.py`) — primary. Verified
   correct: its order marginal logZ matches the unbiased prior-proposal IS and
   its own thermodynamic integration for identity and non-identity orderings;
   all 24 ordering likelihoods match the frozen numpy fleet to <1e-10.
2. **MCMC + thermodynamic integration** (`src/pfn_dag_verify/pilot_mcmc.py`) —
   independent. Chain-based (adaptive Metropolis-Hastings, no resampling, no
   importance weights); predictive from the beta=1 chain, evidence via a
   beta-ladder trapezoid (fine near beta=0), beta=0 chain from the exact prior.
3. **Defensive adaptive IS** (`src/pfn_dag_verify/pilot_ais.py`) — retained as
   a diagnostic only. Its evidence has a documented heavy-tail importance-weight
   obstruction (~5 nat bias, varying across orderings), making it non-qualifying.

**Key scientific finding (development, synthetic contexts):** the order
marginal likelihood `Z_o(D)` has a pathological integrand (huge dynamic range,
steep in beta near 0). Only the SMC's adaptive-beta incremental estimator
handles it well; independent estimators (AIS, and MCMC-TI at fixed ladders)
reach only ~0.5-1 nat agreement on the order posterior, far above the frozen
±0.0005-nat gate. The order posterior (which weights the full predictive) is
the binding precision bottleneck of the continuous-prior oracle.

**Cluster execution status (compute constraint):**
- Full-config smoke measured ~3 h per row; the reduced config (SMC 8192
  particles, MCMC 64 chains x 600 iterations x 7 betas, documented in
  `config/oracle_precision_pilot_v1.json`) measures ~1 h per row.
- The complete 400-row pilot therefore requires ~40 h of wall time on the
  owned `condo-cse5100` partition (~400 GPU-hours). This is a genuine compute
  constraint; the 40-shard pilot was launched and persists on the cluster at
  `/engrfs/project/class/zhao.b/pfn-dag-oracle-precision-pilot-v1/run`.
- Validation of the pipeline on one frozen row was in progress (job 160561).

**Documents:** `ORACLE_PRECISION_PILOT_DESIGN.md` (design + threat model),
`ORACLE_PRECISION_PILOT_PREREG.md` (preregistration), `ORACLE_PRECISION_PILOT_AUDIT.md`
(adversarial review dispositions), `WORKLOG.md` (running log), `config/oracle_precision_pilot_v1.json`
(frozen config), `src/pfn_dag_verify/pilot_{shared,smc,mcmc,ais,score,verify,report}.py`,
`cluster/{oracle_precision_pilot.sbatch,submit_oracle_precision_pilot.py}`,
`tests/test_pilot_fixtures.py` (12 passing fixtures).

## Expected pilot verdict and next stage

Given the evidence-precision bottleneck, the expected pilot verdict is
`FAILED_ORACLE_METHOD_AGREEMENT`, routing to **Branch B: the exact finite-prior
causal wind tunnel** (build a small finite library of valid covariance/SEM
atoms, train PFNs on that exact finite prior, and measure whether predictive
capture of causal-ordering value can exceed graph-posterior fidelity). The
highest-value possible result is a reproducible regime where predictive
capture > 0 while exact graph-posterior fidelity remains poor.

## Prohibited claims (until a later experiment directly establishes them)

- "the architecture knows Bayes";
- "training erases Bayesian composition";
- "the model reads evidence but refuses to use it";
- "the model is a consistent-but-miscalibrated Bayesian";
- "a decodable direction is a causal mechanism";
- "PFNs generally exploit causal ordering."
