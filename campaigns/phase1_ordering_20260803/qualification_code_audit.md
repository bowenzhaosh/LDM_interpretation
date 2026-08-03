# Phase-1 cross-bank qualification pre-run code audit

Status: **PASS after repair**. No qualification context or scientific PFN
endpoint had been generated when this audit closed.

## Independent lenses

| Lens | Initial verdict | Blocking or major finding | Repair | Final verdict |
| --- | --- | --- | --- | --- |
| Metric validity | PASS | None | None | PASS |
| Leakage and contamination | PASS | None | Freeze commit and tag before generating contexts | PASS |
| Configuration, fallback, and transaction integrity | UNSOUND | Missing identity fields could compare as the string `None`; raw and partial arrays were not cryptographically bound to the marker identity | Require both identity objects, recompute their digest, bind every raw and partial identity row, and cross-check config, fleet, and commit fields | PASS |
| Reproducibility and portability | UNSOUND | CPU model, CPU features, and active OpenBLAS execution were absent from the runtime lock; seeded atom generation could vary at covariance-boundary decisions | Fix OpenBLAS to one thread, fingerprint CPU and active NumPy runtime, hash each full atom bank, and require a shared 4,096-atom determinism canary across jobs | PASS |
| Numerical stability and determinism | NEEDS REVISION | The join did not reject duplicated full atom banks | Require three pairwise-distinct full-bank SHA-256 values | PASS |

The observed-bin log-probability comparison was also changed to fail closed on
zero or non-finite values. It no longer applies a silent probability floor.

## Executable guards

Regression tests cover missing marker identity objects, mismatched raw identity,
cross-node canary disagreement, duplicated full atom banks, a zero observed-bin
probability, and first-passing-candidate selection. The complete repository test
suite passed on the frozen pre-run tree: `101 passed`.

The runtime-lock preflight was job `158825` on `a100-2207`; it completed with
exit code `0:0`. Its CPU/BLAS-aware fingerprint is
`44394126ccf9b4d75eec6d1c3d691f0ab34fbbd50c579deed3abdcb06296636a`.

## Gate

The three qualification jobs may start only from a clean, tagged commit. All
three are constrained to `a100-2207`, and the join must independently verify
their marker inventories, common canary hash, distinct full-bank hashes, and
the frozen statistical gates before confirmation is unlocked.
