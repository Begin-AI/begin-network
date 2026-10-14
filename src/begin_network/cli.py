import argparse
import json
import os
from pathlib import Path
from importlib.resources import files
from urllib.parse import urlsplit
from jsonschema import Draft202012Validator, FormatChecker


def validate_index(value):
    schema = json.loads(files("begin_network").joinpath("schemas/discovery-index.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    for collection in ("methods", "nodes"):
        ids = [entry["id"] for entry in value[collection]]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate identifiers in " + collection)
    for node in value["nodes"]:
        url = urlsplit(node["endpoint"])
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("endpoint must be HTTPS without credentials, query, or fragment")
    return value


def main():
    from .envelope import generate_key, sign, verify, decode, strict_json, ReplayStore
    parser = argparse.ArgumentParser(description="Experimental Begin local runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-index")
    validate.add_argument("path", type=Path)
    keygen = sub.add_parser("keygen")
    keygen.add_argument("path", type=Path)
    signer = sub.add_parser("sign")
    signer.add_argument("--key", required=True, type=Path)
    signer.add_argument("--payload", required=True, type=Path)
    verifier = sub.add_parser("verify")
    verifier.add_argument("--keys", required=True, type=Path, help="Locally trusted kid-to-base64url-public-key map")
    verifier.add_argument("--token", required=True, type=Path)
    verifier.add_argument("--audience", required=True)
    verifier.add_argument("--replay-db", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "validate-index":
            value = validate_index(strict_json(args.path.read_bytes()))
            print("Valid index structure: %d methods, %d nodes. Trust and privacy are not verified." % (len(value["methods"]), len(value["nodes"])))
        elif args.command == "keygen":
            key = generate_key()
            fd = os.open(args.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as stream:
                json.dump(key, stream)
            print(json.dumps({"kid": key["kid"], "public": key["public"]}))
        elif args.command == "sign":
            key = strict_json(args.key.read_bytes())
            print(sign(strict_json(args.payload.read_bytes()), decode(key["private"])))
        elif args.command == "verify":
            keys = {kid: decode(public) for kid, public in strict_json(args.keys.read_bytes()).items()}
            replay = ReplayStore(str(args.replay_db))
            try:
                payload = verify(args.token.read_text().strip(), keys, args.audience, replay=replay)
                print(json.dumps({"checks": ["signature", "profile", "fields", "audience", "expiry", "replay"],
                                  "permission_checked": False, "envelope": payload}))
            finally:
                replay.close()
    except Exception as exc:
        parser.exit(1, "Rejected: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
