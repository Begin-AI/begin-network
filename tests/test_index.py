import copy
import json
from pathlib import Path
import unittest
from jsonschema import ValidationError
from begin_network.cli import validate_index

ROOT = Path(__file__).resolve().parents[1]

class IndexTests(unittest.TestCase):
    def setUp(self):
        self.index = json.loads((ROOT / 'discovery/index.json').read_text())

    def test_seed_has_no_live_nodes(self):
        self.assertEqual(validate_index(self.index)['nodes'], [])

    def test_rejects_private_fields(self):
        for field in ('intentions', 'vectors', 'memberships', 'mailboxes'):
            value = copy.deepcopy(self.index)
            value[field] = []
            with self.assertRaises(ValidationError):
                validate_index(value)

    def test_duplicate_method_ids(self):
        self.index['methods'].append(copy.deepcopy(self.index['methods'][0]))
        with self.assertRaises(ValueError):
            validate_index(self.index)

    def add_node(self):
        self.index['nodes'] = [{'id': 'synthetic-node', 'endpoint': 'https://node.example.org',
            'capabilities': ['discovery'], 'expires_at': '2026-10-15T00:00:00Z',
            'trust': 'unverified-advertisement'}]

    def test_rejects_private_node_fields(self):
        self.add_node()
        self.index['nodes'][0]['participant_ids'] = ['private-person']
        with self.assertRaises(ValidationError):
            validate_index(self.index)

    def test_rejects_credentials_and_query(self):
        self.add_node()
        for endpoint in ('https://user:secret@node.example.org', 'https://node.example.org?secret=value',
                         'https://node.example.org#private', 'http://node.example.org'):
            self.index['nodes'][0]['endpoint'] = endpoint
            with self.assertRaises((ValueError, ValidationError)):
                validate_index(self.index)

    def test_method_contract_and_artifact_paths(self):
        for method in self.index['methods']:
            self.assertTrue((ROOT/method['implementation']).is_file())
        del self.index['methods'][0]['model']
        with self.assertRaises(ValidationError): validate_index(self.index)

    def test_invalid_timestamp(self):
        self.index['generated_at'] = 'yesterday'
        with self.assertRaises(ValidationError):
            validate_index(self.index)

    def test_packaged_schema_matches_published_schema(self):
        self.assertEqual((ROOT / 'schemas/discovery-index.schema.json').read_bytes(),
                         (ROOT / 'src/begin_network/schemas/discovery-index.schema.json').read_bytes())

if __name__ == '__main__':
    unittest.main()
