"""Actual separate-process signed, authorized, bounded goal execution."""
import copy
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

from begin_network.envelope import Rejected, ReplayStore, decode, encode
from begin_network.execution import receive_result

SPEC = importlib.util.spec_from_file_location('goal_process_demo',Path(__file__).resolve().parents[1]/'examples'/'goal_process_demo.py')
DEMO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMO)


class GoalProcessTests(unittest.TestCase):
    def test_worker_executes_in_distinct_process_and_cached_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            with DEMO.GoalProcessNetwork(directory) as network:
                result = network.run()
                pids = list(result['processes'].values())
                self.assertEqual(len(set(pids)),3)
                self.assertNotIn(os.getpid(),pids)
                self.assertEqual(result['worker_pid'],network.children[0].pid)
                self.assertEqual(result['verified_output'],{'slots':[[570,600],[800,840]]})
                self.assertEqual(result['completed_executions'],1)
                self.assertEqual(result['budget_spent'],{'mentor-root':1,'mentor-requester':1})
                self.assertTrue(result['offline_retrieval_verified'])
                self.assertFalse(result['duplicate_reexecuted'])
            self.assertTrue(all(child.poll() is not None for child in network.children))

    def test_tampered_attached_input_has_no_successful_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            with DEMO.GoalProcessNetwork(directory) as network:
                attachment = copy.deepcopy(network.attachment())
                raw = bytearray(decode(attachment['sealed_input']['ciphertext']))
                raw[0] ^= 1
                attachment['sealed_input']['ciphertext'] = encode(raw)
                with self.assertRaises(Rejected): network.submit(attachment)
                stats = DEMO.post(network.nodes['worker']['url']+'/stats',{})
                self.assertEqual(stats['completed_executions'],0)
                self.assertEqual(stats['budget_spent'],{})
                with self.assertRaises(Rejected): network.retry()

    def test_direct_worker_endpoint_cannot_admit_new_goal(self):
        with tempfile.TemporaryDirectory() as directory:
            with DEMO.GoalProcessNetwork(directory) as network:
                with self.assertRaises(Rejected): network.retry()
                self.assertEqual(DEMO.post(network.nodes['worker']['url']+'/stats',{})['completed_executions'],0)

    def test_routing_replay_rejected_but_worker_retry_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            with DEMO.GoalProcessNetwork(directory) as network:
                first = network.submit()
                with self.assertRaises(Rejected): network.submit()
                duplicate = network.retry()
                self.assertTrue(duplicate['result']['duplicate'])
                self.assertEqual(duplicate['result']['token'],first['result']['token'])
                self.assertEqual(duplicate['result']['box'],first['result']['box'])
                self.assertEqual(duplicate['completed_executions'],1)

    def test_signed_result_rejects_wrong_original_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            with DEMO.GoalProcessNetwork(directory) as network:
                result = network.submit()['result']
                scenario = network.scenario
                wrong = copy.deepcopy(scenario['request'])
                wrong['id'] = 'another-validly-signed-goal'
                wrong_token = DEMO.GOAL.signed(scenario['keys']['requester'],wrong)
                replay = ReplayStore(Path(directory)/'requester-test-replay.sqlite')
                options = {'worker_keys':{scenario['keys']['worker']['kid']:decode(scenario['keys']['worker']['public'])},
                    'requester_keys':{scenario['keys']['requester']['kid']:decode(scenario['keys']['requester']['public'])},
                    'expected_grant_tokens':scenario['grant_tokens'],
                    'audience':scenario['keys']['requester']['kid'],
                    'recipient_private':decode(scenario['requester_encryption']['private']),
                    'replay':replay,'now':DEMO.GOAL.NOW}
                try:
                    with self.assertRaises(Rejected):
                        receive_result(result['token'],result['box'],request_token=wrong_token,**options)
                    accepted = receive_result(result['token'],result['box'],request_token=scenario['request_token'],**options)
                    self.assertEqual(accepted['output']['slots'],[[570,600],[800,840]])
                finally: replay.close()
