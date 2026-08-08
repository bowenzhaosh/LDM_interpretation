# PFN-DAG scientific status

## Completed experiments

### Phase-1 FIX2 confirmation (immutable, historical)
- Tag: `phase1-ordering-confirmation-v1-fix2-results`
- Verdict: `INCONCLUSIVE_PHASE1_INSTRUMENT`. The prior-proposal oracle failed its
  convergence gate (full-oracle ESS median 16.38 at 3M atoms). The favorable
  descriptive model-side signal is not confirmatory and cannot be retroactively
  rescued.

### Phase-2 induced-coordinate readout (immutable, historical)
- Verdict: `FAILED_NATIVE_MAPPING` (`MAPPING_QUALIFICATION_PREREG.md`).
- No induced-coordinate composition slopes, probes, steering, BIC, or TabPFN
  bridge runs are licensed until a prospectively qualified instrument exists.

### Oracle-precision pilot (2026-08-08 — sealed)
- Tag: `phase1-oracle-precision-pilot-v1-result`
- Verdict: **`FAILED_ORACLE_METHOD_AGREEMENT`**
- The two independent posterior-targeted estimators (annealed SMC and
  MCMC+thermodynamic integration) disagree on the order posterior and the full
  predictive by orders of magnitude above the frozen precision gates:
  - C order-posterior JS median 0.131 (gate < 1e-4, FAIL by 1300×)
  - C full-predictive NLL median 0.048 (gate < 0.002, FAIL by 24×)
  - 15 of 200 C rows have >0.5 nat full-NLL catastrophe
- The order marginal likelihood has a pathological integrand (steep in β near 0),
  making the order posterior the binding precision bottleneck for the
  continuous-prior oracle. Normalization and predictive regularity hold.
- Full campaign, raw arrays, independent verifier, claim ledger, and report at
  `campaigns/phase1_ordering_20260803/oracle_precision_pilot_run1/`.

## Route

The continuous-prior oracle cannot reach the frozen ±0.0005-nat evidence precision.
The next licensed stage is:

> **Branch B: exact finite-prior causal wind tunnel.** Design a small finite
> library of valid covariance/SEM atoms; train PFNs on that exact finite prior;
> measure two axes on the held-out contexts from the same exact library:
> 1. predictive competence (gap, deficit, capture of ordering value), and
> 2. posterior fidelity (order-posterior error, evidence-response calibration,
>    sequential evidence-composition error, posterior predictive error).
> The highest-value result is a reproducible regime where predictive capture > 0
> while exact graph-posterior fidelity remains poor — that would establish that
> exploiting causal structure for prediction does not imply recovering the
> Bayesian posterior over structure.

## Prohibited claims (until a later experiment directly establishes them)

- "the architecture knows Bayes"
- "training erases Bayesian composition"
- "the model reads evidence but refuses to use it"
- "the model is a consistent-but-miscalibrated Bayesian"
- "a decodable direction is a causal mechanism"
- "PFNs generally exploit causal ordering"
