# Bounded synthetic goal exchange

This example connects the patent's independent coordinators, voluntarily delegated work, device-local data, and asynchronous return path. It uses synthetic calendar intervals to make the entire calculation inspectable. It does not read a real calendar, infer intentions, execute arbitrary downloaded code, or schedule a meeting.

The requester first verifies a synthetic, locally pinned publisher attestation of a local copy of the method index and selects the owner-local contract. The index grants no authority and advertises zero operating nodes. This does not sign or change the production seed index.

The requester then forms an editable Window intention (learn guitar); a known synthetic mentor opts into a complementary offer. A two-coordinate declared topic fixture represents guitar/piano under an exact method/model contract. A separately authorized encrypted coarse query is evaluated locally by the mentor. Decline or no-match stops the example before task routing, budget reservation or full input disclosure. These are manual synthetic representations, not a learned encoder or private global candidate search.

The resource owner delegates a two-unit calendar-overlap budget to a manager. The manager narrows that to a one-unit grant for the requester, addressed to the worker. The requester signs an `available-overlap` request for `fixture:mentor` and binds its encrypted input digest. Independent ingress, relay, and worker coordinator identities verify the origin and every hop. Routing does not authorize execution.

The worker requires a fresh owner-signed revocation snapshot and independently validates the grant chain. One shared owner budget ledger atomically reserves a unit against both ancestor and leaf budgets. Only the built-in bounded overlap operation runs against its synthetic local fixture. No network content can replace the implementation or select arbitrary code.

The deterministic fixture has intervals `[540,600]` and `[780,840]`; the request supplies `[570,630]` and `[800,860]`. Intervals are integer minute offsets within one synthetic day, with half-open boundaries. Expected overlaps are `[570,600]` and `[800,840]`. This demonstrates computation from authorized fixture data; it is not evidence of human consent to an actual appointment.

The result carries explicit deterministic-computation provenance. It is signed by the pinned worker identity and encrypted to the pinned requester key before mailbox storage. The requester can disconnect, reopen the durable mailbox, retrieve its own pending result, independently verify the worker signature and request binding, and decrypt the answer. Repeating the original work must not consume another budget unit or produce another execution.

## Boundaries

The demonstration uses synthetic identities and data. Coordinator routing here uses local callable transport; the separate coordinator-process example supplies loopback HTTP evidence. The owner controls a single durable budget ledger; independent replicas cannot each spend the same allowance. Reserved work is not automatically refunded or retried after crashes. Mailbox persistence, execution accounting, and result delivery are separate transactions, so recovery from every intermediate failure is not guaranteed.

A signed result proves its signer and integrity, not truthful computation. Encryption protects against parties without the pinned recipient key under the experimental sealed profile; it does not protect against the recipient or a compromised endpoint. Key holders can bypass application permission checks. No private semantic matching, real-device deployment, hardware attestation, or legal compliance is asserted.

## Run and verify

From the repository root, run `.venv/bin/python examples/goal_exchange_demo.py`. The output reports two signed routing hops, the two expected overlap intervals, the synthetic-calculation provenance and fixture revision, exactly one completed execution, one unit spent against each grant, and verified offline mailbox retrieval. The original signer explicitly selects the ingress and hop limit within the signed request.

Run `.venv/bin/python -m unittest discover -s tests -p test_goal_exchange.py -v` for integration checks. Alongside the full exchange, they verify cached idempotency after worker restart, input-ciphertext substitution rejection before budget admission, ancestor revocation blocking a cached retry, wrong-worker result rejection, result-ciphertext substitution rejection, original-request binding, and response replay rejection. These are executable evidence for this fixed operation only.

The demo uses an explicit synthetic clock (NOW=110, envelopes valid 100–200); it does not issue current production credentials. Discovery-before-work is demonstration orchestration under already explicit fixture mandates. The fixture executor also supports direct authorized known-counterparty work; this is not a cryptographic match-conditioned key-release service. The local query reveals authorized coarse representation to the counterpart, not the full calendar input. Root delegated task grants are pre-created in the fixture controller but used only after a proposal; no-match and decline send no task.
