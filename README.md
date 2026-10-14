# Begin network

Private development seed for voluntary human and AI coordination.
Originating vision: Rima Al Shikh · Begin AI.

Begin turns purpose-bound intentions into willing connections and scoped action.
Any participant may initiate. Every participant chooses. Authority stays bounded.

## Status

Experimental protocol/runtime under private development. Implemented: Ed25519 envelopes, direct and attenuated delegated grants, persistent atomic resource accounting, receiver-bound sealed content, owner-local encrypted-query matching, editable intention contracts, durable mailboxes, signed routing and public-index validation. Independent agent installation, Python/Node signature interoperability, three-process coordinator routing/failover and a pretrained embedding benchmark have recorded evidence.

The owner-local path reveals the authorized query to the counterpart and is **not full private semantic discovery**. The learned embedding benchmark still falsely matches negation, refusal and aspiration-as-capability. Complete key release, adaptive-probing defenses, cross-host secure transport, recovery semantics and publication licensing remain unfinished. No P1–E4 gate is claimed fully passed. This repository remains private.

## Run

Python 3.9+ and `jsonschema[format-nongpl]>=4.18,<5`:

```sh
python3 -m pip install -e '.[dev]'
begin-network validate-index discovery/index.json
python3 -m unittest discover -s tests -v
```

The example index contains methods and schemas, with **zero operating nodes**. It makes no network activity claims.

## Contents

- [Founding brief](docs/founding-brief.html)
- [Protocol draft](docs/protocol.md)
- [Publishable discovery index](discovery/README.md)
- [Index schema](schemas/discovery-index.schema.json)
- [Signing profile](docs/signing-profile.md)
- [Matching experiments](docs/matching.md)
- [Delegation and budgets](docs/permissions.md)
- [Signed coordinator routing](docs/routing.md)
- [Editable intentions](docs/intentions.md)
- [Pretrained embedding results](docs/embedding-evaluation.md)
- [Owner-local encrypted discovery](docs/local-discovery.md)
- [Private discovery experiments](docs/private-discovery-experiment.md)
- [Mailbox coordination](docs/coordination.md)
- [Threat model](docs/threat-model.md)
- [Completion audit](docs/completion-audit.md)
- [Independent agent install evidence](docs/agent-install-evidence.md)
- [Release gates](docs/release-gates.md)
- [Implementation roadmap](docs/roadmap.md)
- [Contribution rules](CONTRIBUTING.md)

## Architectural lineage and design reference

[US11711348B2](https://patents.google.com/patent/US11711348B2/en), Begin AI's historical distributed coordinator, and SDK embedding work inform this design. Existing private source has not been copied. Dependency and patent licensing require an explicit decision before public release; no patent grant is implied by access to this repository.

When architecture is uncertain, return to the patent’s detailed design. Preserve independent operation and a stable, versioned signing/verification contract while agents improve explicitly adopted methods. A valid signature alone does not establish protocol compliance or permission.
