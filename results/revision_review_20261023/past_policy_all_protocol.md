# Past-only capacity forecast, declared before execution

Scope is preselected for computational relevance: machine-3-4 is the existing
constrained server; machine-1-1 is a previously used inexpensive control. Both
PCA and ridge, paired coarse and fine schedules, plus ESA Mission 1 PCA/ridge
give ten histories. This is a targeted stress/control analysis, not an estimate
of the distribution of deployment capacities or an independent external test.

Record service is unchanged: all eligible high records (t,channel,review
version,float32 score,float32 window-last), and separately charged usability.
For each prefix the full format is the smaller actual byte string among the
existing SOA-zlib and bitmap-plus-values codecs. JSON, framing and usability
bytes are included. This is a growing-history single-file service, not the
fixed-chunk FIFO retention experiment.

At the end of each of the first three equal quarters, predict complete bytes
for the next quarter prefix using only payload sizes already observed:
  predicted_payload_next = payload_now + max(0,payload_now-payload_previous).
The first difference uses the actual empty-prefix payload as its predecessor.
Add the known next scheduled prefix's header cost. The two prespecified rules
multiply predicted_payload_next by 1.0 or 1.25 before adding that header cost.
These multipliers are fixed illustrations, not tuned using later prefixes.
The known schedule horizon/next query time is a planning input, not future
measurements. Header contains no future review-arrival list, source score hash
or incident information. True next cost is computed only for evaluation.

At illustrative 64/256 KiB caps, report true-feasible, false-feasible (promise
would fail), true-infeasible and false-infeasible (missed opportunity). A
forecast is not a guarantee: actual admission must recheck bytes; an incorrect
prediction cannot justify a completeness certificate. This test quantifies
predictability of growth, not human benefits or a measured field bottleneck.

No labels enter the forecasting rule or capacity costs. Existing coarse loader
may read labels to construct its unused event table; no event/query outcome is
passed to a forecast, selector or serializer. Repeated prefixes/backbones and
cadences are related observations and are not independent deployments. Use
descriptive counts, no significance tests or deployment frequency inference.

## Recorded census extension after the targeted pilot

The ten-history pilot completed in 12.3 seconds, establishing feasibility.
Before this census execution the scope is expanded to ALL 56 existing SMD
device/backbone identities at BOTH paired schedules (112 histories), plus all
four ESA mission/backbone histories (116 total). This supersedes the selected
scope paragraph above only. The cost definition, forecasts, 1.0/1.25 factors,
quarter boundaries and caps are unchanged; no performance-dependent exclusion
or threshold tuning is permitted. The census is a post-pilot extension, not
preregistration or previously untouched external validation. All failures stay.
