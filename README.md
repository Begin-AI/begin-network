# Begin network

Private development seed for voluntary human and AI coordination.
Originating vision: Rima Al Shikh · Begin AI.

Begin turns purpose-bound intentions into willing connections and scoped action.
Any participant may initiate. Every participant chooses. Authority stays bounded.

## Status

Experimental protocol/runtime under private development. Implemented: local Ed25519 signing and envelope checks, direct scoped grants, receiver-bound sealed content, durable local mailboxes, public-index validation, and two synthetic matching baselines. Python/Node crypto interoperability and an independent fresh-install agent trial are recorded in docs. These do not establish a secure live network: private semantic discovery, complete delegation/revocation, multi-node routing, cumulative budgets, and real embedding quality remain unfinished. No P1–E4 gate is claimed fully passing. Repository remains private until explicitly approved for publication.

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
