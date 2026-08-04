# Oracle precision pilot — design

Status: **DRAFT v0.1 (development).** This is instrument-development design, not
a preregistration. The preregistration (`ORACLE_PRECISION_PILOT_PREREG.md`) is
written only after the estimators pass the Phase-2 fixture suite and an
adversarial code review.

## 1. Why the prior-proposal oracle failed

The FIX2 oracle scored each context by prior-proposal importance sampling over
a fixed bank of 3,000,000 covariance matrices drawn exactly from the frozen
prior:

    w(atom) ∝ p(D | atom, o),   posterior over atoms ∝ w(atom).

For a fixed ordering `o` and context `D` of 30 rows, the likelihood
`p(D | atom, o)` is concentrated on a tiny fraction of the prior mass. Across
the 3,201 causal rows the collapsed full-oracle effective sample size has
median 16.38, minimum 1.01, and 34.05% of rows below 10. The nested
3M-versus-1.5M changes then carried Monte Carlo error far above the frozen
±0.0005-nat gate (`C` ablated `-0.002751`, control-subtracted `-0.001623`,
`C` full `-0.015597`).

Root cause, per `diagnostics/hypotheses.md` and the claim ledger: the proposal
(prior) is far from the posterior; the estimator is not posterior-targeted.

## 2. What is being inferred

For each context `D` (30 rows), each prior `P ∈ {C, N}`, and each of the 24
orderings `o`, we infer the latent covariance/SEM parameter

    θ = (sd_1..sd_4, ρ_12..ρ_34, sign_12..sign_34)

whose covariance matrix is `S(θ)`, with `S_jj = sd_j^2` and
`S_jk = sign_jk ρ_jk sd_j sd_k`. This is the exact latent object of the frozen
d=4 generator.

The object we must estimate precisely is the **order-specific marginal
likelihood** `Z_o(D) = p(D | o)` and the **order-conditioned 100-bin posterior
predictive** `p(y | x_q, D, o)` for the query row `(x_q, y)`.

## 3. Exact target density

In native coordinates the frozen prior is **uniform on a box** intersected
with validity:

    p(sd, ρ, sign) = [ 1 / (log 1.5 − log 0.6)^4 ] · [ 2 ]^6 · [ 1/2 ]^6
                      · 1[sd_j ∈ [0.6,1.5]] · 1[ρ_jk ∈ [0.3,0.8]]
                      · 1[PD(S)] · 1[validity_keep(S)]

where `PD` requires the minimum eigenvalue of `S` to exceed `1e-6` and
`validity_keep` requires, for **every** one of the 24 orderings, that the
Cholesky-derived regression coefficients of the permuted covariance satisfy
`max|beta| ≤ 1.5` and each partial scale `b ∈ [0.3, 1.3]`. Measured acceptance
rate of the joint validity+PD indicator is approximately 7.3% of raw draws.

Working in `(log sd, ρ_mag, sign)` (a bijective reparameterization) the prior
density is a constant times the indicator functions — **no Jacobian is needed
in the native parameterization**. All posterior computations use this native
parameterization. The order-specific posterior target is

    π_o(θ) ∝ p(θ) · p(D | θ, o),       Z_o(D) = ∫ p(θ) p(D | θ, o) dθ.

The likelihood `p(D | θ, o)` is the product over the 30 rows of the d=4
residual density under the ordering `o`:

    residual_m = (U_o x_o)_m,   U_o = inv(Lunit_o),   b_o = partial scales.

For `C`: each residual is asymmetric-Laplace with `(a, c) = al_ac(b, r=4)`.
For `N`: each residual is Gaussian with scale `√2 b`, which makes
`p(D | θ, o)` independent of `o` (the Gaussian is closed under permutation),
so `Z_o(D) ≡ Z(D)` and the ordering value is exactly null under `N`.

## 4. How evidence and predictives are estimated

