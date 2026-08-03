# Confirmation v1 fix1 attempt 2: failed before endpoints

This directory preserves the second production attempt at source commit
`2157aa08e076c90af4b715efc1f89e3b3a053e58`, annotated tag
`phase1-ordering-confirmation-v1-fix1`.

The repaired panel stage completed and sealed all 6,402 context rows. PFN job
`160021` then failed its label-free replay guard on the first frozen
checkpoint, before writing a prediction shard. The guard compared batch-64
inference with singleton and reverse-order batching. Its registered
`1e-6`-nat tolerance was smaller than ordinary float32 kernel-shape roundoff.
No joined endpoint or scientific decision was computed.

The three oracle shards had started in parallel after the panel. They were
cancelled immediately once the PFN failure was confirmed so a doomed join did
not consume GPU hours. None wrote a completed or partial oracle array. Join and
independent verification were cancelled without runtime.

Two initial label-free diagnostics followed. Job `160028` reproduced the
failing checkpoint and separated batch-shape, context-order, and repeat
effects. Job `160030` swept all 18 frozen checkpoints on the same 72
registered replay rows per model. That first sweep did not invoke the locked
runtime contract, so it is retained as diagnostic history rather than used to
set a repaired tolerance.

Jobs `160038` and `160040` reran an expanded 18-checkpoint sweep in separate
fresh processes after invoking the production attempt identity and locked
runtime checks. Both completed with identical output SHA-256
`d4f0ded169899b6cfc7054aeacdb7b05289f85b5220c5158ae102e4c05e3bc47`
under runtime fingerprint
`44394126ccf9b4d75eec6d1c3d691f0ab34fbbd50c579deed3abdcb06296636a`.
Deterministic algorithms and deterministic cuDNN were enabled, while both
TF32 flags and cuDNN benchmarking were disabled. Across this locked sweep:

- repeated batch-64 inference was bit-identical for every checkpoint;
- maximum singleton/reverse batch log-probability error was
  `2.6702880859375e-5` nats;
- maximum context-roll log-probability error was `1.9073486328125e-5` nats;
- maximum probability error was `2.17098238802782e-7`;
- maximum total variation was `5.504126464169025e-7`.

Job `160041` then evaluated every one of the 3,201 saved panel rows for every
one of the 18 frozen checkpoints, with nine shards per checkpoint. It ran
under the same locked runtime and tested repeated inference, two fixed random
row permutations, reversed rows, same-shape block permutations, batch size 8,
and both view and contiguous context-row rolls. On all 162 checkpoint-shards,
repeat and all row-permutation controls were bit-identical. The full-panel
maxima were:

- batch-size-8 log-probability error `3.4332275390625e-5` nats;
- batch-size-8 probability error `5.024417268906234e-7`;
- batch-size-8 total variation `1.996038085179163e-6`;
- context-roll log-probability error `1.9073486328125e-5` nats;
- context-roll probability error `3.0763227687469197e-7`;
- context-roll total variation `9.077932729430932e-7`.

The diagnostics opened only panel input shards. They did not open outcomes,
labels, oracle predictions, or scientific endpoints. Their exact sources and
machine-readable outputs are in `diagnostics/` and `slurm/`. Job `160027`
failed only because its first diagnostic source path was node-local; it did
not run the diagnostic.

`SUBMISSION.json`, the sealed panel, stage leases, tracebacks, telemetry,
diagnostic sources, terminal receipt, and Slurm accounting are retained here.
Runtime bytecode caches are omitted because they are neither source nor
scientific output; the remote attempt remains unchanged.
