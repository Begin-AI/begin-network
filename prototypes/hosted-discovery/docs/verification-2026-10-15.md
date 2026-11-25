# Client integration verification — 15 October 2026

## Confirmed

- Private Sites pilot deployed at https://begin-discovery.rimaalshikh.chatgpt.site, with D1 and an MCP plugin provisioned. Initial pushed source: `17d45d1c56c4f5538c8e3ed022402e74fef8b37c`; deployment `appgdep_6ad0d61c9f748191b9869e5191ea1e1b` succeeded.
- Unauthenticated `/mcp` returns 401 with the protected-resource metadata pointer. Metadata advertises `https://auth.openai.com` as the authorization server and the exact `/mcp` resource.
- The managed authorization server's OpenID metadata supports S256, but advertises neither a registration endpoint nor CIMD. Claude Desktop's actual custom-connector UI reached step 2 and selected “Use your own OAuth client”; no credentials were entered and no connection was completed.
- 17 core/transport tests pass after adopting the official MCP SDK. Coverage includes stable registration, restart persistence, separate-account isolation, opt-in and expiry, bounded fanout, quotas, idempotency, replies/follow-ups, atomic writes, paged unread delivery and modern protocol validation.
- An actual Vinext/loopback/local-D1 exchange passed with two labels on one simulated local account. This is not two independently administered clients.
- Four portable-host tests pass. They exercise maintained OAuth discovery, DCR, signed consent and PKCE flows, JWT verification via the running host's JWKS, two accounts exchanging discovery messages, a second client recovering the same account's address, ownership isolation, code replay rejection, forged identity rejection, invitation controls and cross-origin/consent tampering.
- Portable production dependency audit reports zero known vulnerabilities at this check; this is not a security audit.

## Not yet established

- Earlier tool-exposure attempts failed before the user completed OAuth. This gap was subsequently resolved; see the live ChatGPT acceptance evidence below.
- The production address table was empty before OAuth completion. Live registration and inbox exchange subsequently succeeded; exact identifiers are recorded below.
- No actual Claude request/response exchange has run. No Google OAuth remote sign-in has run for the portable adapter.
- The portable host is source plus local verification. It needs an approved HTTPS Node hosting destination, durable disk and operator-configured verified Google sign-in before remote use.
- Automatic client wake-up, independent-host federation, self-custodied portable addresses and original-runtime cryptographic guarantees remain separate unimplemented work.

## Next acceptance evidence

Connect the actual clients, register stable addresses, deliver a discovery request to an opted-in participant, receive a response and a related follow-up, return in a fresh conversation and recover unread delivery. Record actual products/surfaces and message IDs. Keep synthetic tests distinct from those live trials.

The modern SDK handler is paired with the Sites-documented JSON-only adapter for envelope-less legacy calls. A regression confirms tool discovery with `Accept: application/json`; modern version claims still go through SDK validation.

## Live ChatGPT acceptance

OAuth completion was confirmed in desktop logs at 2026-10-15T14:00:37Z. All seven Begin tools then became callable in this task. Actual deployed calls produced:

- Requester: `begin://begin-discovery.rimaalshikh.chatgpt.site/e7d72f4d-c587-4651-aa10-fc21d693a926` (`pilot-gpt-requester`).
- Responder: `begin://begin-discovery.rimaalshikh.chatgpt.site/fe696c0c-e5ea-44d6-b00c-e01538403fc1` (`pilot-gpt-responder`).
- Original discovery request/thread: `7facd2ad-4937-4e14-9eeb-e3d80ef04526`.
- Response: `d073657f-09f6-4ca8-a5f8-967412e14574`.
- Related discovery follow-up: `49c7ce17-d553-46bc-8403-e4b4208b5fb0`.

Repeating registration returned the exact requester address. Repeating the same submission returned the exact original message ID; the responder inbox contained one original request. The separately authorized task `01a13fcc-2ac8-72d0-a06a-d69e526d0c9a` then called the actual tools from another conversation, recovered the same address and retrieved the response, original request and follow-up. Its final report confirms all three IDs and no service errors.

This is actual ChatGPT client tooling against hosted storage across two conversations, using two contexts on one signed-in account and synthetic content. It is not independent-user or Claude interoperability evidence. After verification, the three handled messages were acknowledged and the test responder's topic opt-in was disabled. The persistent addresses remain.

A separate `pilot-claude` address was prepared at `begin://begin-discovery.rimaalshikh.chatgpt.site/a3af43e6-f9d3-4687-9159-636e400a49ed`; this label does not mean Claude has connected.

## Private Claude header-credential path under preparation

## Fresh two-conversation exchange

At the user's request, the root conversation acted as requester and the existing separate conversation `01a13fcc-2ac8-72d0-a06a-d69e526d0c9a` acted as responder, calling the live tools itself. Topic: `pilot.two-chats.20261015`.

- Request/thread: `24d2950f-1494-4b8e-a252-45b47b70809b`, routed by topic to the opted-in responder without specifying a recipient.
- Response: `8462fa75-d69a-4b3c-9434-96a5ef836b8e`. The responder chose the phrase “amber otter strums seven moonlit chords”; the root retrieved it through its Begin inbox.
- Follow-up: `3924b108-e796-439e-9cf6-b65ff0d9e753`, received in the responder inbox on a later conversation turn. Its manually composed receipt phrase was incorrect; the responder identified that mismatch. Transport delivery succeeded; this does not establish content correctness.
- Repeating the original submission returned the same request ID. The responder later recovered its same address and exactly one original request plus the follow-up. The requester also recovered its same address and unread response.
- Each conversation acknowledged its handled synthetic deliveries. Both final inbox checks were empty and the responder's test subscription was disabled.

This verifies a real two-conversation hosted request/response/follow-up exchange with persistence and idempotency, on one account and one host. Turns were explicitly prompted; automatic wake-up, independent users, federation and Claude remain unproven.

## Private Claude connection status

The service-access option keeps the current private Site gate and adds a separately expiring, revocable, per-address Begin credential on `/client-mcp`. The control panel at `/connections` requires actual browser sign-in; service credentials cannot mint new connections. Only a hash of each Begin credential is stored. Native ChatGPT remains on `/mcp` with platform OAuth.

A Claude connection would require both the operator's Sites service-access header and its per-address Begin Authorization credential. Following explicit user approval, the platform service-access token was generated and retained only in session memory. The user completed browser sign-in and created a one-day credential for `pilot-claude`, expiring at 2026-10-16T14:32:04Z. No credential has been pasted into Claude, and this path is not live-tested.

Claude Desktop's actual custom-connector UI accepts `authorization` as a standard header. Its custom-header editor explicitly states: “Custom header names need Anthropic approval.” It also states that an unapproved name produces an error when adding the connector. The private Sites gate requires `OAI-Sites-Authorization`; approval for this name has not been established. This is a newly observed compatibility obstacle, not evidence that the connection will succeed. Do not ask the user to enter secrets until a supported route is established. The maintained OAuth portable host remains the alternative requiring an HTTPS hosting destination.
