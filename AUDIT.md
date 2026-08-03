# Pre-run adversarial audit disposition

No scientific checkpoint estimate was generated before this audit and repair cycle completed.

## Initial gate

Four independent lenses returned `UNSOUND` before execution:

| Lens | Blocking issue |
| --- | --- |
| Metric validity | arbitrary validation substitution and an infeasible unselected interior panel |
| Numerical determinism | wrong seed chain, bank-specific resampling, incomplete fleet guard, and no executable cost gate |
| Configuration plumbing | unrestricted scientific CLI settings, dead run-lock code, and stale shard reuse |
| Replay portability | dirty-code bypass, incomplete ledgers, no sealed tree, absolute checkpoint paths, and no immutable commit |

## Repairs

- The scientific CLI obtains every dimension, threshold, query bank, registry, and resource cap from one run lock.
- The run lock hashes the preregistration, harness, audit disposition, all experiment source, all guard tests, runtime records, registry, query bank, and all six validation artifacts.
- The unsigned 64-bit evaluation root and every child stream follow the exact two-stage preregistered hash rule. Bootstrap and permutation resamples are identical across query banks.
- Oracle-only selection yields exactly the first 256 passing cores and first nine passing blocks per core. Every accepted and rejected candidate is archived.
- All 32 checkpoints, both steps, and both query banks are checked for byte-identical repeat evaluation, batch-size agreement, and row-order invariance.
- Prediction and derived resumes require exact schemas, identities, hashes, query banks, shapes, normalization, and finiteness. Ledgers require exactly 64 unique shards at each stage.
- Validation loading recomputes every numerical pass predicate and verifies the producer-source hash.
- A selected-interior 8 by 8 end-to-end smoke is mandatory, and projected plus measured resource caps fail closed.
- Finalization verifies the live replay tree, creates a deterministic content-addressed tar archive containing every recorded repository and run file, fsyncs it, and rehashes every archive member before summary generation.

## Repair recheck

The metric-validity and numerical-determinism lenses returned `READY`, with only a nonterminal NMAE quantile-convention mismatch. That mismatch was repaired and given an exact expanded-weight regression test.

The configuration and replay lenses found four final plumbing issues: source files were absent from the run lock, numeric validation fields were not independently re-adjudicated, the summary output override could overwrite sealed inputs, and no recoverable archive was created. All four were repaired.

All four final targeted rechecks returned `SOUND` with no blocking or major finding. The configuration lens verified the exact 49-file lock set and validation tamper guards. The replay lens verified archive creation, archive-member hashing, and recovery after a live-source mutation. The numerical and metric lenses verified the common NMAE convention to `1.11e-16`. The final pre-commit suite reported 32 passed tests.

Disposition: `READY` to create the run lock and immutable scientific commit.