**Annealed SMC (primary).** For each `(P, D, o)` run an SMC sampler over
tempered targets

    π_t(θ) ∝ p(θ) p(D | θ, o)^{β_t},   0 = β_0 < … < β_T = 1,

with (i) adaptive temperature increments controlled by a frozen conditional-ESS
rule; (ii) a frozen systematic-resampling rule; (iii) an adaptive-covariance
random-walk Metropolis rejuvenation kernel on the continuous variables plus
sign-flip Metropolis moves, both enforcing the validity/PD indicators by
rejection (proposal with zero target mass is rejected); and (iv) independent
replicas with disjoint seed namespaces. `Z_o(D)` is the SMC normalizing-constant
estimate `log Z_o = Σ_t log(mean_i exp((β_t − β_{t−1}) ℓ_i))`. The order
posterior is `p(o | D) ∝ Z_o(D)`.

The order-conditioned predictive is

    p(y | x_q, D, o) = Σ_i w_i p(y | x_q, θ_i, o),

the SMC-weighted average of the per-particle conditional predictive, evaluated
on the frozen production 100-bin quadrature (32 interior / 128 tail nodes per
tail; the 64/256 reference grid is used only in the quadrature qualification
fixtures). Per-particle `p(y | x_q, θ_i, o)` integrates the residual density
over the outcome coordinate at each quadrature node and aggregates into the
native 100 bins exactly as the production oracle does.

**Defensive adaptive importance sampling (independent).** A second estimator
through a separate code path draws from

    q(θ) = (1 − ε) q_adaptive(θ) + ε p(θ),    ε frozen prospectively,

where `q_adaptive` is a heavy-tailed proposal fit to the posterior in the same
native parameterization (a Student-t mixture on the continuous variables times
a fitted product-Bernoulli on the sign bits). The evidence estimate is
`Z_o(D) ≈ mean_i π_o(θ_i)/q(θ_i)`; the predictive is the weighted average.
All proposal densities, mixture terms, and weights are exact (including the
logistic Jacobian of the transform if a transformed proposal coordinate is
used). The AIS module imports neither the SMC estimator, its aggregation, nor
its decision code.

## 5. Full and ordering-ablated predictives

With `p(o | D) ∝ Z_o(D)`:

    p_full(y | x_q, D)      = Σ_o p(o | D) · p(y | x_q, D, o)
    p_ablated(y | x_q, D)   = (1/24) Σ_o p(y | x_q, D, o)

The ablated predictive normalizes each order-conditioned predictive
independently (each `p(y|x_q,D,o)` is already a normalized 100-bin vector) and
mixes the 24 uniformly. Retained-mass weighting across orderings is never
reintroduced. This is the corrected ablation from the v3 qualification; it is
enforced by a regression test.

The FIX2 endpoints re-derived from these predictives are, per row,
`NLL_full = −log p_full(y_bin)`, `NLL_ablated = −log p_ablated(y_bin)`,
`V_P = mean(NLL_ablated − NLL_full)`, and the row mean `d_P`/`e_P` nested-half
changes used by the convergence gates.

## 6. How the new estimators avoid the old failure

- The proposal follows the likelihood: SMC anneals from the prior to the
  posterior with controlled conditional ESS; AIS uses a posterior-tilted
  defensive mixture. Neither relies on prior atoms landing in the posterior
  mass by chance.
- Rejuvenation mixes within the exact latent space, including the discrete
  sign variables and the validity/PD support constraints.
- Convergence is judged at the prediction and endpoint level, not by ESS
  alone (ESS is diagnostic).
- Every production estimator has an independent raw-array verifier that does
  not import the estimator's likelihood, proposal, aggregation, or decision
  implementation.

## 7. Independence map

