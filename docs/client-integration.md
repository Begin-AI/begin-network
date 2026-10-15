# Existing-client discovery integration

The product target is for people to use their existing GPT and Claude clients to submit discovery requests and receive responses or discovery-related requests, with no separately installed Begin app. Client connection and consent may still be necessary. A phone need not run the Python runtime for this experience.

## Architecture correction — 15 October 2026

The hosted adapter described below is a connection/inbox experiment, not an implementation of the founding network design. Its exact-topic SQL routing bypasses this repository's runtime. It must not serve as evidence for decentralized indexes, Mirror/Window/Social representation, protected matching or signed participant coordination.

The corrective implementation is now in this repository: `runtime_bridge.py`, `mcp_adapter.py`, `relay_transport.py` and `encoders.py`. See [participant bridge](participant-bridge.md) for the tested original-runtime path and remaining gaps. It is not deployed or wired to the current ChatGPT plugin. The no-install product target requires an authenticated remote client endpoint bound to each participant's chosen runner. Stdio in the experiment is the operator-side boundary; requiring phone users to install Python would not meet the target.

## Earlier separate inbox pilot

A separate private client adapter is being developed in the adjacent `begin-discovery-service` checkout. Its private pilot is https://begin-discovery.rimaalshikh.chatgpt.site. It exposes persistent host-scoped addresses, voluntary expiring exact-topic subscriptions, bounded discovery fanout, replies/follow-ups, and durable paginated inboxes. Participants authenticate through the host; no model API key is required.

The adapter currently stores readable discovery text and account-bound addresses. It does not assert participant-signed envelopes, self-custodied identity, private semantic discovery, or the cryptographic guarantees of this Python runtime. The adapter's OAuth authentication and the runtime's signed protocol remain distinct. Future integration must preserve that distinction.

A portable Node adapter adds maintained OAuth client discovery/registration and the official MCP SDK. Complete synthetic OAuth/request/response tests pass locally, including account isolation and the same account recovering its address through another client registration. The portable adapter is not yet remotely hosted. The Sites-managed sign-in currently advertises neither DCR nor CIMD; Claude Desktop asks for a separately registered OAuth client. This is an observed client-connection gap, not proof that every remote MCP endpoint works in every client.

On 15 October 2026, the user completed OAuth and all seven Begin tools became callable. A live ChatGPT request, response and related follow-up succeeded against hosted storage. Another authorized conversation recovered the same persistent address and retrieved all three messages. This is two contexts on one signed-in account, with synthetic data. Actual Claude interoperability remains unproven. Source-level and synthetic OAuth tests must not be reported as live Claude evidence.

A private service-access path is being prepared for Claude on the same host, using the documented Sites platform gate plus a separate per-address, expiring and revocable Begin credential. This requires an explicit user request before creating the Sites service-access token. It preserves the private Site audience; it is not public registration or independent-host federation.

The current tools route among consenting addresses on one host. Independent operators must remain free to host compatible adapters; no mandatory Begin gateway or company-wide signing root is introduced. Cross-host discovery, portable identity migration and unsolicited-message defenses remain further work. Durable inbox delivery does not wake a closed GPT or Claude conversation; clients check when invoked or through separately supported automation.

Acceptance requires actual client tools becoming available, stable address registration, opted-in request delivery, a response and related follow-up, and retrieval in a fresh conversation. Record product, device/surface, account scope and actual message IDs. The adjacent adapter's `docs/verification-2026-10-15.md` records the present evidence and gaps.
