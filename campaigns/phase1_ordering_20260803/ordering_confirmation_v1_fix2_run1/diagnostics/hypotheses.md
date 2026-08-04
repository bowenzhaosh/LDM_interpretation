# Hypothesis ladder

1. **Nested-half row misalignment. KILLED.** All 400 row hashes are unique and
   present in the full archive. Row metadata, input hashes, and full-oracle NLL
   values match exactly.
2. **PFN batch or context-order instability moved the endpoint. KILLED.** The
   production guard passed all 18 checkpoints. The direct combined
   context-roll plus batch-8 maximum was `3.814697265625e-5`, below the frozen
   `8e-5` per-NLL envelope, and join propagated that envelope to every decision.
3. **Join-only arithmetic or reporting error. KILLED.** The independent raw
   verifier reproduced the same decision and its joined raw/summary hashes
   match the sealed artifacts.
4. **The prior-atom importance sampler is under-resolved. KEPT.** At three
   million atoms, the causal full-oracle median ESS is only `16.38`, with
   34.05% of rows below 10. On the fixed convergence panel, absolute
   full-versus-half error is negatively associated with log ESS (Spearman
   `-0.267` for C and `-0.440` for N); causal rows with ESS at most 10 have mean
   absolute error `0.10275` nats.
5. **A modest uniform atom-count increase is sufficient. NOT ESTABLISHED.**
   The observed paired-difference standard errors (`0.00828` full C and
   `0.00384` ablated C) are far above the `0.0005` gate, while worst-row ESS is
   near one. The next discriminating test should compare an improved proposal
   or exact/conditional oracle against the frozen estimator on a small fixed
   subset before another full campaign. Merely tuning atom count until the
   result passes is prohibited.
