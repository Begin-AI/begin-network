# Independent discovery and routing adversarial review

Executed with the repository's current `.venv/bin/python` on 2026-10-14. This report records historical findings and independent retesting of subsequent repairs, not an external security audit. No implementation changes were made by this reviewer. All four concrete findings below are resolved in the retested snapshot; broader limitations remain.

Historical vulnerable snapshot SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `intentions.py` | `86c3b3df701b84132029f6ad469769b07c57d7da0999548bab1ed12a5db01b4b` |
| `local_discovery.py` | `c0023d4ba26a2c779f495d0785fcc203207f2b81c04d1fd1b896096f9c7612bf` |
| `routing.py` | `e546ccacd2013d6d819291b340a6ab8fb61b291d014afe3ef686a210c4be32dd` |

## Repair verification

Independent `.venv/bin/python` adversarial retest on 2026-10-14 returned:

| Original finding | Current executed outcome | Status |
| --- | --- | --- |
| NaN host timestamp | `InvalidIntention: integer current timestamp required` | Resolved |
| Boolean vector dimension/coordinates | `InvalidIntention: invalid vector contract` | Resolved |
| Trusted hop budget reset from 1 to 8 | `Refused: hop limit exceeded` | Resolved |
| Truncated chain retaining original limit 1 | `Refused: route does not begin at origin-selected ingress` | Resolved |
| Duplicate matching work | Second call rejected; decryption count 1 and evaluation count 1 across original plus replay | Resolved |

Retested source SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `intentions.py` | `250834a1ee7df37ff450107601e8e19b39ac54ce5ed126bb66f6a5300d02b8b9` |
| `local_discovery.py` | `7f10f790b14034cd69fdb3d12b0cab76b08aed13d8fdf187f4d65993743c1fd2` |
| `routing.py` | `79bdf8948bd1b1ffe7984e047d83eb0e4cc5dfb36e0db77ff4163c9e4e80afe8` |

The intention reproductions below now throw the listed rejection exceptions. The route retest used the same malicious-peer construction, but explicitly signed `body.routing = {'ingress': A, 'hop_limit': 1}` in the origin token before submitting at A. Resetting the latest hop's limit to 8 failed. Keeping limit 1 while substituting B as the first signer also failed. The original token now binds both the designated ingress and budget. The historical route fixture below documents the former behavior and is not directly runnable against the changed policy requirement.

For replay, the reviewer independently wrapped both `local_discovery.open_match_query` and `local_discovery.evaluate` with counters, invoked the valid fixture twice, and asserted `{'decrypt': 1, 'evaluate': 1}`. Authorization, matching scope, and sealed digest checks now precede admission; admission precedes expensive decryption/comparison. A valid request whose later decryption/evaluation fails is consumed, so integrations need a new request ID for a corrected retry. This is fail-closed admission, not a general transactional exactly-once execution protocol.

These repairs establish the tested input and supplied-chain boundaries. They do not prove physical global hop count against a malicious designated ingress, prevent off-protocol copying, or make trusted participants honest.

## Historical findings — independently retested as resolved

### Nonfinite host time bypasses intention expiry

From repository root:

```python
from begin_network.intentions import Store
s = Store()
for id, role in [('a', 'seek'), ('b', 'offer')]:
    s.create(id, 'window', consent=True, role=role,
             available_from=0, available_until=10, expires_at=10)
a = s.vector('a', [1], 'm', 'v')
b = s.vector('b', [1], 'm', 'v')
print(s.compare(a, b, float('nan')))  # observed: 1.0
```

Expiry and remaining-availability checks do not reject NaN timestamps. This requires bad caller-supplied host time; the network query does not directly select `now`. Reject non-integer host timestamps before any lifetime or availability comparison.

### Caller-forged vector contract accepts Boolean dimension and coordinates

Using the same fixture:

```python
from dataclasses import replace
print(s.compare(replace(a, dimension=True, values=(True,)),
                replace(b, dimension=True, values=(True,)), 1))  # observed: 1
```

