"""A host can inspect installed CLI scope without generating keys or network traffic."""
import json
import subprocess
import sys
import unittest

class CapabilitiesTests(unittest.TestCase):
    def test_installed_cli_reports_limits_and_grants_no_authority(self):
        result = subprocess.run([sys.executable, '-m', 'begin_network.cli', 'capabilities'],
                                text=True, capture_output=True, timeout=10, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(data['protocol_version'], '0.1-draft')
        self.assertEqual(data['data_policy'], 'synthetic-only')
        self.assertEqual(data['supported_fixture_action'], 'available-overlap')
        for field in ['authority_granted', 'permission_checked', 'live_personal_data_supported',
                      'arbitrary_remote_code_supported', 'secure_public_transport_supported']:
            self.assertIs(data[field], False)
        self.assertTrue(data['envelope_verification'])
        self.assertEqual(result.stderr, '')
