"""Actual pinned local embedding -> secret shares -> conditional introduction.

Compares the quantized circuit with its plaintext predicate, not human relevance.
The model manifest is an operator input and the loader refuses downloads.
"""
import argparse
import json
from pathlib import Path
import tempfile
import time

from begin_network.encoders import LocalMiniLM
from begin_network.runtime_bridge import Participant
from begin_network.shared_index import private_row, fingerprint
from harness import Committee
from support import source_hashes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-config', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.model_config.read_text())
    encoder = LocalMiniLM(config['directory'], config['file_hashes'])
    now = int(time.time())
    with tempfile.TemporaryDirectory(prefix='begin-shared-model-') as folder:
        root = Path(folder)
        committee = Committee(root / 'pool')
        people = []
        try:
            for name, role, text in [('requester', 'seek', 'synthetic guitar'), ('guitar', 'offer', 'synthetic guitar'),
                                     ('piano', 'offer', 'synthetic piano')]:
                person = Participant(root / name, encoder=encoder)
                person.set_intention('intention', purpose='window', role=role, facts=[], aspirations=[text], inferences=[],
                    available_from=now, available_until=now+600, expires_at=now+900, consent=True, disclosure=['aspirations'])
                people.append(person)
            _, query = people[0].representation('intention')
            quantized = private_row(query, minimum_score=950000)
            expected = []
            for person in people[1:]:
                committee.enroll(person, 'intention', minimum_score=950000)
                _, representation = person.representation('intention')
                other = private_row(representation, minimum_score=950000)
                expected.append(sum(a*b for a,b in zip(quantized[:384], other[:384])) >= 950000)
            cards, *_ = committee.search(query, people[0], minimum_score=950000)
            found = {card['identity']['address'] for card in cards}
            actual = [person.id in found for person in people[1:]]
            if expected != actual:
                raise AssertionError('MPC and quantized plaintext predicate disagree')
            report = {'experiment': 'shared-index-pinned-minilm', 'model': encoder.model, 'method': encoder.method,
                      'dimensions': 384, 'model_manifest_sha256': fingerprint(config['file_hashes']),
                      'source_hashes': source_hashes(), 'expected_predicates': expected, 'actual_predicates': actual,
                      'predicate_equivalence': True, 'semantic_quality_evaluated': False,
                      'parties': committee.last_metrics, 'synthetic_only': True,
                      'deployment': 'same-host test harness, local model; separate MPC processes over mutual TLS'}
            args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        finally:
            committee.close()
            for person in people:
                person.close()


if __name__ == '__main__':
    main()
