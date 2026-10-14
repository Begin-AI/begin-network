import argparse
import json
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
    parser = argparse.ArgumentParser(description="Validate public Begin discovery index structure only")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-index")
    validate.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        value = validate_index(json.loads(args.path.read_text()))
    except Exception as exc:
        parser.exit(1, "Invalid index: " + str(exc) + "\n")
    print("Valid index structure: %d methods, %d nodes. Trust and privacy are not verified." % (len(value["methods"]), len(value["nodes"])))


if __name__ == "__main__":
    main()