| Component | SMC | AIS | Shared frozen substrate |
| --- | --- | --- | --- |
| Prior density / validity | own | own | `d4_generator.py` primitives |
| Likelihood assembly | own | own | `params_for`, `bin_y`, `BIN_EDGES`, `R_OF` |
| Proposal | own (anneal + MH) | own (adaptive + defensive) | — |
| Evidence estimator | SMC normalizing const | IS mean | — |
| Predictive aggregation | own | own | frozen quadrature grid definition |
| Seeds | disjoint namespace | disjoint namespace | — |
| Decision/gates | own | own | frozen thresholds in prereg |

The frozen quadrature grid and the fleet primitives are shared scientific
definitions, not estimator implementations.

## 8. Data and blindness

The pilot consumes only the frozen 400-row panel inputs
(`panel/inputs/C_d0_b*`, `panel/inputs/N_d0_b*` — the contexts and queries for
the rows with `draw_index == 0` and `stream_index < 200`) and the panel labels'
outcome bins (the observed `y` values needed for held-out log probability). It
never opens `nested_half_raw.npz`, `confirmatory_raw.npz`, any `oracle_raw.npz`,
any PFN checkpoint, or any PFN prediction file, and it never computes
`deficit`, `gap`, `Delta`, or `capture`. A software guard rejects any import of
the PFN loader and any read of those paths. Calibration of methods,
hyperparameters, gates, and particle counts uses only analytic fixtures, exact
finite-support fixtures, low-dimensional brute-force fixtures, and disjoint
synthetic calibration contexts under a **new registered seed namespace**
(`886_xxx_xxx`), never the 400-row panel.

## 9. Planned gates (frozen in the prereg)

Primary numerical gates, all evaluated on the frozen 400-row panel:

1. Independent SMC-replica agreement.
2. SMC particle-count (ladder) convergence.
3. Independent AIS-replica agreement.
4. SMC-versus-AIS agreement.
5. Prediction-level agreement: Jensen–Shannon divergence; held-out log
   probability differences; binwise log-probability differences;
   order-posterior disagreement.
6. Endpoint-level agreement for all oracle-only quantities feeding the FIX2
   direct and control-subtracted convergence checks.
7. Inherited ±0.0005-nat convergence requirement for the relevant direct and
   control-subtracted oracle changes.
8. Separate passing results for C full, C ablated, N full, N ablated.
9. A preregistered difficult subset based on the old low-ESS diagnostics,
   membership fixed before new estimates are seen.
10. No catastrophic row-level failure hidden by an aggregate mean.

Terminal taxonomy: `QUALIFIED_ORACLE`, `FAILED_ORACLE_PRECISION`,
`FAILED_ORACLE_METHOD_AGREEMENT`, `INCONCLUSIVE_IMPLEMENTATION`,
`INTERRUPTED_ATTEMPT`.

## 10. Threat model

| Threat | Control |
| --- | --- |
| Wrong prior density | β=0 fixture reproduces the exact prior sampler; prior acceptance rate regression |
| Incorrect Jacobian | native-parameterization avoids Jacobian; transformed-coordinate fixtures |
| Invalid covariance support | PD + validity enforced by rejection in every move; failure fixture |
| Discrete-sign proposal errors | sign-flip MH balance test; sign-marginal fixture |
| Order-label leakage | order-index vs permutation tested; order-relabeling fixture |
| Top-K retained-mass leakage | uniform-order-weight regression; unequal-masses fixture |
| Biased resampling | systematic resampling; particle-permutation and replay fixtures |
| Unstable evidence normalizers | log-space accumulation; tempered-likelihood fixture |
| Particle impoverishment | conditional-ESS adaptive schedule; ESS reported but never gates |
| Proposal support failure | defensive prior component in AIS; failure fixture |
| Correlated “independent” replicas | disjoint seed namespaces, disjoint batching code |
| Row misalignment | row-key/input-hash checks against the frozen manifests |
| Underflow | log-space arithmetic; float64 everywhere load-bearing |
| Quadrature mismatch | frozen production grid; quadrature qualification fixtures |
| Accidental access to PFN outputs | import guard + path guard; reviewed |
| Thresholds selected after seeing outcomes | methods/gates frozen before 400-row evaluation |
| Wrong marginal-likelihood estimator | independent AIS evidence agrees with SMC evidence |
| Posterior multimodality (sign) | sign-aware proposal + annealing; multimodality reported |

