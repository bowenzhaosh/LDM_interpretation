# Mapping qualification cross-family review

Reviewer: configured DeepSeek v4-pro helper  
Stage: pre-run, before the attempt attestation and model predictions  
Raw verdict: `UNSOUND`

## Findings and adjudication

### Claimed blocking finding 1: missing `panel` and `score` CLI commands

Disposition: rejected as a reviewer file-attribution error.

The reviewer attributed the `qualification_seal.py` archive CLI to
`mapping_qualification.py`. The latter registers `panel`, `score`, and `verify`, and
the targeted CLI test exercises the nonzero scientific exit for a failed score.
The archive module separately registers `seal` and archive `verify` commands.

### Claimed blocking finding 2: qualification lookup uses current `HEAD`

Disposition: rejected because exact same-commit execution is intentional and
preregistered.

The qualification decision licenses a scientific run only "without changing source
or configuration." The scientific run lock and qualification artifact are therefore
both rebuilt before the final protocol commit, and the qualification and any licensed
science run use that same commit. Looking up the qualification under the clean current
`HEAD` is a fail-closed enforcement of this rule, not a path bug.

## Useful agreement

The cross-family reviewer found no independent major issue in the mapping gates,
information barrier, seed-domain separation, saved guard tensors, or artifact seal.
It agreed with the licensed interpretation:

> `FAILED_NATIVE_MAPPING` means the readout is not qualified for scientific scoring.
> It does not falsify Bayesianity of the checkpoints.

## Cross-check status

The review was completed and retained even though its overall verdict depended on two
incorrect premises. Its scientifically relevant semantic check agreed with the local
audit panel. No code was relaxed in response to the review.
