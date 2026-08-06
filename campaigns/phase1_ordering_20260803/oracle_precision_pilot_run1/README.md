# Oracle-precision pilot — partial raw results

Status: **PARTIAL — 13 of 40 shards as of 2026-08-06.** The full 40-shard run
continues on the WashU cluster; these are the completed shards' raw outputs
downloaded for record. The pilot is outcome-blind: it reads only the frozen
panel inputs and labels (contexts, queries, outcome bins); no PFN output or
model deficit enters.

Each `rows_<start>_10/` directory contains:
- `summary.json` — config path, seed root, row range.
- `smc_raw.npz` — per-row SMC and MCMC held-out NLLs (full and ablated),
  order posteriors, 100-bin predictives, per-ordering logZ / ESS / acceptance.

The shards cover rows 0-130 of the frozen 400-row nested panel (both C and N
priors). The pilot verdict is sealed only after the independent verifier runs
on the joined full set; do not treat these partial arrays as a result.

Pipeline provenance: attempt tag `phase1-oracle-precision-pilot-v1`;
preregistration `ORACLE_PRECISION_PILOT_PREREG.md`; audit
`ORACLE_PRECISION_PILOT_AUDIT.md`; design `ORACLE_PRECISION_PILOT_DESIGN.md`;
config `config/oracle_precision_pilot_v1.json`.
