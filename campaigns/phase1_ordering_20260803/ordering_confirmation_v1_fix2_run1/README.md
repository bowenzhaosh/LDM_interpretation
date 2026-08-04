# Phase-1 ordering confirmation, FIX2 run 1

This directory contains the archived campaign output and audit package for the
first successfully executed essential confirmation campaign. The scientific
decision is
`INCONCLUSIVE_PHASE1_INSTRUMENT`. It does not verify or refute PFN use of
causal-ordering information.

All seven Slurm jobs completed with exit code zero. The independent verifier
recomputed the raw result and returned
`INDEPENDENT_CONFIRMATION_RAW_RECOMPUTATION_PASS`. The model replay guard also
passed all 3,201 panel rows per checkpoint, for 57,618 checkpoint-row
evaluations, plus 72 stress rows. The blocking failure is the
preregistered oracle-convergence gate.

Key endpoints:

| Quantity | Estimate | Interval | Registered outcome |
| --- | ---: | ---: | --- |
| Ordering value under C | 0.075718 | one-sided lower 0.064180 | manipulation check passes |
| Ordering value under N | approximately 0 | approximately +/- 6.6e-17 | exact null passes |
| Direct C deficit at 120k | -0.010804 | [-0.022328, 0.000724] | fails direct rule |
| C-minus-N deficit at 120k | -0.025802 | [-0.038691, -0.012884] | passes descriptively |
| C full-oracle 3M-minus-1.5M | -0.015597 | [-0.032741, -0.000473] | convergence fails |
| C ablated 3M-minus-1.5M | -0.002751 | [-0.010216, 0.004608] | convergence fails |

The oracle diagnostic found severe importance-weight degeneracy under C. The
three-million-atom full-oracle ESS has median 16.38, minimum 1.01, and 34.05%
of rows below ESS 10. That points to an under-resolved prior-proposal oracle,
not a checkpoint-loading or report-only failure.

Start with [REPORT.html](REPORT.html), then inspect
`join/confirmation_summary.json`, `join/confirmatory_raw.npz`, and
`verification/independent_verification.json`. The adversarial synthesis is in
`AUDIT_REPORT.md`, the claim check is in `CLAIM_LEDGER.md`, and the forensic
ladder is under `diagnostics/`.
`ARTIFACT_SHA256SUMS` seals every
archived file except itself and ignored Python cache files. `checkpoints/`
contains the 18 model states and six training sidecars. The original frozen
cluster registry remains at repository `config/phase1_checkpoint_registry.json`;
`PORTABLE_CHECKPOINT_REGISTRY.json` maps the same hashes to a repository-relative
local root. It is a portability inventory, not a replacement for the frozen
production config.

The remote transfer can be independently rechecked with
`verify_transfer_tree.py`; its exact 8,021-line source inventory is
`REMOTE_TRANSFER_MANIFEST.jsonl`.

Source: commit `9c6a3732993ea13557279ec8d330b7d1a076e63f`, annotated tag
`phase1-ordering-confirmation-v1-fix2`, attempt identity
`ec282fc468de2f42f01dc11c4b6733a5d926796a5929e96e549f52fcfa9c91b8`.
