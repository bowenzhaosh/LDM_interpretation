# Phase-1 confirmation FIX2 instrument evidence

Symptom: the complete confirmation DAG returned
`INCONCLUSIVE_PHASE1_INSTRUMENT`; primary and secondary claims were
`NOT_EVALUATED` because the preregistered oracle-convergence gate failed.

Frozen evidence:

- Source: commit `9c6a3732993ea13557279ec8d330b7d1a076e63f`, annotated tag
  `phase1-ordering-confirmation-v1-fix2`.
- Attempt identity:
  `ec282fc468de2f42f01dc11c4b6733a5d926796a5929e96e549f52fcfa9c91b8`.
- Remote attempt (read-only):
  `/engrfs/project/class/zhao.b/pfn-dag-phase1-confirm-v1-fix2-run1`.
- Local mirror:
  `/Users/bowenzhao/LDM_interpretation_confirmation/campaigns/phase1_ordering_20260803/ordering_confirmation_v1_fix2_run1`.
- Jobs: panel `160055`, PFN `160056`, oracle banks `160057`, `160062`,
  `160063`, join `160064`, verifier `160065`. All completed with exit code
  zero.
- Independent verification:
  `INDEPENDENT_CONFIRMATION_RAW_RECOMPUTATION_PASS`; decision
  `INCONCLUSIVE_PHASE1_INSTRUMENT`; joined summary and raw hashes both match.
- PFN replay maxima: batch logp `3.4332275390625e-5`, context logp
  `1.9073486328125e-5`, combined logp `3.814697265625e-5`, probability
  `5.024417268906234e-7`, total variation `1.996038085179163e-6`; all 18
  checkpoints passed their frozen caps.
- Failed oracle-convergence quantities on 200 fixed rows per prior:
  causal full-minus-half full-oracle NLL `-0.015596968876355054`, causal
  ablated `-0.002750615327850201`, control ablated
  `-0.0011271514656034309`, and causal-minus-control ablated difference
  `-0.0016234638622467702`. The locked direct and control-subtracted ablated
  limits are `0.0005` nats.
- For the causal prior, the full-oracle change was 22.91% of the positive
  fixed-fleet gap, above the locked 20% maximum.
- Effective sample size at three million prior atoms is low. Across all 3,201
  causal rows, full-oracle ESS has minimum `1.0077`, median `16.3784`, and
  34.05% of rows below 10. On the fixed 200-row convergence panel the median
  is `17.0651` and minimum `1.0954`.
- The nested-half rows are unique, all are present in the full result, every
  metadata and input digest matches, and copied full-oracle NLL values match
  the full archive exactly (maximum difference zero).

No result artifact in this run may be edited. Any repair requires a new source
tag, new attempt identity, and fresh output root.
