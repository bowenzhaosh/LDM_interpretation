# Phase-1 corrected oracle qualification v2

Status: **BLOCKED BEFORE EXECUTION; SUPERSEDED BY V3**

After this protocol was frozen but before it was committed, tagged, or run, a
numerical audit showed that its inherited 8-interior/32-tail quadrature could
move a causal ordering value by about `0.0014` nats. Version 2 is retained as a
design-stage record and must not be executed. Version 3 uses another fresh
context namespace and adds a high-order quadrature gate.

This qualification repairs a blocker found during the pre-confirmation code
audit. No confirmatory panel has been generated and no PFN checkpoint has been
evaluated under the confirmation protocol.

## Defect and corrected estimand

Version 1 formed the retained ordering-specific log weights as

`kept_log_likelihood - full_bank_log_normalizer`.

After top-K truncation, the retained masses differ by ordering. Normalizing the
result only after concatenating orderings therefore weights orderings by their
retained masses. That is not the preregistered ordering-blind reference.

Version 2 first normalizes each ordering over its own retained top-K atoms,

`kept_log_likelihood - logsumexp(kept_log_likelihood, axis=atoms)`,

then mixes all 24 orderings uniformly. A positive-control test with deliberately
unequal retained masses must assign exactly equal total probability to every
ordering. The per-ordering log normalizers must be zero within absolute error
`1e-12`.

## Frozen rerun

- Dimension 4, context size 30, priors `C` and `N`.
- Three atom banks, each containing 3,000,000 covariance draws from seeds
  `881003101`, `881003102`, and `881003103`.
- A shared 4,096-atom determinism canary from seed `881103999`.
- Fresh `C` context streams from seeds `880923000`, `880923001`, and
  `880923002`.
- Fresh `N` context streams from seeds `880933000`, `880933001`, and
  `880933002`.
- 160 contexts per prior and atom bank.
- Candidates 8,192 and 16,384, each compared directly with reference 32,768.
- The exact locked WashU A100 runtime and the existing frozen d=4 generator.

The candidate thresholds and selection rule are unchanged from version 1.
For each bank, prior, predictor, and candidate, the aggregate median and p95 JS
and observed-bin absolute log-probability changes must pass the original
10%-margin rule. In addition, there may be zero individual exceedances of
`9e-4` JS or `0.009` nats. The lowest candidate passing all 48 registered
families is selected. If neither candidate passes, confirmation stops.

## Replay archive and independent check

Each shard retains, for every prior, truncation level, and context:

- the 100-bin full predictive probability;
- the 100-bin uniformly ordering-ablated predictive probability; and
- the observed outcome-bin index.

It also retains the derived JS and observed-bin log-probability diagnostics.
It does not retain PFN outputs or compute any scientific deficit. An independent
verifier that does not import the oracle, metric, or qualification modules must
recompute normalization, nonnegativity, every JS value, every log-probability
change, every exceedance count, and the selected truncation from these arrays.
Any disagreement, missing array, stale marker, source-hash mismatch, nonfinite
value, or incomplete context invalidates the qualification.

The version-1 artifacts and result tag remain unchanged for audit history.
Version 2 receives no source or result tag because it was blocked before
execution.
