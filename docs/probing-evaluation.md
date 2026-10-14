# Repeated boolean outcome leakage experiment

This is a synthetic failure measurement against the actual owner-local discovery API. It is not a private-discovery solution, a general embedding inversion result, or a P2 pass. It uses no real intentions, external service, model weights or stored private keys.

Run after installing the core runtime:

```sh
python experiments/probing/run.py
python -m unittest discover -s tests -p test_probing_evidence.py -v
```

## Mechanism and adversary

The owner holds a synthetic two-dimensional L2 vector at angle 0.37 radians. The requester knows only that the angle lies in the first quadrant, the compatible method/model/purpose and complementary role, overlapping time window, and the fixed cosine threshold 0.5. The requester is authorized to submit match queries and may choose arbitrary normalized vectors. Input validation checks shape/contract, not whether a trusted encoder generated a vector. The owner sees each authorized query; this attack measures what the requester learns from the boolean outcomes.

Each round invokes `receive_query` with a real freshly signed request, distinct request ID, encrypted query bound by its digest, pinned keys, persistent replay store and the same valid direct matching grant. The grant's `max_units: 1` is a per-request ceiling. It is not the opt-in delegated ledger and imposes no cumulative limit on twelve distinct one-unit queries. Replay rejection does not limit fresh identifiers. No grant is forged and no signature, cipher or replay implementation is broken.

The requester bisects its angle interval at m and queries the direction m + π/3. In the stated range, a cosine match at threshold 0.5 is true exactly when the owner's angle is at least m. It updates its interval solely from that boolean. Benchmark truth is used to construct the owner's fixture and report error, not to select queries or update bounds.

## Observed result

The recorded twelve-query execution in `experiments/probing/results.json` produced:

| Measurement | Observed |
| --- | --- |
| Accepted distinct requests | 12 |
| Units in each request / direct-grant maximum | 1 / 1 |
| Recovered angle interval | [0.3696893698804395, 0.3700728650774109] |
| Interval width | 0.0003834951969713951 radians |
| Midpoint estimate error | 0.00011888252107483677 radians |

All requests passed the existing signature, encrypted-digest, scope and replay checks. The regression reruns the actual API and checks containment/error rather than relying on the stored result. It deliberately verifies leakage remains demonstrable; green here means the measurement works, not that privacy passed.

## Implications and limits

Returning only a boolean avoids disclosing a raw score in a single call, but repeated chosen queries can still recover protected information. Hiding the comparison with MPC would not by itself remove information intentionally returned by the same predicate. This experiment did not execute the MPC protocol or invert the 384-dimensional learned encoder; those stronger claims would require their own tests.

A privacy-preserving discovery deployment needs an explicit repeated-query policy, cumulative admission, owner consent/freshness, deliberate output accounting and analysis of colluding or many-key principals. Even a small query allowance is not a proof of privacy. Device keys are not unique humans, and malicious participants can coordinate outputs. The current direct owner-local handler has no cumulative query budget, rate control or differential-privacy mechanism. The delegated ledger used for bounded task execution does not automatically protect matching calls.

This is concrete probing evidence for the research plan. Complete private candidate discovery, conditional key release, membership leakage, broad inversion/collusion evaluation and safe real-data participation remain unproved. Do not enable personal data merely because this demonstration is reproducible.

## Independent check

A second collaborating agent reran the API experiment and reproduced the stored result exactly. It reconstructed the interval from only the recorded query angles and booleans, then tested six additional synthetic truth angles (0, 0.1, 0.37, 0.9, 1.5 and π/2): every recovered interval contained its truth, with midpoint error at most 0.00019175 radians. Source inspection confirmed the query-update logic does not read truth or owner coordinates; temporary keys remain in memory. This is independent agent scrutiny on the shared development host, not an external security assessment.
