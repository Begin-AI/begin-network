# Security status and reporting

Begin is an experimental protocol and synthetic reference implementation. It is not approved for live personal data, real calendars, payments, arbitrary remote code or public production node deployment. The repository is private pending an explicit publication decision.

Security evidence is operation-specific: signed-envelope verification, scoped grant checks, single-ledger reservations, encrypted content integrity, signed routing, and bounded fixture results have tests and review reports. None proves human identity, truthful capability, honest computation, complete private discovery or safe execution of arbitrary instructions. The MPyC experiment assumes a passive dishonest minority and lacks authenticated distributed transport. The owner-local matcher reveals an explicitly disclosed query to its counterpart.

Read `docs/threat-model.md`, the mechanism-specific documents and the current release audit before running a component. Do not relax local key pins, authority policy, revocation freshness, resource limits or expiry based on incoming text. Fixture workers accept only registered deterministic synthetic operations and cannot run commands or request-supplied code.

For this private development phase, report a suspected issue directly to the repository owner through an already authorized private channel. Do not publish sensitive reproductions or private data in an issue. A dedicated public reporting contact and supported-version policy must be chosen before publication; no response-time guarantee is currently advertised.

A useful report identifies the tested commit, affected operation, trust/adversary assumptions, minimal synthetic reproduction, expected and observed behavior, and any keys/data exposed. Preserve failed tests and corrected versions. Do not treat a green CI run or a valid signature as a blanket security certification.
