# Confirmation v1 attempt 1: failed before science

This directory is the immutable evidence bundle for the first production
attempt at source commit `38b6167bf97777e9eaf516cb972f923a4113157e`, tag
`phase1-ordering-confirmation-v1`.

Panel job `159868` failed after 45 seconds on 2026-08-03 because the harness
required bitwise covariance symmetry. The generated matrices differed across
mirrored entries only by float64 multiplication-order roundoff. All six
downstream jobs were cancelled by dependency and used zero runtime. No panel
was sealed and no scientific result was computed.

`SUBMISSION.json` is the durable seven-stage launch receipt. `panel/` contains
the attempt lease and running identity. `slurm/` contains the exact traceback.
`telemetry/` records the assigned device and utilization. `sacct.txt` records
the terminal state of every job. Runtime bytecode caches are deliberately not
archived because they are neither source nor scientific output; the original
remote attempt directory remains unchanged.

The root-cause analysis and prospective repair are specified in
`PHASE1_ORDERING_CONFIRMATION_FIX1.md` at repository root.
