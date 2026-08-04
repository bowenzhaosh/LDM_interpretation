# Oracle precision pilot — adversarial code audit

Status: **audit dispositions recorded before 400-row evaluation.**

Three adversarial code audits were run on 2026-08-04 against the frozen pilot
estimators (`pilot_shared`, `pilot_smc`, `pilot_mcmc`, `pilot_ais`,
`pilot_score`). Every objection and its disposition is recorded below. The
attempt tag `phase1-oracle-precision-pilot-v1` precedes any panel estimate;
code fixes after the tag are recorded as amendments and re-frozen before the
first estimate.

## Audit 1 — SMC estimator (`pilot_smc.py`)

| # | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| 1 | MAJOR | Recorded `incremental_log_normalizers` computed after the `logw` update, so every entry was 0.0 (the `logZ` field was correct). | FIXED: record the increment before the `logw` update. Guard: `sum(incremental_log_normalizers) == logZ` (verified: -128.1412 == -128.1412). |
| 2 | MAJOR | Conditional-ESS temperature bisection used unweighted increments, over-estimating the weighted CESS and over-stepping beta. | FIXED: weighted CESS `n (sum w e^{d l})^2 / (sum w e^{2 d l})` in the bisection. |
| 3 | MINOR | `torch.rand` for sign flips and acceptance lacked `dtype` (float32). | FIXED: `dtype=torch.float64` on both. |
| 4 | MINOR | `thermodynamic_integration` substituted `means[0]` for the beta=0 endpoint. | FIXED: record `prior_mean_ll` (E_prior[logL]) at initialization and use it for the first interval. |
| 5 | MINOR | `order_predictive` did not filter invalid/zero-weight particles. | FIXED: filter `w > 0` before the quadrature loop. |
| 6 | SOUND | Resampling, rejuvenation MH (z-space Jacobian handled in the prior density; symmetric proposals), and the `logZ` accumulator were verified correct. | No action. |

## Audit 2 — MCMC + TI estimator (`pilot_mcmc.py`)

| # | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| 1 | BLOCKING | The beta=0 TI chain was warm-started from the posterior mode, but the target is the exact prior (the integrand is steepest there and the mode is not in the prior bulk), biasing E_0[logL]. | FIXED: `mcmc_evidence_ti` now initializes the beta=0 chain from exact prior samples; the scorer's per-ordering TI already did. |
| 2 | MAJOR | No ESS/quality gate on the MCMC chains; `n_effective` counted raw states. | ADDED: a post-chain finiteness gate and a cross-chain mean-ll sanity check in the TI loop; the scorer validates predictive normalization and observed-bin mass. |
| 3 | MINOR | Non-diminishing adaptive proposal (Roberts-Rosenthal condition not met). | ACCEPTED for the pilot: adaptation stabilizes; documented as a caveat for the predictive. |
| 4 | MINOR | Cholesky try/except marks a whole chunk -inf (inconsistent with the mode-finder and predictive paths). | ACCEPTED: the validity filter catches marginal matrices before the likelihood; the same pattern is used by the SMC. |
| 5 | MINOR | `betas` array trusted; per-beta seed `seed + int(b*1000)` could collide for spacing < 0.001. | FIXED: assert `betas[0] < 1e-3`, `betas[-1] == 1`, and unique `round(beta*1e6)`; per-beta seed uses an integer ladder index. |
| 6 | MINOR | `find_mode` re-created RNGs per iteration and a successful sign flip did not set `improved`. | ACCEPTED: affects initialization only; the beta=0 prior start makes the mode-finder non-load-bearing for the evidence. |

## Audit 3 — outcome blindness and data integrity (`pilot_shared.py`, `pilot_score.py`)

| # | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| 1 | BLOCKING | The scorer paired inputs (contexts) with labels (outcome bins) positionally without verifying row alignment; a mispaired label set would silently produce wrong NLLs. | FIXED: per-shard `row_key_sha256`/ROW_KEYS equality checks against the label files (hard fail on mismatch), matching `phase1_join`. |
| 2 | MAJOR | No panel provenance/hash checks. | FIXED: verify each opened shard's sha256 against `panel_manifest.json` when present; assert the exact frozen 400-row identity (C rows 0..199, N rows 3201..3400) and that the selection equals the stored `nested_half_mask`. |
| 3 | MAJOR | The 1e-300 floor silently capped observed-bin NLLs. | FIXED: hard error when the observed-bin predictive mass is <= 0 or non-finite, matching the oracle convention. |
| 4 | MAJOR | Diagnostics (logZ, ESS, acceptance, probability vectors) were dropped at save time. | FIXED: persisted `smc_logZ`, `smc_ess`, `smc_accept`, `smc_full/ablated_probability`, and the MCMC equivalents in `smc_raw.npz`. |
| 5 | MINOR | The label shard path was not passed through `assert_path_allowed`; the path guard is a substring check. | FIXED: guard the label path too; documented the substring-check limitation. |
| 6 | MINOR | `assert_no_forbidden_imports` is a one-shot name scan with a dead `torch.load` fragment. | ACCEPTED as a tripwire; the actual import graph is clean (pilot modules import only `pilot_shared` + stdlib + numpy + torch + the hash-pinned generator). |
| 7 | MINOR | `FORBIDDEN_SEED_NAMESPACES` was defined but never enforced. | FIXED: `score_pilot` raises if `seed_root` falls in a forbidden namespace. |
| 8 | MINOR | No output finiteness/normalization guard before save. | FIXED: hard checks on every predictive and order posterior before save. |

## Post-fix verification

- The full fixture suite (12 tests) passes after all fixes.
- SMC logZ after the weighted-CESS fix still matches the unbiased prior-IS
  (identity ordering: -128.14 vs -128.60 within MC error) and its own TI.
- `sum(incremental_log_normalizers) == logZ` (the audit guard).
- The outcome-blindness guard refuses forbidden paths and imports; the scorer
  hard-fails on misaligned labels, wrong row counts, and zero observed-bin
  mass.

Disposition: **REVISED-AND-RE-VERIFIED.** The frozen attempt tag is re-created
at the post-fix commit before the first 400-row estimate.
