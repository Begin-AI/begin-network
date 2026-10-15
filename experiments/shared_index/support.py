"""Local source identity; no remote executable method selection."""
import hashlib
from pathlib import Path
from begin_network import envelope, shared_index, introductions, sealed, runtime_bridge, intentions, encoders, local_discovery


def source_hashes():
    files = [Path(__file__), Path(__file__).with_name('party.py')]
    files += [Path(module.__file__) for module in
              (envelope, shared_index, introductions, sealed, runtime_bridge, intentions, encoders, local_discovery)]
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
