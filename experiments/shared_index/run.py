"""Run synthetic acceptance checks and save public, input-free evidence."""
import argparse
import json
from pathlib import Path
import platform
import time
import unittest

from test_shared_index import SharedIndexTests, MEASUREMENTS
from support import source_hashes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SharedIndexTests)
    names = [test.id() for test in suite]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'experiment': 'begin-shared-index-v1', 'synthetic_only': True,
              'python': platform.python_version(), 'platform': platform.platform(),
              'source_hashes': source_hashes(), 'tests': names, 'tests_run': result.testsRun,
              'successful': result.wasSuccessful(), 'measurements': MEASUREMENTS,
              'wall_seconds': time.perf_counter()-started,
              'trust': 'three passive MPC nodes, at most one passively corrupt; not malicious security',
              'deployment': 'same-host processes; fixture controller knows all inputs; no OS isolation',
              'client_integration': 'Python participant API for new candidate search; live GPT/Claude not migrated'}
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    raise SystemExit(not result.wasSuccessful())


if __name__ == '__main__':
    main()