The normal vector factory rejects Boolean values, but direct public dataclass construction bypasses that validation. `compare` accepts the forged representation because Python treats `True == 1`. This violates a strict interoperable representation contract; it does not establish permission or override stored consent. Require exact numeric types and a positive integer dimension at the comparison boundary.

### Trusted transit peer can reset the route chain and hop budget

The receiving coordinator authenticates the supplied chain, but the original request does not bind a hop budget or ingress coordinator. A malicious explicitly trusted peer can replace the whole chain with its own valid first hop. Observed reproduction with existing test fixture helpers:

```python
import sys
sys.path.insert(0, 'tests')
from test_routing import RoutingTests
from begin_network.envelope import sign, decode
from begin_network.routing import digest
r = RoutingTests(); r.setUp()
try:
    packets = []
    a = r.node('a', {'c': ['b']},
               transport=lambda peer, packet: packets.append(packet))
    a.submit(r.original(), r.kid('c'), hop_limit=1)
    original = packets[0]['original']
    hop = {'version': '0.1-draft', 'type': 'request',
           'sender': r.kid('b'), 'id': 'reset-path', 'audience': r.kid('c'),
           'issued_at': 100, 'expires_at': 200, 'proofs': [],
           'body': {'original_digest': digest(original),
                    'destination': r.kid('c'), 'path': [r.kid('b')],
                    'hop_limit': 8, 'parent_digest': digest(original)}}
    c = r.node('c', {})
    print(c.receive({'original': original,
                     'hops': [sign(hop, decode(r.keys['b']['private']))]})['id'])
    # observed: goal-one, although ingress supplied hop_limit=1
finally:
    r.tearDown()
```

This is an expansion of the ingress routing budget by a trusted peer, not execution authority. Supplied-chain checks cannot prove global traversal history or enforce the origin's unspecified routing policy. If origin-wide hop bounds are required, bind them in an origin-signed routing policy and test reset/truncation explicitly; hop signatures alone do not solve it.

### Duplicate query performs matching before replay rejection

Wrapped `local_discovery.evaluate` with a call counter, then invoked the valid `LocalDiscoveryTests.receive` fixture twice. The second call raised `Rejected: replayed request`, but the counter was **2**. Replay admission occurs after decryption and evaluation. No second successful result was returned, but replay does not prevent repeated computation. For expensive future matching, design atomic admission/state and failure/retry policy before side effects or costly work.

## Verified boundaries

- Adding any of `threshold`, `authority`, or `consent` to the network query causes `Rejected: unsupported matching query fields`. Query data does not rewrite these host choices.
- Repeated valid local query yields a replay rejection, despite the preceding computation described above.
- The authorized query response is only a proposal/no-match Boolean and explicitly reports `full_request_disclosed: false`. It does not release a full request.
- The signed outer local-discovery request contained purpose/action/resource/units and sealed-content digest, not the query vector, model, or intention text.
- Host-supplied owner records and keys remain outside the supplied query. No dynamic code execution or host instruction interpretation was found in these modules.

## Documented limitations, not additional exploits

Routing authenticates transport envelopes, not encryption: the synthetic routing fixture's goal is readable by decoding the original JWS payload. Sensitive content must be separately sealed; routing alone cannot provide transit confidentiality. Even with sealed matching content, transit metadata includes sender, recipient, request ID, timing, action/resource, and routing path. The authorized counterpart necessarily learns the query vector. It can inspect information, retain it, or answer dishonestly; a Boolean result is not a proof of correct computation.

`receive_query` assumes an opted-in owner, with host-selected authority, keys, and owner representation. It does not obtain consent from the intention store, expose grant revocation input, or authenticate owner-record provenance. Those are explicit host integration responsibilities, not evidence that a remote query can select its own authority. Integrations must check current consent/revocation and avoid using remote data as host policy.

The local query contract does not include language, location, intention revision, or expiry independently of its enclosing request and availability. It must not be advertised as enforcing the richer intention-store contract. Plain geometric similarity cannot validate willingness, skill, or aspirations; the separate pretrained benchmark demonstrates failures. Matching remains distinct from permission and task execution.
