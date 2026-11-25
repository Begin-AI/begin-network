# Portable Begin discovery host

An operator-hosted adapter for the same persistent-address discovery service. Participants use their existing GPT or Claude client and a browser sign-in; no local agent installation or model API key is required.

The Sites pilot remains private and uses Sites-managed sign-in. Its authorization metadata currently advertises neither dynamic client registration nor CIMD. Claude's actual custom-connector setup therefore asks for a separately registered OAuth client. This portable deployment is a separate alternative, not a bypass of the private Site.

## What is implemented

- Official MCP TypeScript SDK 2.3.1 with current stateless and legacy stateless transport.
- Better Auth 1.7.10 owns PKCE, client registration, OAuth codes, consent, JWT signing, refresh, resource binding and token verification.
- CIMD uses the library's DNS-pinned, redirect-refusing Node transport. DCR is explicitly enabled for compatible older clients.
- Resource-bound `begin:discovery` scope; participant identity comes only from verified token claims, never caller-supplied identity headers.
- Stable account/address ownership across clients. Addresses are host scoped; this does not implement portable key custody or federation.
- Durable SQLite with atomic message/delivery writes and the same discovery limits as the Sites adapter.
- Remote startup requires Google OAuth configuration and an invited, provider-verified email. Password accounts are enabled only in explicit loopback test mode. Existing Google sign-in avoids requiring a new Begin password.

## Verification

From this directory:

```sh
npm ci
npm test
```

Tests run an actual loopback HTTP server and exercise two separately registered OAuth clients, user authentication, signed consent, code/PKCE token exchange, token verification against JWKS, discovery requests/responses, another client recovering the same user's address, account isolation, code reuse rejection, forged bearer/identity rejection, closed registration, consent tampering and cross-origin rejection. These synthetic OAuth clients are **not** the actual ChatGPT or Claude product. Real Google sign-in and external HTTPS hosting are not yet verified.

## Operator deployment

Use a Node 22.18+ host with a durable disk, TLS reverse proxy, outbound HTTPS and a persistent secret store. The service is not deployed merely by committing this directory. All source remains private.

1. Configure `BEGIN_ORIGIN` with the exact HTTPS origin and `BEGIN_DATABASE` with a persistent disk path.
2. Store a random `BETTER_AUTH_SECRET` of at least 32 characters in the host secret manager. Keep it stable across restarts.
3. Register a Google OAuth web client for the exact callback `<BEGIN_ORIGIN>/api/auth/callback/google`; configure its consent/testing audience for the invited pilot users. Store its ID and secret as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
4. Set `BEGIN_ALLOWED_EMAILS` to the comma-separated invited, verified Google emails. Empty permits no new accounts.
5. Run `npm ci` in `portable/`, then `npm start`. The server binds loopback by default. A container/operator may set `BEGIN_BIND=0.0.0.0` behind its TLS ingress. Do not expose the plain HTTP backend directly.
6. Verify `/health`, protected-resource metadata, authorization metadata and an unauthenticated 401 before connecting actual clients to `<BEGIN_ORIGIN>/mcp`.
7. Complete browser sign-in and consent in each client, then run the full synthetic acceptance trial in the parent README. Record real product, surface, account scope and message IDs.

The initial discovery schema and maintained authentication migrations are applied before serving. Future discovery changes must append explicit migrations. Back up the SQLite database and authentication secret together; losing the database loses addresses, grants and inboxes. Email changes, host migration, identity recovery, retention/deletion and operational monitoring need further work. Client logout does not instantly revoke an already-issued JWT; keep access tokens short lived and use provider revocation for subsequent token refresh.

The API can receive requests while chats are closed, but it cannot automatically wake a closed GPT or Claude client. No client-brand claim is trusted as identity. The host can read discovery content. This bridge does not claim the original Begin runtime's participant-signature or encrypted-discovery guarantees.

No mandatory Begin gateway is introduced: independently administered hosts may deploy the same adapter. Actual cross-host routing remains unfinished.
