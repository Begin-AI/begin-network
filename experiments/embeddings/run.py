"""Run frozen synthetic goal-pair benchmark; optional heavyweight dependencies only."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from begin_network.matching import Intention, represent, compare
from huggingface_hub import HfApi, snapshot_download
from sentence_transformers import SentenceTransformer

MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
CORPUS = Path(__file__).with_name('corpus.json')
RESULTS = Path(__file__).with_name('results.json')


def eligible(case):
    a, b = case['query'], case['candidate']
    if not a['consent'] or not b['consent']: return 'declined'
    if a['purpose'] != b['purpose']: return 'purpose'
    if a['language'] != b['language']: return 'language'
    if a['location'] != b['location']: return 'location'
    if max(a['start'],b['start']) >= min(a['end'],b['end']): return 'timing'
    # Task-specific fixture roles, not a definition of Window or Social.
    if (a['role'],b['role']) not in [('seek','offer'),('peer','peer')]: return 'role'
    return None


def baseline(case, method):
    reps=[]
    for side in ('query','candidate'):
        item=case[side]
        reps.append(represent(Intention(side,item['purpose'],item['text'],item['role'],
                                           item['language'],item['location'],item['consent']),method))
    return compare(*reps).score


def main():
    corpus=json.loads(CORPUS.read_text())
    # Freeze hub revision on the first run, reuse exact revision thereafter.
    revision_file=Path(__file__).with_name('model-revision.txt')
    revision=revision_file.read_text().strip() if revision_file.exists() else HfApi().model_info(MODEL).sha
    revision_file.write_text(revision+'\n')
    snapshot=Path(snapshot_download(MODEL,revision=revision,allow_patterns=['*.json','*.txt','*.safetensors','1_Pooling/*']))
    model=SentenceTransformer(str(snapshot),device='cpu',trust_remote_code=False)
    texts=[case[side]['text'] for case in corpus['cases'] for side in ('query','candidate')]
    embeddings=model.encode(texts,normalize_embeddings=True,show_progress_bar=False)
    output={method:{'counts':dict(tp=0,fp=0,tn=0,fn=0),'cases':[]} for method in corpus['thresholds']}
    for i,case in enumerate(corpus['cases']):
        gate=eligible(case)
        scores={m:baseline(case,m) for m in ('lexical-v1','concept-v1')}
        scores['all-MiniLM-L6-v2']=float(embeddings[2*i] @ embeddings[2*i+1])
        for method,score in scores.items():
            prediction=not gate and score>=corpus['thresholds'][method]
            expected=case['expected_match']
            key=('t' if prediction==expected else 'f')+('p' if prediction else 'n')
            output[method]['counts'][key]+=1
            output[method]['cases'].append(dict(id=case['id'],score=score,gate=gate,predicted_match=bool(prediction),expected_match=expected))
    files={str(p.relative_to(snapshot)):hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.rglob('*') if p.is_file()}
    report=dict(corpus_sha256=hashlib.sha256(CORPUS.read_bytes()).hexdigest(),model=MODEL,revision=revision,
                model_files_sha256=files,dimension=int(embeddings.shape[1]),normalization='l2',device='cpu',
                python=sys.version,platform=platform.platform(),thresholds=corpus['thresholds'],
                dependencies={d.metadata['Name']:d.version for d in importlib.metadata.distributions()},results=output)
    RESULTS.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({m:r['counts'] for m,r in output.items()},indent=2))

if __name__=='__main__':main()
