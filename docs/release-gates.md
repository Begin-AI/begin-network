# Release gates

All gates are NOT DEMONSTRATED in this seed. Schema tests are not security certification.

| Gate | Required evidence |
|---|---|
| P1 Authenticity | Signed-envelope interoperability, tampering, audience, expiry, replay, forged authority tests |
| P2 Private discovery | Defined adversaries/collusion, leakage analysis, inversion/probing tests, authorized key release |
| P3 Bounded actions | Scope attenuation, resource accounting, revocation freshness and stop-access tests |
| P4 Independent operation | Independent implementations, retry/deduplication, offline retrieval, expiry, node replacement |
| D1 Need is enough | Needs represented without public profiles, repayment, or contribution history |
| D2 Open initiative | Agent/human initiative, decline, pause, exit without new rights |
| D3 Personal control | Inspect/edit/retire representations; explain disclosure limits |
| D4 Fair opportunity | Newcomer discovery, small contributions, no authority from extra keys/compute |
| E1 Faithful representation | Facts/aspirations/inferences/consent are distinct and editable |
| E2 Complementary fit | Role/constraint/mutual-willingness cases, including adversarial mismatches |
| E3 Window/social | Controlled exploration without moral ranking |
| E4 Measured quality | Versioned multilingual corpus, false/missed matches, incompatible-method rejection |

Before public repository release: choose code and patent license terms, review attribution and dependencies, scan for secrets and private source/data, and accurately label implemented features. Before personal-data participation: pass applicable privacy/authorization gates. Publication and live deployment are separate decisions.
