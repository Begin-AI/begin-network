"""End-to-end synthetic bounded-goal evidence, including failure paths."""
import importlib.util
import copy
from pathlib import Path
import tempfile
import unittest
from begin_network.envelope import Rejected, ReplayStore, decode, encode, generate_key
from begin_network.execution import receive_result

SPEC = importlib.util.spec_from_file_location('goal_exchange_demo', Path(__file__).resolve().parents[1] / 'examples' / 'goal_exchange_demo.py')
DEMO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMO)


class GoalExchangeTests(unittest.TestCase):
    def test_no_match_and_decline_do_not_execute_or_disclose_task(self):
        for options,outcome in (({'mentor_topic':'piano'},'no-match'),({'mentor_consent':False},'declined'),({'requester_consent':False},'declined')):
            with self.subTest(options=options),tempfile.TemporaryDirectory() as directory:
                report=DEMO.run(directory,**options)
                self.assertEqual(report['status'],outcome)
                self.assertEqual(report['executions'],0)
                self.assertFalse(report['full_request_disclosed'])
                self.assertFalse((Path(directory)/'owner-budget.sqlite').exists())

    def test_original_goal_routes_across_independent_signers(self):
        with tempfile.TemporaryDirectory() as directory:
            scenario = DEMO.prepare(directory)
            path = DEMO.route_original(scenario)
            self.assertEqual(path, [scenario['keys']['relay']['kid'], scenario['keys']['worker']['kid']])

    def test_complete_goal_mailbox_return_and_single_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            report = DEMO.run(directory)
            self.assertEqual(report['verified_output'], {'slots':DEMO.EXPECTED_OVERLAPS})
            self.assertEqual(report['provenance'], {'kind':'synthetic-calculation',
                'method':'interval-intersection-v1', 'resource_revision':'fixture-v1'})
            self.assertTrue(report['bootstrap']['attestation_verified'])
            self.assertFalse(report['bootstrap']['authority_granted'])
            self.assertEqual(report['discovery']['outcome'],'proposed')
            self.assertEqual(report['discovery']['representation_kind'],'manual-synthetic-fixture')
            self.assertEqual(report['executions'], 1)
            self.assertEqual(report['budget_spent'], {'mentor-root':1,'mentor-requester':1})
            self.assertTrue(report['offline_retrieval_verified'])
            self.assertFalse(report['duplicate_reexecuted'])

    def test_failed_input_consumes_one_reservation_and_does_not_retry(self):
        from begin_network.sealed import seal, sealed_digest
        import json
        with tempfile.TemporaryDirectory() as directory:
            scenario=DEMO.prepare(directory)
            scenario['sealed_input']=seal(json.dumps({'slots':[[20,20]]}).encode(),decode(scenario['worker_encryption']['public']),
                scenario['request']['id'],scenario['keys']['worker']['kid'])
            scenario['request']['body']['sealed_digest']=sealed_digest(scenario['sealed_input'])
            scenario['request_token']=DEMO.signed(scenario['keys']['requester'],scenario['request'])
            ledger,worker=DEMO.open_worker(scenario)
            try:
                with self.assertRaises(Rejected):worker.execute(scenario['request_token'],scenario['grant_tokens'],scenario['sealed_input'],now=DEMO.NOW)
                retry=worker.execute(scenario['request_token'],scenario['grant_tokens'],scenario['sealed_input'],now=DEMO.NOW)
                self.assertEqual(retry['status'],'failed')
                self.assertTrue(retry['duplicate'])
                self.assertIsNone(retry['token'])
                self.assertEqual(dict(ledger.db.execute('SELECT id,spent FROM grants')),{'mentor-root':1,'mentor-requester':1})
            finally:ledger.close()

    def test_interrupted_reservation_does_not_execute_again(self):
        with tempfile.TemporaryDirectory() as directory:
            scenario=DEMO.prepare(directory)
            ledger,worker=DEMO.open_worker(scenario)
            try:
                self.assertEqual(ledger.reserve(scenario['request_token'],scenario['grant_tokens'],DEMO.NOW),'accepted')
                retry=worker.execute(scenario['request_token'],scenario['grant_tokens'],scenario['sealed_input'],now=DEMO.NOW)
                self.assertEqual(retry['status'],'pending-or-interrupted')
                self.assertIsNone(retry['token'])
                self.assertEqual(ledger.db.execute('SELECT COUNT(*) FROM executions').fetchone()[0],0)
            finally:ledger.close()

    def test_maximum_valid_input_returns_63_bounded_fragments(self):
        from begin_network.sealed import seal,sealed_digest
        import json
        with tempfile.TemporaryDirectory() as directory:
            scenario=DEMO.prepare(directory)
            scenario['sealed_input']=seal(json.dumps({'slots':[[4*i,4*i+3] for i in range(32)]}).encode(),
                decode(scenario['worker_encryption']['public']),scenario['request']['id'],scenario['keys']['worker']['kid'])
            scenario['request']['body']['sealed_digest']=sealed_digest(scenario['sealed_input'])
            scenario['request_token']=DEMO.signed(scenario['keys']['requester'],scenario['request'])
            ledger,worker=DEMO.open_worker(scenario)
            replay=ReplayStore(Path(directory)/'max-results.sqlite')
            try:
                worker.resources['fixture:mentor']['slots']=[[4*i+2,4*i+5] for i in range(32)]
                result=worker.execute(scenario['request_token'],scenario['grant_tokens'],scenario['sealed_input'],now=DEMO.NOW)
                received=receive_result(result['token'],result['box'],worker_keys={scenario['keys']['worker']['kid']:decode(scenario['keys']['worker']['public'])},
                    requester_keys={scenario['keys']['requester']['kid']:decode(scenario['keys']['requester']['public'])},expected_grant_tokens=scenario['grant_tokens'],
                    audience=scenario['keys']['requester']['kid'],recipient_private=decode(scenario['requester_encryption']['private']),
                    request_token=scenario['request_token'],replay=replay,now=DEMO.NOW)
                self.assertEqual(len(received['output']['slots']),63)
            finally:replay.close();ledger.close()

    def test_cached_duplicate_survives_worker_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            scenario = DEMO.prepare(directory)
            ledger, worker = DEMO.open_worker(scenario)
            try:
                first = worker.execute(scenario['request_token'],scenario['grant_tokens'],scenario['sealed_input'],now=DEMO.NOW)
            finally: ledger.close()
            ledger, worker = DEMO.open_worker(scenario)
            try:
                retry = worker.execute(scenario['request_token'],scenario['grant_tokens'],scenario['sealed_input'],now=DEMO.NOW)
                self.assertTrue(retry['duplicate'])
                self.assertEqual(first['token'],retry['token'])
                self.assertEqual(first['box'],retry['box'])
                self.assertEqual(ledger.db.execute('SELECT COUNT(*) FROM executions').fetchone()[0],1)
                self.assertEqual(dict(ledger.db.execute('SELECT id,spent FROM grants')),{'mentor-root':1,'mentor-requester':1})
            finally: ledger.close()

    def test_ciphertext_substitution_rejected_before_budget_spend(self):
        with tempfile.TemporaryDirectory() as directory:
            scenario = DEMO.prepare(directory)
            ledger, worker = DEMO.open_worker(scenario)
            try:
                changed = copy.deepcopy(scenario['sealed_input'])
                raw = bytearray(decode(changed['ciphertext']))
                raw[0] ^= 1
                changed['ciphertext'] = encode(raw)
                with self.assertRaises(Rejected):
                    worker.execute(scenario['request_token'],scenario['grant_tokens'],changed,now=DEMO.NOW)
                self.assertEqual(ledger.db.execute('SELECT COUNT(*) FROM operations').fetchone()[0],0)
            finally: ledger.close()

    def test_ancestor_revocation_blocks_goal_and_cached_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            scenario = DEMO.prepare(directory)
            ledger, worker = DEMO.open_worker(scenario)
            try:
                worker.execute(scenario['request_token'],scenario['grant_tokens'],scenario['sealed_input'],now=DEMO.NOW)
                snapshot = DEMO.envelope(scenario['keys']['owner'],'revocation','new-revocation',scenario['keys']['worker']['kid'],
                    {'profile':DEMO.GRANT_PROFILE,'revoked':['mentor-root']})
                snapshot['issued_at'] = 105
                ledger.apply_revocations(DEMO.signed(scenario['keys']['owner'],snapshot),DEMO.NOW)
                with self.assertRaises(Rejected):
                    worker.execute(scenario['request_token'],scenario['grant_tokens'],scenario['sealed_input'],now=DEMO.NOW)
                self.assertEqual(ledger.db.execute('SELECT COUNT(*) FROM executions').fetchone()[0],1)
            finally: ledger.close()

    def test_result_wrong_worker_tamper_binding_and_replay_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            scenario = DEMO.prepare(directory)
            ledger, worker = DEMO.open_worker(scenario)
            replay = ReplayStore(Path(directory) / 'results.sqlite')
            try:
                result = worker.execute(scenario['request_token'],scenario['grant_tokens'],scenario['sealed_input'],now=DEMO.NOW)
                options = {'worker_keys':{scenario['keys']['worker']['kid']:decode(scenario['keys']['worker']['public'])},
                    'audience':scenario['keys']['requester']['kid'],
                    'recipient_private':decode(scenario['requester_encryption']['private']),
                    'requester_keys':{scenario['keys']['requester']['kid']:decode(scenario['keys']['requester']['public'])},
                    'expected_grant_tokens':scenario['grant_tokens'],
                    'request_token':scenario['request_token'],'replay':replay,'now':DEMO.NOW}
                wrong = generate_key()
                with self.assertRaises(Rejected):
                    receive_result(result['token'],result['box'],**dict(options,worker_keys={wrong['kid']:decode(wrong['public'])}))
                changed = copy.deepcopy(result['box'])
                raw = bytearray(decode(changed['ciphertext'])); raw[0] ^= 1
                changed['ciphertext'] = encode(raw)
                with self.assertRaises(Rejected):receive_result(result['token'],changed,**options)
                with self.assertRaises(Rejected):
                    receive_result(result['token'],result['box'],**dict(options,request_token='unrelated-original'))
                # A different trusted service is not the worker named in the request.
                from begin_network.envelope import strict_json, sign
                altered = strict_json(decode(result['token'].split('.')[1]))
                altered['sender'] = wrong['kid']
                forged = sign(altered,decode(wrong['private']))
                all_workers = dict(options['worker_keys'], **{wrong['kid']:decode(wrong['public'])})
                with self.assertRaises(Rejected):receive_result(forged,result['box'],**dict(options,worker_keys=all_workers))
                with self.assertRaises(Rejected):receive_result(result['token'],result['box'],**dict(options,expected_grant_tokens=['unrelated']))
                accepted = receive_result(result['token'],result['box'],**options)
                self.assertEqual(accepted['output']['slots'],DEMO.EXPECTED_OVERLAPS)
                with self.assertRaises(Rejected):receive_result(result['token'],result['box'],**options)
            finally:
                replay.close()
                ledger.close()
