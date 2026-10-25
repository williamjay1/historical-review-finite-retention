# Past-only feasibility: interpretation and reproducibility

This extension uses all 56 existing SMD device/backbone identities at both
paired cadences and the four ESA mission/backbone histories. These are 116
related histories, not 116 independent deployments. Three next-quarter
decisions per history produce 348 decisions per budget/factor condition.
The small ten-history feasibility pilot remains separately documented. The
census extension was declared after that pilot with the same fixed rule.

For actual serialized payload sizes p, predict the next payload as
`p_current + max(0, p_current - p_previous)`. The buffered version multiplies
that predicted payload by 1.25. Both add the known next-prefix header cost.
No incident labels, affected channels, future measurements or future review
arrivals enter this formula. Caps are illustrative, not measured deployments.

| Capacity | Factor | True feasible | False feasible | True infeasible | False infeasible |
|---|---:|---:|---:|---:|---:|
| 64 KiB | 1.00 | 299 | 15 | 32 | 2 |
| 64 KiB | 1.25 | 297 | 11 | 36 | 4 |
| 256 KiB | 1.00 | 334 | 4 | 9 | 1 |
| 256 KiB | 1.25 | 332 | 4 | 9 | 3 |

The 25% buffer reduced false-feasible decisions at 64 KiB, but did not remove
them. At 256 KiB it left all four false-feasible decisions and increased
missed opportunities. A feasibility forecast can guide planning; it cannot
establish a completeness guarantee. Each actual admission must still verify
the encoded bytes and downgrade or refuse the service on overflow.

Fine SMD at 64 KiB alone produced 13 false-feasible and one false-infeasible
decision without the buffer, versus nine and two with the buffer, across 168
decisions from 56 related fitted streams. The worst single underprediction in
the complete census was 91.7042%; the fixed buffer left 89.9403%. These are
descriptive stress results, not estimates of deployment risk or independent
test statistics.

Examples illustrate why past growth is insufficient. Under the as-of header,
ESA Mission 1 ridge grew from 19,943 bytes at the first quarter to 274,131
bytes at the second. SMD machine-1-1 PCA fine grew from 8,154 bytes at the
second quarter to 100,580 at the third. These histories do not justify assuming
stationary compressed-byte increments. The examples were located after the
unchanged census rule was executed and are illustrative, not selected inputs
to the forecast.

This experiment recompresses each observed prefix as a complete single file.
It diagnoses growing-history capacity and does not measure a causal online
admission latency. All numerical atoms, full support and usability bitmaps
are decoded and compared with the input prefix. Byte strings are actually
serialized; the experiment does not claim these prefix files were written to
disk. The online chunk experiment separately measures file-backed queries.

The current core semantic receipt is `core_semantic_audit.json`: 64 support
worlds, 448 archive conditions, 28,672 arbitrary index-set queries, zero false
certificates and zero avoidable unknowns, with script SHA256
`6ffa3462733abd162d9a6d612464ef5bec9ead680335b0f9d83330d36d44d637`.
A project-wide filename search found no `finite_possibleworld_audit.json`;
that earlier filename should not be cited as the final receipt.
