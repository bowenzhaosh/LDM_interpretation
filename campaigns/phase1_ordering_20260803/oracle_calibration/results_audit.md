# Oracle calibration result audit

Verdict: **TRUSTWORTHY WITH CAVEATS** for the narrow registered finite-panel
claim.

Independent recomputation verified all `COMPLETE.json` payload hashes and
sizes, 64/64 completed contexts, finite diagnostics, no forbidden context,
label, prediction, checkpoint, or scientific-endpoint arrays, direct comparison
of both candidates with 32,768, and the first-passing selection of 8,192. Both
8,192 and 16,384 passed. The worst 8,192 p95 absolute held-out log-probability
change was 0.001788529 nats, below the strict 0.009 boundary.

The result is artifact-level verification, not an independent A100 replay. Its
32 contexts per prior and one atom bank do not establish a population-p95 or
cross-bank guarantee. A zero-exceedance sample of 32 still permits an 8.94%
one-sided 95% upper bound on the exceedance rate. For that reason, confirmation
is blocked on the separately preregistered three-bank qualification with 160
fresh contexts per prior per bank.

The exact locked preregistration blob, job ID, scheduler log, GPU identity and
trace, completion marker, independent verifier, and their hashes are anchored
in `integrity_manifest.json`. Later preregistration changes are an explicitly
post-calibration addendum and do not alter the locked run protocol.
