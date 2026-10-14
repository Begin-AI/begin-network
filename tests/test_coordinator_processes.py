"""Synthetic independent OS-process HTTP routing evidence; not deployment tests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

from begin_network.envelope import Rejected, decode, encode, strict_json

SPEC = importlib.util.spec_from_file_location('coordinator_process_demo', Path(__file__).resolve().parents[1] / 'examples' / 'coordinator_process_demo.py')
DEMO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMO)


class CoordinatorProcessTests(unittest.TestCase):
    def test_three_process_routing_failover_and_clean_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            with DEMO.ProcessNetwork(directory) as network:
                result = network.run()
                self.assertEqual(len(set(result['processes'])), 3)
                self.assertTrue(result['offline_peer_failover'])
                self.assertEqual(result['verified_original_body']['units'], 1)
                self.assertTrue(all(child.poll() is None for child in network.children))
            self.assertTrue(all(child.poll() is not None for child in network.children))

    def test_signed_payload_tampering_rejected_by_ingress_process(self):
        with tempfile.TemporaryDirectory() as directory:
            with DEMO.ProcessNetwork(directory) as network:
                parts = network.token().split('.')
                payload = strict_json(decode(parts[1]))
                payload['body']['units'] = 999
                import json
                parts[1] = encode(json.dumps(payload).encode())
                with self.assertRaises(Rejected):
                    DEMO.post(network.nodes['a']['url'] + '/submit',
                        {'original':'.'.join(parts), 'destination':network.keys['c']['kid']})
                # Rejection does not admit the invalid operation to replay storage.
                self.assertTrue(network.run()['offline_peer_failover'])

    def test_route_endpoint_refuses_unsigned_packet(self):
        with tempfile.TemporaryDirectory() as directory:
            with DEMO.ProcessNetwork(directory) as network:
                with self.assertRaises(Rejected):
                    DEMO.post(network.nodes['b']['url'] + '/route',
                        {'original':network.token(), 'hops':['unsigned']})
