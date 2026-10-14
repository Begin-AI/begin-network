import tempfile
import unittest
from pathlib import Path
from begin_network.envelope import generate_key, decode, sign, ReplayStore, Rejected, strict_json
from begin_network.routing import Coordinator, Refused


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.keys = {name: generate_key() for name in ('origin', 'a', 'b', 'c', 'd')}
        self.nodes = {}
        self.stores = []
        self.now = 100
        self.transmissions = []

    def tearDown(self):
        for store in self.stores: store.close()
        self.tmp.cleanup()

    def kid(self, name): return self.keys[name]['kid']

    def node(self, name, routes, transport=None, peers=None):
        store = ReplayStore(Path(self.tmp.name) / (name + '.db'))
        self.stores.append(store)
        key = self.keys[name]
        coordinator = Coordinator(decode(key['private']),
            peers if peers is not None else {self.kid(n): decode(self.keys[n]['public']) for n in ('a','b','c','d')},
            {self.kid('origin'): decode(self.keys['origin']['public'])},
            {self.kid(dest): [self.kid(peer) for peer in values] for dest, values in routes.items()},
            store, transport or self.transport, clock=lambda: self.now)
        self.nodes[self.kid(name)] = coordinator
        return coordinator

    def transport(self, peer, packet):
        self.transmissions.append((peer, packet))
        if peer not in self.nodes: raise ConnectionError('offline')
        return self.nodes[peer].receive(packet)

    def original(self, hop_limit=8):
        return sign({'version':'0.1-draft', 'type':'request', 'sender':self.kid('origin'),
            'id':'goal-one', 'audience':self.kid('c'), 'issued_at':100, 'expires_at':200,
            'body':{'goal':'synthetic bounded discovery','routing':{'ingress':self.kid('a'),'hop_limit':hop_limit}}, 'proofs':[]}, decode(self.keys['origin']['private']))

    def test_three_independent_coordinators_and_replay(self):
        a = self.node('a', {'c':['b']})
        self.node('b', {'c':['c']})
        self.node('c', {})
        result = a.submit(self.original(), self.kid('c'))
        self.assertEqual(result['body']['goal'], 'synthetic bounded discovery')
        self.assertEqual(len(self.transmissions), 2)
        with self.assertRaises(Rejected): a.submit(self.original(), self.kid('c'))

    def test_offline_peer_failover(self):
        a = self.node('a', {'c':['d','b']})
        self.node('b', {'c':['c']})
        self.node('c', {})
        self.assertEqual(a.submit(self.original(), self.kid('c'))['id'], 'goal-one')
        self.assertEqual(self.transmissions[0][0], self.kid('d'))

    def test_refusing_peer_failover(self):
        a = self.node('a', {'c':['d','b']})
        self.node('d', {})
        self.node('b', {'c':['c']})
        self.node('c', {})
        self.assertEqual(a.submit(self.original(), self.kid('c'))['id'], 'goal-one')

    def test_unknown_incoming_peer_and_tampering_fail_closed(self):
        packets = []
        a = self.node('a', {'c':['b']}, transport=lambda peer, packet: packets.append(packet))
        a.submit(self.original(), self.kid('c'))
        b = self.node('b', {}, peers={})
        with self.assertRaises(Rejected): b.receive(packets[0])
        b.peers = {self.kid('a'): decode(self.keys['a']['public'])}
        altered = dict(packets[0])
        altered['original'] = altered['original'][:-1] + ('A' if altered['original'][-1] != 'A' else 'B')
        with self.assertRaises(Rejected): b.receive(altered)

    def test_loop_and_hop_limit_refusal(self):
        a = self.node('a', {'c':['b']})
        self.node('b', {'c':['a']})
        with self.assertRaises(Refused): a.submit(self.original(), self.kid('c'))
        self.assertEqual(len(self.transmissions), 1)

    def test_hop_limit_before_destination(self):
        a = self.node('a', {'c':['b']})
        self.node('b', {'c':['c']})
        self.node('c', {})
        with self.assertRaises(Refused): a.submit(self.original(hop_limit=1), self.kid('c'), hop_limit=1)

    def test_expired_in_flight(self):
        packets = []
        a = self.node('a', {'c':['b']}, transport=lambda peer, packet: packets.append(packet))
        a.submit(self.original(), self.kid('c'))
        b = self.node('b', {'c':['c']})
        self.now = 200
        with self.assertRaises(Rejected): b.receive(packets[0])

    def test_validly_signed_forward_cannot_change_original_digest(self):
        packets = []
        a = self.node('a', {'c':['b']}, transport=lambda peer, packet: packets.append(packet))
        a.submit(self.original(), self.kid('c'))
        b = self.node('b', {})
        packet = packets[0]
        payload = strict_json(decode(packet['hops'][0].split('.')[1]))
        payload['body']['original_digest'] = '0' * 64
        changed = {'original':packet['original'], 'hops':[sign(payload, decode(self.keys['a']['private']))]}
        with self.assertRaises(Rejected): b.receive(changed)

    def test_peer_cannot_truncate_ingress_or_expand_origin_hop_limit(self):
        from begin_network.routing import digest
        original=self.original(hop_limit=1)
        b=self.node('b',{})
        c=self.node('c',{})
        hop={'version':'0.1-draft','type':'request','sender':self.kid('b'),'id':'evil-hop',
             'audience':self.kid('c'),'issued_at':100,'expires_at':200,'proofs':[],
             'body':{'original_digest':digest(original),'destination':self.kid('c'),
                     'path':[self.kid('b')],'hop_limit':8,'parent_digest':digest(original)}}
        with self.assertRaises(Refused):c.receive({'original':original,'hops':[sign(hop,decode(self.keys['b']['private']))]})
        hop['body']['hop_limit']=1
        with self.assertRaises(Refused):c.receive({'original':original,'hops':[sign(hop,decode(self.keys['b']['private']))]})

    def test_malformed_inner_hop_is_rejected(self):
        packets = []
        a = self.node('a', {'c':['b']})
        self.node('b', {'c':['c']}, transport=lambda peer, packet: packets.append(packet))
        a.submit(self.original(), self.kid('c'))
        c = self.node('c', {})
        packet = {'original':packets[0]['original'], 'hops':['bad', packets[0]['hops'][-1]]}
        with self.assertRaises(Rejected): c.receive(packet)
