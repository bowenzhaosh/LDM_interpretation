# Oracle-precision pilot — claim ledger

Document checked: the pilot preregistration (`ORACLE_PRECISION_PILOT_PREREG.md`), design (`ORACLE_PRECISION_PILOT_DESIGN.md`), audit (`ORACLE_PRECISION_PILOT_AUDIT.md`), and the frozen config (`config/oracle_precision_pilot_v1.json`).

Evidence checked: all 40 shards' summary.json + smc_raw.npz, the joined raw array (400 rows), the independent verifier output, the 12-passing fixture tests, the three adversarial code audits, the cluster submission record, and the outcome-blindness guards.

| ID | Claim | Verdict | Evidence and qualification |
| --- | --- | --- | --- |
| C1 | The pilot is outcome-blind: it never loads PFN checkpoints, reads PFN predictions, or computes deficit/gap/Delta. | SUPPORTED | The path guard (`pilot_shared.assert_path_allowed`) and import guard (`assert_no_forbidden_imports`) were active; all panel inputs and labels passed hash/manifest verification; no forbidden path was opened. |
| C2 | The pilot consumed exactly the frozen 400-row nested panel without regeneration, reordering, filtering, or mutation. | SUPPORTED | Per-shard row-key alignment verified against labels; the nested-half mask matched the panel's stored mask; the joined row-id set is exactly C rows 0..199 and N rows 3201..3400. |
| C3 | The SMC and MCMC+TI are genuinely independent estimators. | SUPPORTED | They have separate likelihood assemblies, proposal code, evidence estimation, predictive aggregation, and decision logic. The defensive AIS module (non-qualifying) is a separate third path. |
| C4 | The annealing SMC matches the unbiased prior-proposal IS and its own thermodynamic integration. | SUPPORTED | On development synthetic contexts (seed 886_000_000), the incremental SMC logZ matches prior-IS to within 0.05 nat; the independent TI cross-check agrees within 0.7 nat; all 24 ordering likelihoods match the frozen numpy fleet to <1e-10. |
| C5 | The order-posterior gate fails by orders of magnitude. | SUPPORTED | The 400-row join and independent verifier give: C order-posterior JS median 0.131 (gate < 1e-4 → FAIL by 1300×), p95 0.583 (gate < 1e-3 → FAIL by 580×). |
| C6 | The SMC-vs-MCMC full-predictive NLL agreement gate fails | SUPPORTED | C full NLL median 0.048 (gate < 0.002 → FAIL by 24×); max 2.25 (gate < 0.02 → FAIL by 110×). |
| C7 | The SMC-vs-MCMC ablated-predictive NLL agreement gate fails | SUPPORTED | C ablated NLL median 0.010 (gate < 0.002 → FAIL by 5×); max 0.70 (gate < 0.02 → FAIL by 35×). |
| C8 | The row-catastrophe gate fails. | SUPPORTED | 15 of 200 C rows have full NLL difference > 0.5 nat. |
| C9 | All 100-bin predictive vectors are finite, nonnegative, and normalized. | SUPPORTED | Independent normalization check on all four predictive arrays (SMC full/ablated, MCMC full/ablated) confirms 0 bad rows. |
| C10 | The order-posterior precision bottleneck is the binding failure mechanism. | SUPPORTED AS INFERENCE | The SMC and MCMC both produce valid, normalized predictives — they converge in distribution — but the order posterior weights (which weight the full mixture) disagree systematically. The order marginal likelihood integrand is pathologically steep near beta=0 (development finding documented in the design doc §12), making the order posterior the most precision-sensitive quantity. |
| C11 | The pilot does not retroactively change the FIX2 verdict. | SUPPORTED | The FIX2 `INCONCLUSIVE_PHASE1_INSTRUMENT` is immutable. The oracle-precision pilot is instrument development on the same 400-row panel; its verdict is `FAILED_ORACLE_METHOD_AGREEMENT`, not a qualification. |
| C12 | The expected next stage is Branch B: the exact finite-prior causal wind tunnel. | SUPPORTED AS RECOMMENDATION | The continuous-prior oracle cannot reach the frozen ±0.0005-nat evidence precision. The next decisive experiment builds a small finite library of valid covariance/SEM atoms, trains PFNs on that exact finite prior, and measures whether predictive capture of causal-ordering value can exceed exact graph-posterior fidelity. |

No external papers or web sources are cited. All internal links resolve within the repository.

Final tally: 11 factual/interpretive claims supported, one recommendation evidence-backed, and no remaining overstated or unsupported claim.
