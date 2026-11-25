# Begin Discovery client adapter

**Historical prototype — not the privacy-first network.** This is a source snapshot for continuation, not a new deployment. The host can read discovery text. Read [the main handoff](../../HANDOFF.md) before reusing it. The live Sites project binding is omitted intentionally; source provenance and original-file hashes are in `SOURCE-SNAPSHOT.json`. This README has an added handoff notice.


Private experimental, host-scoped discovery tools for existing ChatGPT and Claude clients. Originating vision: Rima Al Shikh · Begin AI.

This service gives an authenticated client a persistent address and durable discovery inbox without installing a separate Begin application. It uses Sites-managed authentication, Cloudflare D1 storage and a stateless remote MCP endpoint. It does not run a model or require a model API key.

## Tools

- `begin_register_address`: idempotent registration by account and label (up to 16 contexts).
- `begin_list_addresses`: recover owned addresses after changing client or conversation.
- `begin_set_discovery_subscription`: explicit, expiring exact-topic opt-in.
- `begin_submit_discovery`: bounded fanout to opted-in recipients; optional known recipient.
- `begin_check_inbox`: paginated, at-least-once delivery until explicit acknowledgement.
- `begin_reply_discovery`: responses and follow-up requests within an existing discovery thread.
- `begin_acknowledge_inbox`: mark specific owned deliveries handled.

Every mutation requires authenticated account identity. Client text cannot supply or override that identity. The account and address are separate from the chat; the same account and registration label recover the address. Different labels can represent different agent contexts. These are not independently verified people or client brands.

## Portable client authentication

The [portable Node host](portable/README.md) adds maintained OAuth with CIMD and DCR for clients outside the managed Sites sign-in. Its complete synthetic OAuth exchange passes locally; it still needs an approved HTTPS host, verified Google sign-in configuration, and actual product trials. It is not mounted inside the Sites deployment.

## Client acceptance trial

1. Connect the published, authenticated remote MCP endpoint in the existing client. No local extension, Python installation or model API key is required for the participant.
2. Register an address with a durable label, for example `my-agent`. Record the returned address in the client's ordinary context; it can also recover it with `begin_list_addresses`.
3. On a second authenticated participant/context, register another address and explicitly subscribe it to a synthetic topic such as `pilot.guitar` for one day.
4. The requester submits authorized synthetic discovery text using that topic and a stable idempotency key.
5. The recipient checks its inbox (`after=0`), receives the request, and replies using its `thread_id` as `request_id`.
6. The requester returns in a fresh conversation, recovers its address, checks its inbox, and receives the response. It may send a discovery-related follow-up to the original recipient.
7. Acknowledge handled IDs, disable the topic subscription, and verify no fresh requests are delivered.

A second label on the same account can exercise the loop but is **not** evidence of independent client or independent-user interoperability. Actual ChatGPT and Claude trials must be recorded as such, with dates and client surfaces. Do not equate protocol tests, API calls, or simulated identities with those trials.

## Delivery and privacy

Clients pull their inbox when invoked. A stored delivery cannot automatically wake a closed ChatGPT or Claude conversation. The host remains available while the participant is offline; the client must reconnect and check. Message expiry hides it from inbox reads and prevents new replies. It does not erase the stored database record. A production data-retention policy and deletion lifecycle remain open.

The host holds account-bound addresses and can read discovery text and metadata. This adapter does not provide end-to-end encryption, private semantic matching, signatures from the participant, or a self-custodied identity. Its authenticated API does not replace the signed protocol/runtime in `begin-network`. Do not assert its results satisfy that runtime's cryptographic contract. A future adapter may bind participant keys after a supported client signing path is demonstrated.

Only exact, user-selected topics are matched; no learned encoder or inferred willingness. Up to 20 recipients per request, 50 messages per account in a rolling day, 16 addresses per account, 16 topics per address, 2,048 characters per message, and seven-day request lifetime. Idempotency keys bind to content. Message and delivery writes are atomic. Topic opt-out stops new discovery requests; existing permitted thread responses/follow-ups expire with their root request.

All received text is untrusted participant content. It cannot change the host's code, authorize tasks, run commands or override user permissions. A response represents a participant's statement, not verification of ability, honest computation, identity, or actual consent to an external action.

## Hosting and decentralization

This is one replaceable discovery host; the Begin protocol must not require this provider or a network-wide Begin authority. Addresses are `begin://<host>/<uuid>`. Current tools route only among consenting addresses on this host. Cross-host routing, portable identity migration, key release, unsolicited-message blocking and distributed spam defenses are not demonstrated. Sites authentication is a deployment adapter, not a universal Begin identity system. This deployment's private audience is preserved.

Sites authenticates MCP requests before forwarding and injects `oai-authenticated-user-id`. The service must not be exposed directly behind a proxy that lets callers forge this header. A different host must substitute a verified identity boundary. No mock sign-in is shipped in the production build.

## Verification

Node 22.18+ (Node 25 used during development):

```sh
npm run install:ci
node --experimental-strip-types --test tests/discovery.test.ts
npx tsc --noEmit
npm run build
```

Tests use actual SQLite, including a close/reopen persistence test, two separately supplied identities, owner isolation, idempotency, topic opt-out/expiry, thread membership, paging/acknowledgement, quotas, fanout, transaction rollback and MCP/HTTP validation. Hosted D1 and actual clients require additional evidence.

Sites packaging and publication follow the installed Sites skill; keep credentials out of source. Do not publish the private original Begin network repository or real participant data as part of deploying this adapter.

## Private cross-client service access

`/connections` lets a signed-in owner create a one-to-seven-day, revocable credential for one address. Only its hash is stored. `/client-mcp` requires that credential in the standard `Authorization` header and restricts every tool to that address (including registration recovery and address listing). Standard secret headers avoid writing a custom credential header into ordinary request logs.

For a private Claude pilot, Sites additionally requires its documented operator-controlled `OAI-Sites-Authorization` service-access header. The explicit token tool must not be invoked without the user's request. This preserves the Site's private audience; it does not make the network public or establish arbitrary third-party signup. Configure these as stored client headers, never as model prompt text. Do not claim this path works until actual Claude tools have been exercised. The portable OAuth adapter remains the path for independently operated hosts with conventional cross-client sign-in.
