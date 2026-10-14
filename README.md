# Begin network

Private development seed for voluntary human and AI coordination.
Originating vision: Rima Al Shikh · Begin AI.

Begin turns purpose-bound intentions into willing connections and scoped action.
Any participant may initiate. Every participant chooses. Authority stays bounded.

## Status

Experimental protocol/runtime under private development. Implemented: Ed25519 envelopes, direct and attenuated delegated grants, persistent atomic resource accounting, receiver-bound sealed content, owner-local encrypted-query matching, editable intention contracts, durable mailboxes, signed routing, public-index validation, replaceable signed bootstrap, and a bounded fixture executor with encrypted signed results. Independent agent installation, Python/Node signature interoperability, three-process coordinator routing/failover and a pretrained embedding benchmark have recorded evidence.

The owner-local path reveals the authorized query to the counterpart and is **not full private semantic discovery**. The learned embedding benchmark still falsely matches negation, refusal and aspiration-as-capability. Complete key release, adaptive-probing defenses, cross-host secure transport, recovery semantics and publication licensing remain unfinished. No P1–E4 gate is claimed fully passed. This repository remains private.

## Run

Python 3.9.2+ and `jsonschema[format-nongpl]>=4.18,<5`:

```sh
python3 -m pip install --require-hashes -r requirements.lock
python3 -m pip install --no-deps .
begin-network capabilities
begin-network validate-index discovery/index.json
python3 -m unittest discover -s tests -v
python3 examples/goal_exchange_demo.py
```

The example index contains methods and schemas, with **zero operating nodes**. It makes no network activity claims.

## Contents

- [Complete synthetic goal exchange](docs/goal-exchange.md)
- [Three-process useful goal](docs/goal-processes.md)
- [Bounded executor and result contract](docs/execution.md)
- [Signed discovery bootstrap](docs/discovery-bootstrap.md)
- [Experimental release audit](docs/release-audit.md)
- [Requirement checklist](docs/release-checklist.md)
- [Independent candidate audit](docs/candidate-audit.md)
- [Candidate download trial](docs/candidate-agent-evidence.md)
- [Local runtime adapter](docs/runtime-adapter.md)
- [Security status](SECURITY.md)
- [Pending license decision](LICENSE-DECISION.md)
- [Dependency inventory](docs/dependencies.md)
- [Patent design map](docs/patent-design-map.md)
- [Charter](docs/charter.md)
- [Activity definitions](docs/activity.md)
- [Linux CI evidence](docs/ci-evidence.md)
- [Remote agent trial](docs/remote-agent-evidence.md)
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
