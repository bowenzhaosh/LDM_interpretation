# Native mapping qualification pre-run audit

Status: ready for one prospective local execution.

## Audit panel

| Lens | Final verdict | Load-bearing result |
| --- | --- | --- |
| Metric validity | SOUND | Mapping uses only coordinate/KL agreement, endpoint-segment residuals, and cross-bank agreement. Exact-evidence reconstruction and slopes are excluded. |
| Configuration plumbing | SOUND | Panel dimensions, threshold values, fleet identities, and all gates are sealed in one settings object and independently checked. |
| Numerical determinism | SOUND | Fresh verification initializes the locked runtime; all finite, replay, batch-order, and row-order guards are derived from saved tensors. |
| Leakage | SOUND | The exact 27-file protocol inventory, fixed seed root, namespace, prior-seed inventory, and context-overlap checks prevent adaptive use of the previous science panels. |
| Silent fallback/dead arm | SOUND | `score` exits 2 for a scientific failure; integrity verification and sealing preserve failed artifacts; the later science gate accepts only `QUALIFIED`. |
| Replay portability | SOUND with caveat | The archive supports a fresh-source replay under the exact local runtime. It does not claim a new-machine environment reconstruction. |
| Bias/claim semantics | AMENDMENT_JUSTIFIED | `FAILED_NATIVE_MAPPING` blocks this readout. It cannot be reported as evidence for model non-Bayesianity. |

The executable regression suite contains 80 passing tests before the attempt.

## Cross-family review

The configured DeepSeek v4-pro reviewer returned `UNSOUND` based on two claimed
blockers. Both were adjudicated as incorrect premises and retained in
`mapping_qualification_cross_family.md`:

1. It confused the archive CLI with the experiment CLI; `panel`, `score`, and
   working-directory `verify` are registered in `mapping_qualification.py`.
2. It treated same-commit qualification plus science as a path bug, although this is
   the explicit fail-closed preregistered design. The complete validation, audit
   readiness, and run lock were rebuilt before the final protocol commit.

The cross-family reviewer agreed that a failed qualification means only that the
readout is unqualified and does not falsify Bayesianity.

## Remaining provenance limitation

No GitHub push was authorized. The runner therefore creates and retains an annotated
local Git tag before panel generation, and the final content-addressed archive embeds
that tag. This establishes integrity and local chronology for this execution, but it
is not an independently protected append-only remote timestamp. The fixed seed root
makes the panel deterministic, and this audit treats the limitation as provenance
rather than a threat to the numerical result of the retained single run.

## Pre-run decision

Proceed once, retain either terminal result, and seal it. If the decision is
`FAILED_NATIVE_MAPPING`, stop all induced-coordinate science. If it is `QUALIFIED`,
the unchanged commit may proceed to the preregistered replace-10 scientific run.