## 11. Open sizing questions (answered by development probes, not the panel)

- Per-(context, ordering) posterior concentration and required particle count
  to reach per-row predictive logp MC error ≲ 0.002 nat.
- Number of temperature steps and MH sweeps; acceptance rate.
- Total GPU-hours and shard plan (400 rows × 24 orderings × 2 priors × 2
  methods × ladder rungs × replicas).

## 12. Development findings (2026-08-04) — recorded before freezing

These findings came from synthetic development contexts (seed namespace
886_xxx_xxx), never the 400-row panel. They shaped the estimator set.

**Bugs found and fixed during development** (all corrected; regression-tested):

1. The prior is uniform in LOG_sd (sd log-uniform), but the initial
   `native_to_z`/`z_to_native` treated sd as uniform on [0.6,1.5]. The
   z-coordinate for the sd dimension was wrong, corrupting the prior density in
   z and the likelihood mapping. Fixed.
2. The ordering permutation in the torch likelihood assembly used
   `S[..., pi][..., :, pi]`, which permutes only the last axis (columns twice);
   the frozen numpy fleet uses `S[:, pi][:, :, pi]` (rows then columns). For
   identity orderings this is invisible; for non-identity orderings it
   corrupted the likelihood. Fixed in SMC and AIS; all 24 orderings now match
   the numpy fleet to <1e-10.
3. The SMC incremental log-evidence used an unweighted mean; corrected to the
   weighted increment `logsumexp(logw + db*ll) - logsumexp(logw)`.
4. Batch Cholesky fails entirely if one member is numerically marginal;
   likelihood assembly now processes in chunks with per-chunk failure handling.

**Verified results:** The SMC (primary) matches the unbiased prior-proposal
importance estimate of the order marginal likelihood for both identity and
non-identity orderings (e.g. identity -128.04 vs -128.00; non-identity -144.12
vs -144.00) and its own thermodynamic-integration estimate within 0.06 nat.
The SMC's posterior samples reach the true posterior mode.

**AIS obstruction (documented):** the defensive adaptive importance sampler's
evidence is biased low by ~5 nats (varying ~1 nat across orderings) for this
heavy-tailed posterior: the importance weights have heavy tails (khat ~0.4-0.5)
because the posterior is heavy-tailed (its entropy is ~13-15 nats vs 8.3 for a
Gaussian with the same covariance). The order posterior from the AIS disagrees
with the SMC by up to 0.12 in weight. This is a genuine mathematical
obstruction for the AIS estimator family. The AIS is retained only as a
diagnostic; it is not a qualifying estimator.

**Replacement independent estimator — MCMC + thermodynamic integration
(`pilot_mcmc.py`):** a chain-based estimator (adaptive Metropolis-Hastings,
multiple parallel chains, no resampling, no importance weights) targeting the
same order posterior. The beta=1 chain gives the posterior predictive directly;
the evidence comes from thermodynamic integration over a beta-ladder of the
posterior mean log-likelihood, with a fine ladder near beta=0 (the integrand
is steep there: E_prior[ll] ~ -313, E_post[ll] ~ -115). The MCMC predictive
matches the SMC (diff ~0.007 nat at ~180k effective samples). The MCMC-TI
evidence agrees with the SMC to ~0.5-0.7 nat with a 12-point ladder.

**Fundamental precision finding:** the order marginal likelihood Z_o(D) has a
pathological integrand (huge dynamic range; steep in beta near 0). Only the
SMC's adaptive-beta incremental estimator handles it well. Independent
estimators (AIS, and MCMC-TI at fixed ladders) cannot reach the frozen
±0.0005-nat evidence precision at feasible cost. The order posterior (which
weights the full predictive) is therefore the binding precision bottleneck of
the continuous-prior oracle.
