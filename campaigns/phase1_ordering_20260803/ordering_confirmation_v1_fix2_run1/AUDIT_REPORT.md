# Phase-1 confirmation FIX2 integrity report

Claim audited: "The archived d=4 PFN fleet exploits predictive information
associated with causal ordering at 120k, and undertraining suppresses this
use."

## Verdict

**NOT-YET-SUPPORTED.** The archived arrays, bootstrap, and independent
verification reproducibly support `INCONCLUSIVE_PHASE1_INSTRUMENT`, not the
proposed claim.

## Blocking findings

1. The preregistered oracle-convergence gate failed. The causal ablated
   3M-minus-1.5M CI is `[-0.010216, 0.004608]`, the control-subtracted CI is
   `[-0.010404, 0.007167]`, and the causal full-oracle change is `-0.015597`,
   CI `[-0.032741, -0.000473]`. These fail the frozen `+/-0.0005` limits. The
   main bootstrap conditions on the atom banks, so this failed guard leaves
   unaccounted oracle Monte Carlo error in the endpoint.
2. The mandatory direct 120k endpoint did not clear: `deficit_C=-0.010804`,
   CI `[-0.022328, 0.000724]`, with `passes_direct_rule=false`. The favorable
   control-subtracted endpoint, `Delta=-0.025802`, CI
   `[-0.038691, -0.012884]`, is insufficient by the locked conjunctive rule
   and is strengthened by the positive N mismatch of `0.014997`.
3. The secondary undertraining rule is conditional on a valid, passing final
   primary result. Although the observed final-minus-20k changes are negative,
   they support only descriptive improvement in the metric. They do not show
   absence at 20k or ordering use at 120k.

## Root-cause evidence

All 18 checkpoints and all 3,201 panel rows per checkpoint passed the
independent batch, context-order, combined, probability, and total-variation
tolerances, for 57,618 checkpoint-row evaluations plus 72 stress rows. The
nested 400-row oracle panel is also row-aligned exactly. The remaining failure
is concentrated in prior-proposal importance sampling under C: full-oracle
effective sample size has median `16.38` from three million atoms, 34.05% of
rows are below ESS 10, and the minimum is `1.01`. Absolute full-minus-half
error increases as ESS falls. This makes a proposal failure more likely than a
checkpoint, row-join, or reporting failure.

## Caveats

- FIX2 reused all 6,402 FIX1 panel rows. This was declared before execution,
  FIX1 produced no model/oracle predictions or scientific endpoints, and no
  leakage signature was found. It remains a reused panel, not a fresh
  externally enforced holdout.
- N is a matched negative control for generic PFN-oracle mismatch, not a
  counterfactual C fleet.
- Inference is over six fixed archived models, not a population of training
  runs.

## Strongest licensed statement

On the frozen d=4/base fleet and reused panel, the ordering-value manipulation
check is positive under C (`V_C=0.075718`, one-sided lower bound `0.064180`)
and null under N, and the observed control-subtracted metric becomes more
negative from 20k to 120k. The direct 120k causal endpoint did not clear and
oracle convergence failed, so this attempt establishes neither PFN ordering
use nor an undertraining effect.

## Cheapest decisive next run

Do not repeat the full confirmation or merely double the same prior-proposal
atom bank. First run a prospectively locked, outcome-blind oracle-precision
pilot on the existing fixed 400-row nested panel. Compare the frozen estimator
against a proposal that targets the causal posterior and report nested
agreement, ESS, and direct/control-subtracted oracle changes. Advance to a
fresh-seed confirmation only if every frozen convergence gate passes. The
pilot diagnoses the dominant instrument failure; it cannot retroactively
rescue FIX2.

The independent DeepSeek red-team repeated the direct-endpoint and
oracle-convergence objection and added no new threat.
