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

## 2026-08-04 — Cluster validation debugging (IN PROGRESS)

- Built the pilot scorer (`pilot_score.py`, sharded), the cluster launcher
  (`cluster/submit_oracle_precision_pilot.py`, rsync + Slurm), and the
  independent raw-array verifier (`pilot_verify.py` with shard join).
- Cluster issues found and fixed:
  1. `-I -S` interpreter flags broke PYTHONPATH/site-packages; removed.
  2. Seed-namespace guard was too aggressive (a broad 880M entry swallowed the
     pilot 886M root); made the forbidden seeds precise with a 1e6 window.
  3. Manual `CUDA_VISIBLE_DEVICES` override corrupts the GPU allocation;
     removed (Slurm's gres plugin sets it).
- The three adversarial audits (SMC, MCMC-TI, outcome-blindness) were applied;
  dispositions in ORACLE_PRECISION_PILOT_AUDIT.md. Key fixes: weighted-CESS
  schedule, incremental-logZ recording order, prior-init beta=0 TI, input-label
  row alignment + provenance checks, hard NLL floor checks, diagnostics
  persistence.
- Validation job 160413 running (1 row, full config).

## Next
- Confirm validation passes; launch the 40-shard pilot.
- Join + verify + report; record the scientific verdict (expectation:
  FAILED_ORACLE_METHOD_AGREEMENT given the evidence-precision bottleneck,
  routing to Branch B).

## 2026-08-04 — Cluster validation + full pilot launch (compute constraint)

- Cluster validation at the reduced config measured ~1 h per frozen row
  (bottleneck: the validity check runs 24 orderings of Cholesky per particle
  per likelihood evaluation; the MCMC-TI and SMC both call it).
- Full 400-row pilot at the frozen precision therefore needs ~40 h wall
  (~400 GPU-hours) on the owned condo-cse5100 partition — a genuine compute
  constraint, reported per the prompt.
- The 40-shard pilot was launched and persists on the cluster at
  /engrfs/project/class/zhao.b/pfn-dag-oracle-precision-pilot-v1/run
  (SUBMISSION.json records all job IDs).
- STATUS.md updated with the current state and the expected verdict
  (FAILED_ORACLE_METHOD_AGREEMENT -> Branch B).

## Next (when the pilot shards complete)
- Join the shards (pilot_verify.join_shards), run the independent verifier
  (pilot_verify.verify), generate the HTML report (pilot_report.render).
- Record the scientific verdict; proceed to Branch B (exact finite-prior
  causal wind tunnel): design the exact finite library, train PFNs on it, and
  measure predictive capture vs graph-posterior fidelity.

## 2026-08-04 — Full pilot launched (40 shards)

- All 40 shards submitted and running on condo-cse5100 (SUBMISSION.json on the
  cluster records all job IDs). Expected wall time ~40 h at the reduced config.
- Caveat found and fixed: the launcher's rsync `--delete` wiped the remote
  `run/` directory (the local repo does not contain it), which aborted the
  in-progress 1-row validation job mid-write (job 160561). Fixed by excluding
  `run/` from the rsync. Do NOT re-sync while the pilot is running.
- When the shards complete: `pilot_verify.join_shards` then `pilot_verify.verify`
  then `pilot_report.render`. Expected verdict FAILED_ORACLE_METHOD_AGREEMENT
  -> Branch B.

## 2026-08-05 — Pilot re-launch after aggregation bug

- The first-wave shards crashed ~1h in on a list-vs-array bug in the pilot
  scorer's MCMC aggregation: `mcmc_logz` was a list, so `mcmc_logz - max(...)`
  raised TypeError. Fixed by `mcmc_logz = np.asarray(mcmc_logz)` before the
  full/ablated/order-posterior combination. Verified locally (aggregation
  normalizes to 1) and on the cluster (line 241 has the fix).
- Cancelled the crashed shards, cleaned the remote run dir, re-synced (the
  launcher now excludes `run/`), and re-submitted all 40 shards (jobs recorded
  in SUBMISSION.json: 40).
- Pilot running again; hourly cron monitors completion.
