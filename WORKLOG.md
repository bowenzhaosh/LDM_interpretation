# WORKLOG — Oracle-precision pilot development

*Running log of the oracle-precision pilot build (Phase 0-1). Each entry:
timestamp, commit, action, result, next licensed action.*

## 2026-08-04 — Phase 0 forensic inventory (COMPLETE)

- Commit `88d8dfc` (main), clean tree. FIX2 = `INCONCLUSIVE_PHASE1_INSTRUMENT`.
- Located the 400-row nested oracle panel (`join/nested_half_raw.npz`); verified
  row alignment with `panel/inputs/C_d0_b*` + `N_d0_b*` exactly (draw 0,
  stream<200, C=200 + N=200).
- Exact prior documented: log_sd ~ U(log0.6, log1.5), rho ~ U(0.3,0.8), signs
  Rademacher, uniform on the box in native coords, PD + validity (all 24
  orderings |beta|<=1.5, b in [0.3,1.3]) at ~7.3% acceptance.
- Sizing probe: posterior predictive has intrinsic per-particle logp variance
  ~0.32 nat -> full gate needs ~16k effective particles for the dominant
  ordering; ablated gate ~700/ordering. Continuous-prior oracle FEASIBLE.
- Wrote STATUS.md, ORACLE_PRECISION_PILOT_DESIGN.md (draft v0.1).

## 2026-08-04 — Phase 1 estimator build (IN PROGRESS)

Bugs found and fixed during estimator development (all on synthetic context
886_000_010, C prior):

1. SMC evidence incremental logZ used the unweighted mean; fixed to the
   weighted increment `logsumexp(logw + db*ll) - logsumexp(logw)`.
2. Prior normalization: the frozen prior is uniform in LOG_sd (sd log-uniform),
   but `native_to_z`/`z_to_native` treated sd as uniform on [0.6,1.5]. The
   z-coordinate for the sd dimension was wrong, corrupting the prior density in
   z and the likelihood mapping. FIXED: z = logit((log_sd - LOG_SD_LO)/(span)).
3. Ordering permutation in `_params_for_torch`: `S[..., pi][..., :, pi]`
   permutes only the last axis (columns twice, rows not at all); the frozen
   numpy fleet uses `S[:, pi][:, :, pi]` (rows then columns). For identity
   orderings this is invisible; for non-identity orderings it corrupted the
   likelihood. FIXED in both `pilot_smc._params_for_torch` and
   `pilot_ais._params_for`. Verified all 24 orderings now match the numpy fleet
   to <1e-10.
4. Cholesky robustness: batch Cholesky fails entirely if one matrix is
   numerically marginal; `log_likelihood_batch` now processes in chunks with
   per-chunk failure handling.
5. AIS mode-finder prior sign: `_target_value` used `-log(P_VALID_MC)` (+2.57)
   instead of `-NEGLOG_P_VALID` (-2.57). FIXED.

Verified results (with the fixes above, synthetic context, ordering 0 and 19):
- SMC logZ matches the unbiased prior-proposal IS (identity ordering: -128.04
  vs -128.00; non-identity: -144.12 vs -144.00) and the SMC's own
  thermodynamic-integration estimate (within 0.06 nat).
- The AIS (defensive adaptive IS, mode-centered t proposal) has a persistent
  ~5.4-nat evidence bias across all tested proposals (nu 2.5-50, eps 0.1-0.8,
  covariance inflation 1-5x). The AIS machinery is verified correct on a
  finite-support fixture (converges to exact enumeration). The evidence bias is
  attributed to heavy-tail finite-sample importance-sampling under-estimation
  for this concentrated posterior; PSIS attempts to correct it were not yet
  successful.
- The AIS self-normalized PREDICTIVE is unbiased (~0.004-0.02 nat per-row error
  at N=50k), suggesting the predictives may be usable even if the raw evidence
  is biased.

## Next licensed action

- Confirm the AIS evidence bias constancy across the 24 orderings
  (`order_bias.py`, running).
- If the bias is not constant at the frozen precision, the pilot's
  SMC-versus-AIS endpoint agreement will fail -> FAILED_ORACLE_METHOD_AGREEMENT
  -> Branch B (exact finite-prior wind tunnel), per the design doc.
- Proceed to Phase 2 fixtures to validate the SMC thoroughly and characterize
  the AIS before freezing.
