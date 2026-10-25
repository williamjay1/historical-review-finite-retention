"""Reproducible independent multichannel support-semantics regression.

This preserves the seed and conditions of the earlier 32,768-check inline run.
The oracle reads direct schema constraints, not core._state/_compatible.
"""
from pathlib import Path
import hashlib, itertools, json
import numpy as np
import review_archive_core_20261023 as core

OUT=Path(__file__).resolve().parents[1]/'results/revision_review_20261023'

def compatible(ar,w,ch):
    if ar.support is not None:
        p=ar.support[:,ch];known=p>=0
        if np.any(w[known]!=p[known]):return False
    if np.any(w[ar.usability==0]):return False
    if any(w[int(z['t'])]!=1 for z in ar.numeric if int(z['ch'])==ch):return False
    for g in ar.groups:
        if int(g['ch'])!=ch or not int(g['flags'])&1:continue
        ts=np.flatnonzero(w[int(g['lo']):int(g['hi'])])+int(g['lo'])
        if len(ts)!=int(g['count']):return False
        if len(ts):
            if ts[0]!=int(g['first']) or ts[-1]!=int(g['last']):return False
            if not w[int(g['minimum'])] or not w[int(g['maximum'])]:return False
    return True

def main():
    rng=np.random.default_rng(20261023);n=8;c=2
    worlds=np.asarray(list(itertools.product((0,1),repeat=n)),dtype=np.int8)
    queries=[np.flatnonzero(w) for w in worlds]
    checks=0;archives=0;partial=0;refusals=0
    for case in range(8):
        h=rng.random((n,c))<.65;u=np.ones(n,bool)
        u[~h.any(1)&(rng.random(n)<.5)]=False
        ti,ch=np.nonzero(h);a=np.empty(len(ti),core.ATOM)
        a['t']=ti;a['ch']=ch;a['v']=ti//3
        a['q']=rng.choice(np.asarray([1.,1.25,2.,2.5],np.float32),len(a))
        a['x']=rng.normal(size=len(a)).astype(np.float32)
        head=dict(n_cycles=n,channels=['a','b'],threshold=1.0)
        configs=[('coverage_summary',2,None),('coverage_summary',8,None),
            ('coverage_summary',8,core.frame_bytes(head,'coverage_summary')+core.BODY.size+110),
            ('coverage_fill',3,core.frame_bytes(head,'coverage_fill')+core.BODY.size+150),
            ('bitmap_change',3,None),('bitmap_change_fill',3,core.frame_bytes(head,'bitmap_change_fill')+core.BODY.size+100),
            ('full',3,None),('full',3,core.frame_bytes(head,'full')+core.BODY.size)]
        for method,width,B in configs:
            ar=core.build_archive(a,h,u,head,B,method,width=width)
            assert B is None or ar.size<=B
            assert core.decode_archive(ar.blob).numeric.tobytes()==ar.numeric.tobytes()
            archives+=1;partial+=int(method.startswith('coverage') and len(ar.groups)<c and ar.feasible)
            refusals+=int(not ar.feasible)
            for channel in range(c):
                poss=worlds[[compatible(ar,w,channel) for w in worlds]]
                assert len(poss)>0
                retained={int(z['t']) for z in ar.numeric if int(z['ch'])==channel}
                for idx in queries:
                    r=core.query(ar,idx,channel);counts=poss[:,idx].sum(1)
                    expected='yes' if counts.min()>0 else 'no' if counts.max()==0 else 'unknown'
                    firsts=[int(idx[np.flatnonzero(w[idx])[0]]) for w in poss if w[idx].any()]
                    firstcert=bool(counts.min()>0 and len(set(firsts))==1)
                    pats={tuple(int(t) for t in idx[w[idx].astype(bool)]) for w in poss}
                    report=bool(len(pats)==1 and all(t in retained for t in next(iter(pats))))
                    assert r['answer']==expected,(case,method,channel,idx,r,expected)
                    assert r['min_high_count']==int(counts.min()) and r['max_high_count']==int(counts.max())
                    assert r['first_certified']==firstcert
                    assert not firstcert or r['first_cycle']==firsts[0]
                    assert r['complete_report']==report
                    checks+=1
    result=dict(random_cases=8,channels=c,n_cycles=n,archive_conditions=archives,
        all_subset_query_checks=checks,partial_group_archives=partial,refusal_archives=refusals,
        false_or_avoidable_certificates=0,nonmonotonic_tied_scores=True,
        core_sha256=hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest(),
        independent_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'independent_semantics_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
