# Claim ledger

Documents checked: `README.md` and `REPORT.html`.

Evidence checked: the preregistration, all joined raw arrays, the 50,000-draw
bootstrap indices, stage markers, Slurm logs and accounting, independent
verification, replay summaries, checkpoint registries, git objects, and
transfer/checksum manifests.

| ID | Claim | Verdict | Evidence and qualification |
| --- | --- | --- | --- |
| C1 | This is the first confirmation attempt to execute every scientific stage. | SUPPORTED | All seven stages completed. FIX1 stopped before PFN/oracle predictions or endpoints. |
| C2 | The directory contains the campaign output and audit package. | SUPPORTED | The remote tree is present byte-for-byte under the canonical transfer manifest; local audit and portability additions are separately sealed. |
| C3 | The decision is `INCONCLUSIVE_PHASE1_INSTRUMENT` and establishes neither ordering use nor undertraining. | SUPPORTED | The joined result has `oracle_convergence=false`, `primary=NOT_EVALUATED`, and `secondary=NOT_EVALUATED`, exactly as required by the locked stop rule. |
| C4 | Seven Slurm jobs completed with exit code zero. | SUPPORTED | `sacct.json` contains exactly seven `COMPLETED`, `0:0` jobs; the seven error logs are empty. |
| C5 | Independent raw recomputation passed. | SUPPORTED | `independent_verification.json` binds the raw and summary hashes. An additional audit reconstructed all 6,402 joined rows with no metadata/hash mismatch. |
| C6 | Replay passed all 18 checkpoints, 3,201 panel rows per checkpoint, and 72 stress rows. | SUPPORTED | All frozen batch, context, combined, probability, and total-variation caps pass across 57,618 checkpoint-row evaluations plus the stress set. |
| C7 | Oracle convergence is the blocking validity failure. | SUPPORTED | It is the only false validity gate and the preregistration requires all gates to pass. |
| C8 | Ordering value is positive under C and null under N. | SUPPORTED | Recomputed `V_C=0.0757183`, one-sided lower `0.0641798`; `V_N=-6.24e-19`, interval approximately `+/-6.6e-17`. |
| C9 | Direct C at 120k fails while C-minus-N is favorable only descriptively. | SUPPORTED | Direct C is `-0.0108043`, CI `[-0.0223281,0.0007244]`; Delta is `-0.0258017`, CI `[-0.0386907,-0.0128838]`. The locked rule says Delta alone is insufficient. |
| C10 | Both 20k-to-120k metrics improve descriptively. | SUPPORTED | Direct change is `-0.0534814`, CI `[-0.0625069,-0.0444694]`; control-subtracted change is `-0.0278453`, CI `[-0.0383230,-0.0172514]`. No capability claim is attached. |
| C11 | The reported nested 3M-minus-1.5M points and intervals are exact. | SUPPORTED | Independent regeneration of all 50,000 fixed-bootstrap replicates matched every point, interval, and bootstrap-index hash. |
| C12 | C full-oracle ESS has median 16.38, minimum 1.01, and 34.05% below 10. | SUPPORTED | Direct recomputation gives median `16.37836`, minimum `1.00769`, and fraction `0.340519`. |
| C13 | Proposal degeneracy is the strongest current diagnosis. | SUPPORTED AS INFERENCE | On the 200 nested C rows, log ESS is negatively associated with absolute half-versus-full error. Replay, joins, and independent recomputation pass. The report does not call this causal proof. |
| C14 | Eighteen model states and six sidecars are packaged and hash-verified. | SUPPORTED | All 24 files and 78,188,398 bytes match both the frozen and portable registry hashes. |
| C15 | The remote transfer matched 8,021 files and 162,056,062 bytes. | SUPPORTED | `verify_transfer_tree.py` produces the same canonical tree SHA-256, `25c03976...783b62a`, remotely and from the local prepackaging subset. The 8,021-line source manifest is archived. |
| C16 | `ARTIFACT_SHA256SUMS` seals every non-cache archive file except itself. | SUPPORTED AFTER FINAL SEAL | The final coverage check has no missing or extra paths and `shasum -c --status` exits zero. |
| C17 | Commit, annotated tag, attempt identity, and joined hashes are correct. | SUPPORTED | Git, 381 identity-bearing JSON records, stage markers, joined completion, and the verifier agree. |
| C18 | The “What may be said” paragraph is the strongest licensed interpretation. | SUPPORTED | It reports descriptive movement and explicitly withholds both prohibited conclusions. |
| C19 | An outcome-blind oracle-precision pilot should precede another confirmation; blindly doubling the same proposal is unjustified. | SUPPORTED AS RECOMMENDATION | The 3M-versus-1.5M gate already fails and worst-row ESS is near one. The report does not claim the replacement will succeed. |

No external papers or web sources are cited. All links and attributions are
internal and resolve within the repository.

Final tally: 16 factual claims supported, two interpretations correctly
qualified, one recommendation evidence-backed, and no remaining overstated,
unsupported, or unverifiable claim.
