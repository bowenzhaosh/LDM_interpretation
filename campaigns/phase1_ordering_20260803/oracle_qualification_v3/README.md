# Phase-1 oracle qualification v3 result

Status: `QUALIFICATION_PASS`

The corrected Phase-1 oracle is numerically qualified at truncation
`T=16,384` under the preregistered v3 truncation and quadrature gates. This
licenses the subsequent frozen-checkpoint confirmation. It does not establish
that a PFN uses causal ordering, that the oracle is exact, or that the observed
finite-panel bounds hold population-wide.

## Frozen provenance

- Qualification source: commit
  `fc0b8eb48c75f7c0d1dc208b1d344d663b16baf3`, annotated tag
  `phase1-ordering-qualification-v3`.
- Independent verifier: commit
  `04429ae5713dff0f101d842b8e6b4890c7f4e668`, annotated tag
  `phase1-ordering-qualification-v3-verifier-fix1`.
- Joined raw SHA-256:
  `a4bc89e5f22f41764ddefb310bc2fb67dc291c0d0156949c1840841549915317`.
- Artifact-manifest SHA-256:
  `8d2266f595da827044b345053d20bff2aa50fcb9cc236e77312f4122f9228f9e`.
- Independent decision: `INDEPENDENT_RAW_RECOMPUTATION_PASS`.

The first verifier job (`158994`) failed before scientific replay because its
source-inventory parser assumed a `/source/` path component. The repair maps
absolute paths to unique frozen source suffixes and pins the already-produced
joined hashes. No raw array, threshold, candidate order, or scientific metric
changed. The repaired verifier job (`159238`) completed successfully.

## Registered results

| Candidate | JS exceedances | max-bin log-probability exceedances | Worst p95 JS | Worst p95 absolute log-probability change |
| ---: | ---: | ---: | ---: | ---: |
| 8,192 | 0 | 12 | `5.81046e-6` | `0.00500004` |
| 16,384 | 0 | 0 | `2.50488e-7` | `0.00104459` |

All three 32/128 versus 64/256 quadrature comparisons passed. The worst
observed C-prior values were maximum JS `4.4327e-10`, maximum-bin absolute
log-probability change `1.85193e-4`, reference-weighted absolute
log-probability change `5.0435e-5`, and ordering-value change `1.70123e-4`.

The zero-exceedance simultaneous Clopper-Pearson upper bound recorded by the
verifier is `0.0420103770` per registered family. The candidate and reference
share contexts and atom banks within each paired comparison, so this is a
finite-panel stability qualification rather than an absolute-accuracy claim.

## Jobs and artifacts

- Bank shards `158988`, `158989`, and `158990`: completed on A100 GPUs.
- Join `158993`: completed.
- Original verifier `158994`: failed on provenance-path parsing.
- Repaired verifier `159238`: completed.

`bank*/run/` contains each calibration array, both checkpointable partial
arrays, completion marker, atom-bank record, and summary. `joined/` contains
the sealed combined raw array, summary, and completion marker. `logs/`, GPU
telemetry, and `sacct.txt` preserve execution evidence. Both the repaired
verifier filename and the canonical `independent_verification.json` contain
the same bytes.

From the repository root, verify the archive with:

```bash
shasum -a 256 -c campaigns/phase1_ordering_20260803/oracle_qualification_v3/ARTIFACT_SHA256SUMS
```

Replay the standalone decision into a fresh output path with:

```bash
PYTHONPATH=src python -m pfn_dag_verify.phase1_qualification_verify \
  --root campaigns/phase1_ordering_20260803/oracle_qualification_v3 \
  --repo . \
  --commit fc0b8eb48c75f7c0d1dc208b1d344d663b16baf3 \
  --verifier-commit 04429ae5713dff0f101d842b8e6b4890c7f4e668 \
  --verifier-tag phase1-ordering-qualification-v3-verifier-fix1 \
  --protocol-version 3 \
  --out /tmp/phase1-qualification-v3-replay.json
```
