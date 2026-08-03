# Phase-1 calibration pre-run code audit

Scope: oracle-only truncation calibration for the d=4 output-level ordering-use
replication. This audit does not validate a PFN checkpoint or a Phase-2 induced
evidence coordinate.

Final blocker-only verdicts after repair:

- leakage / calibration-confirmatory separation: PASS
- metric validity: PASS
- numerical stability and determinism: PASS
- config plumbing, transaction, and dead-arm checks: PASS
- reproducibility and portability: PASS after the exact snapshot is committed
  and submitted from a clean checkout

Repairs made before launch include direct comparison of every truncation
candidate with the frozen 32,768-atom reference; float64 accumulated context
likelihoods; deterministic ascending-atom-index tie breaking at the top-k
cutoff; a complete frozen production protocol map; an A100 binary/runtime
fingerprint; source and wrapper hashes; device/runtime-bound partials; an
exclusive writer lease with serialized stale recovery; and a verified
`COMPLETE.json` marker as the sole completion authority.

The registered regression suite includes generator parity, Gaussian null,
quadrature alignment, both full and ablated convergence gates, production-field
mutation rejection, runtime-inventory self-hashing, deterministic cutoff ties,
single-writer leasing, and concurrent stale-recovery exclusion.
