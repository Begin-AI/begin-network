import unittest
from run import corpus, plain

class PredicateTests(unittest.TestCase):
    def test_fixed_gold_cases(self):
        cases = corpus()
        expected = [True, True, False, False, False, False, False, False, False, False]
        self.assertEqual([plain(a,b) for _,a,b in cases], expected)

    def test_private_constraint_cannot_be_overridden_by_score(self):
        _, left, right = corpus()[0]
        right[:96] = [1000]*96
        right[98] = 0
        self.assertFalse(plain(left,right))


class SignedPreflightTests(unittest.TestCase):
    def reject_all_parties(self, mode):
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        from run import agreement, HERE, fixture
        ports=[56001,56002,56003]
        config=agreement(ports,1,expired=mode=='expired',
                         consent_digest_overrides={2:'0'*64} if mode=='mismatched_consent' else None)
        if mode=='circuit_hash':config['session']['party_source_sha256']='0'*64
        if mode=='unsigned':config['consents'].pop()
        for party in range(3):
            with self.subTest(mode=mode,party=party),tempfile.TemporaryDirectory() as scratch:
                data=dict(config,party=party,rows=[fixture(role=party) if party<2 else None])
                Path(scratch,'input.json').write_text(json.dumps(data))
                command=[sys.executable,str(HERE/'party.py'),'-I',str(party),'-T','1']
                for port in ports:command+=['-P','127.0.0.1:'+str(port)]
                result=subprocess.run(command,cwd=scratch,capture_output=True,text=True,timeout=6)
                output=result.stdout+result.stderr
                self.assertNotEqual(result.returncode,0,output)
                self.assertNotIn('PREFLIGHT_OK',output)
                self.assertNotIn('Start MPyC',output)
                reasons={'circuit_hash':'session circuit hash mismatch','unsigned':'unanimous consent required',
                         'expired':'expired/future session','mismatched_consent':'mismatched session consent'}
                self.assertIn(reasons[mode],output)

    def test_changed_circuit_aborts_before_start(self): self.reject_all_parties('circuit_hash')
    def test_unsigned_session_aborts_before_start(self): self.reject_all_parties('unsigned')
    def test_mismatched_consent_aborts_before_start(self): self.reject_all_parties('mismatched_consent')
    def test_expired_session_aborts_before_start(self): self.reject_all_parties('expired')

if __name__ == '__main__': unittest.main()
