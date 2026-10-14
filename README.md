# Begin network

Private development seed for voluntary human and AI coordination.
Originating vision: Rima Al Shikh · Begin AI.

Begin turns purpose-bound intentions into willing connections and scoped action.
Any participant may initiate. Every participant chooses. Authority stays bounded.

## Status

Experimental specification and executable public-index validation only. No live discovery service, private semantic matching, authorization verifier, remote runner, or personal-data participation is implemented. No P1–E4 gate is claimed as passing. This repository is private until explicitly approved for publication.

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
- [Release gates](docs/release-gates.md)
- [Implementation roadmap](docs/roadmap.md)
- [Contribution rules](CONTRIBUTING.md)

## Architectural lineage

[US11711348B2](https://patents.google.com/patent/US11711348B2/en), Begin AI's historical distributed coordinator, and SDK embedding work inform this design. Existing private source has not been copied. Dependency and patent licensing require an explicit decision before public release; no patent grant is implied by access to this repository.
