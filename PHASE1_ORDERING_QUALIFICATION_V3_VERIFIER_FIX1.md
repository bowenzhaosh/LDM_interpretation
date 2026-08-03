# Phase-1 ordering qualification v3 verifier fix 1

The three qualification shards and their join were frozen before this repair.
Their source remains commit `fc0b8eb48c75f7c0d1dc208b1d344d663b16baf3`,
tagged `phase1-ordering-qualification-v3`.

The first independent-verifier job, `158994`, failed before reading any raw
scientific array. Its source-inventory parser required every recorded absolute
path to contain the literal directory marker `/source/`. The frozen tagged
checkout instead used the directory name
`LDM_interpretation_phase1_qv3_fc0b8eb`.

Frozen joined artifact hashes at diagnosis:

- `COMPLETE.json`: `dff6b9a4eaf826744911c49cd1d391597e5fead34a74f45bac2d8fe27f83bcdd`
- `qualification_raw.npz`: `a4bc89e5f22f41764ddefb310bc2fb67dc291c0d0156949c1840841549915317`
- `qualification_summary.json`: `e0d30a980de7f1e520e1fc3292edb6a028093f5443e269a3c96d92d5b2abeb30`

This repair is limited to provenance plumbing:

1. A recorded absolute path must end in exactly one member of the frozen exact
   relative-path inventory. Ambiguous, duplicate, relative, missing, and extra
   paths fail closed.
2. Artifact source and verifier source are bound independently. The artifact
   source tag and commit remain unchanged. The repaired verifier must be bound
   to the annotated tag `phase1-ordering-qualification-v3-verifier-fix1` and
   records both identities in its output.

No numerical gate, threshold, raw array, candidate order, seed, or decision
rule is changed. The joined decision remains provisional until the repaired
independent verifier succeeds on the frozen artifact hashes above.
