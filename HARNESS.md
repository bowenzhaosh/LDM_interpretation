# Harness specification

## Scientific target

The first run validates the independent oracle and multi-query mixture coordinate, then tests whether frozen base AL40 checkpoint outputs have induced-coordinate differences compatible with exact evidence differences on a same-length replace-10 design. The 20-to-30 append and paired step-0 versus step-12,000 results are secondary descriptions.

## Success conditions

1. Every exact, tempered, label-swap, mean-pooling, determinism, leakage, checkpoint, and decision-rule assertion passes.
2. Scalar and vectorized oracle paths agree to the locked tolerance.
3. Scientific evaluation uses only a clean audited commit, a frozen query bank, strict checkpoint hashes, and commit-derived one-shot seeds.
4. Raw numeric shards are atomic, hash-addressed, and sufficient to recompute every summary value.
5. The final claim uses only wording licensed by `PREREG.md`.

## Guard mapping

| Risk | Executable guard |
| --- | --- |
| Wrong graph or endpoint orientation | exact fixture and label-swap invariance |
| Broken reverse endpoint query dependence | multi-query endpoint variation assertion |
| Probability/logit confusion | normalization and exact-mixture recovery |
| Clipping plausible failures | retain raw weight and boundary flag; decision gate |
| Wrong conditional evidence target | repeated-continuation replace and append identities |
| Prefix-conditioned confound | within-group slope and cyclic continuation-swap canary |
| Shared-context pseudo-replication | crossed seed-by-group bootstrap tests |
| Stale or wrong checkpoint | committed SHA-256 registry and strict schema loader |
| Hidden fallback | negative tests require nonzero failure |
| Optional stopping | fixed 256 by 8 panel |
| Summary without replay data | numeric-only raw shards and content-tree manifest |

## Cost controls

The smoke run measures end-to-end CPU time, peak memory, and compressed bytes per context. The locked full-run limits are 45 minutes, 16 GB RAM, and 2 GB compressed raw output. The runner stops before unblinding if extrapolated cost exceeds a limit.

## Execution record

This section is append-only once tests begin. It records exact commands, failures, fixes, smoke timing, audit disposition, and final run identifiers.

### 2026-08-03 pre-run record

- The first adversarial audit returned `UNSOUND` on metric validity, numerical determinism, configuration plumbing, stale-artifact handling, and replay portability. Scientific checkpoint evaluation was not started.
- Repairs added the exact two-stage unsigned 64-bit seed chain, identical resampling streams across query banks, a mandatory 256 by 8 selected-interior panel, complete validation semantics, full 32-checkpoint by two-bank batch and row-order guards, strict resume schemas, exact 64-shard ledgers, a content-tree sealing stage, and pre-unblinding cost enforcement.
- A cross-family plan review was attempted through the configured helper and exited nonzero without output. This did not waive any local gate.
- The final selected-interior smoke used 8 accepted groups by 8 continuations. It processed 22 core candidates and 8,089 block candidates in 21.06 seconds. The full end-to-end smoke took 22.33 seconds. With the locked extrapolation and 25 percent safety factor, projected scientific resources were 1,652.80 seconds wall time, 1,652,031,488 bytes peak RSS, and 774,993,440 bytes compressed raw output. All were below the 2,700-second, 16-GB, and 2-GB caps.
- Primary and sensitivity instrument validation passed. Maximum scalar/vector oracle errors were at most `1.11e-16`; maximum coordinate weight error was at most `1.45e-15`; maximum KL weight error was at most `4.00e-8`.
- The repository snapshot of the legacy Stage-1 oracle matched the independent oracle on both banks. Maximum endpoint error was at most `8.61e-16` and evidence error was zero.
- Fresh crossed-bootstrap validation used 500 datasets per slope and 1,000 bootstrap draws per dataset. Coverage was 0.940 at slope 0.8, 0.948 at slope 1.0, and 0.944 at slope 1.2. Every Wilson interval contained 0.95.
- The first legacy replay command failed because the copied snapshot also imports `d5c_analyze.py`. That dependency was copied into `artifacts/source_snapshots/`, added to the content-addressed registry, and both legacy checks then passed.
- After the final repairs, `python -m pytest -q` reported 32 passed tests. Four targeted audit rechecks returned `SOUND` with no blocking or major finding. The tree is ready for the immutable pre-run commit.
