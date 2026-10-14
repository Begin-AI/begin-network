"""Published structural contracts validated against actual generated goal bodies."""
import copy
import importlib.util
from importlib.resources import files
import json
from pathlib import Path
import tempfile
import unittest
from jsonschema import Draft202012Validator, ValidationError
from begin_network.envelope import verify, validate_task_body, Rejected
from begin_network.permissions import _scope

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('schema_goal_exchange',ROOT/'examples/goal_exchange_demo.py')
DEMO=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMO)

class ProtocolSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validators={}
        for name in ('bounded-task','delegation-grant','task-result'):
            schema=json.loads((ROOT/'schemas'/(name+'.schema.json')).read_text())
            Draft202012Validator.check_schema(schema)
            cls.validators[name]=Draft202012Validator(schema)
        with tempfile.TemporaryDirectory() as directory:
            scenario=DEMO.prepare(directory)
            cls.task=copy.deepcopy(scenario['request']['body'])
            cls.grants=[verify(token,scenario['trusted'],scenario['keys']['worker']['kid'],now=DEMO.NOW) for token in scenario['grant_tokens']]
            ledger,worker=DEMO.open_worker(scenario)
            try:
                output=worker.execute(scenario['request_token'],scenario['grant_tokens'],scenario['sealed_input'],now=DEMO.NOW)
                cls.result=verify(output['token'],scenario['trusted'],scenario['keys']['requester']['kid'],now=DEMO.NOW)['body']
            finally:ledger.close()

    def rejects(self,name,body):
        with self.assertRaises(ValidationError):self.validators[name].validate(body)

    def test_actual_goal_task_delegations_and_result_validate(self):
        self.validators['bounded-task'].validate(self.task)
        self.assertEqual(validate_task_body(self.task),self.task)
        for grant in self.grants:
            self.validators['delegation-grant'].validate(grant['body'])
            self.assertEqual(_scope(grant),grant['body'])
        self.validators['task-result'].validate(self.result)

    def test_minimum_task_and_all_optional_fields(self):
        task={k:v for k,v in self.task.items() if k not in ('routing','sealed_digest')}
        self.validators['bounded-task'].validate(task)
        for key in ('routing','sealed_digest'):
            candidate=dict(task,**{key:self.task[key]})
            self.validators['bounded-task'].validate(candidate)

    def test_task_types_limits_and_unknown_fields(self):
        changes=[('units',True),('units',-1),('units',1000000001),('purpose',''),('action',[]),('resource',False),('extra','unknown'),('sealed_digest','A'*64),('sealed_digest','0'*64+'\n')]
        for key,value in changes:
            candidate=dict(self.task,**{key:value})
            with self.subTest(key=key,value=value):
                self.rejects('bounded-task',candidate)
                with self.assertRaises(Rejected):validate_task_body(candidate)
        for routing in ({'ingress':'node','hop_limit':True},{'ingress':'node','hop_limit':0},{'ingress':'node','hop_limit':17},{'ingress':'','hop_limit':1},{'ingress':'node','hop_limit':1,'unsigned_extra':True}):
            candidate=dict(self.task,routing=routing)
            self.rejects('bounded-task',candidate)
            with self.assertRaises(Rejected):validate_task_body(candidate)

    def test_grant_profile_types_limits_and_extra_fields(self):
        body=self.grants[0]['body']
        for key,value in [('profile','unknown'),('depth',True),('depth',9),('depth',-1),('max_units',True),('max_units',1000000001),('actions',[]),('actions',['answer','answer']),('actions',['']),('subject',''),('purpose',{}),('parent',''),('parent',True),('extra','ignored')]:
            candidate=dict(body,**{key:value})
            with self.subTest(key=key,value=value):
                self.rejects('delegation-grant',candidate)
                envelope=dict(self.grants[0],body=candidate)
                with self.assertRaises(Rejected):_scope(envelope)

    def test_result_hashes_profile_status_and_provenance(self):
        for key,value in [('profile','unknown'),('status','pending'),('request_digest',True),('sealed_digest','x'*64),('request_digest','0'*64+'\n'),('grant_digests',[]),('grant_digests',['0'*64]*10),('grant_digests',[False]),('extra','ignored')]:
            with self.subTest(key=key):self.rejects('task-result',dict(self.result,**{key:value}))
        for key,value in [('kind','human-observation'),('method','arbitrary-code'),('resource_revision',''),('extra','ignored')]:
            body=copy.deepcopy(self.result);body['provenance'][key]=value
            with self.subTest(provenance=key):self.rejects('task-result',body)

    def test_required_fields_cannot_be_omitted(self):
        for name,body in [('bounded-task',self.task),('delegation-grant',self.grants[0]['body']),('task-result',self.result)]:
            required=self.validators[name].schema['required']
            for field in required:
                candidate=copy.deepcopy(body);del candidate[field]
                with self.subTest(schema=name,field=field):self.rejects(name,candidate)

    def test_published_and_packaged_copies_identical(self):
        for name in self.validators:
            filename=name+'.schema.json'
            self.assertEqual((ROOT/'schemas'/filename).read_bytes(),files('begin_network').joinpath('schemas/'+filename).read_bytes())

    def test_shape_does_not_claim_authority_or_matching_hash_semantics(self):
        # Structurally correct arbitrary hashes still require runtime binding checks.
        result=dict(self.result,request_digest='0'*64,grant_digests=['f'*64])
        self.validators['task-result'].validate(result)
        unrelated=dict(self.grants[1]['body'],parent='different-parent')
        self.validators['delegation-grant'].validate(unrelated)

if __name__=='__main__':unittest.main()
