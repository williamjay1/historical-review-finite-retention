"""Independent finite-world audit of the closed-block online adapter.

Writes only online_independent_audit* files beside this script.  It enumerates
support worlds directly from decoded files, without core._state/_compatible.
"""
from pathlib import Path
import hashlib, itertools, json, re, sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import review_online_20261023 as online
import review_archive_core_20261023 as core

OUT=Path(__file__).resolve().parent

def records(h,rng):
    ti,ch=np.nonzero(h);a=np.empty(len(ti),core.ATOM)
    a['t']=ti;a['ch']=ch;a['v']=ti//3
    a['q']=rng.choice(np.asarray([1.,1.25,2.,2.5],np.float32),len(a))
    a['x']=rng.normal(size=len(a)).astype(np.float32)
    return a

def read_snapshot(path):
    raw=path.read_bytes()
    magic,now,hs,n=online.FRAME.unpack_from(raw)
    assert magic==b'ONRV1023'
    header=json.loads(raw[online.FRAME.size:online.FRAME.size+hs])
    directory=online.FRAME.size+hs
    entries=[online.ENTRY.unpack_from(raw,directory+i*online.ENTRY.size) for i in range(n)]
    cursor=directory+n*online.ENTRY.size;last=-1;parts=[]
    for lo,hi,offset,size,kind in entries:
        assert lo>=last and lo<hi<=now
        assert offset==cursor and offset+size<=len(raw)
        ar=core.decode_payload(raw[offset:offset+size],header,online.DECODE[kind])
        assert ar.start==lo and ar.stop==hi
        parts.append(ar);cursor+=size;last=hi
    assert cursor==len(raw)
    return now,parts,len(raw)

def compatible(parts,w,ch):
    for ar in parts:
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

def formal_directory_check():
    files=0;entries_total=0;max_fraction=0.0
    for path in (OUT/'online_snapshots').glob('*.arc'):
        match=re.search(r'_(\d+)_(full|bitmap_change|coverage_summary|adaptive)_b(\d+)(?:_(\d+))?\.arc$',path.name)
        if not match:continue
        budget=int(match[1]);raw=path.read_bytes()
        magic,now,hs,n=online.FRAME.unpack_from(raw)
        assert magic==b'ONRV1023' and len(raw)<=budget
        header=json.loads(raw[online.FRAME.size:online.FRAME.size+hs])
        assert int(header['n_cycles'])==now
        base=online.FRAME.size+hs;cursor=base+n*online.ENTRY.size;last=-1
        for i in range(n):
            lo,hi,offset,size,kind=online.ENTRY.unpack_from(raw,base+i*online.ENTRY.size)
            assert 0<=lo<hi<=now and lo>=last
            assert offset==cursor and offset+size<=len(raw) and kind in online.DECODE
            body=core.BODY.unpack_from(raw,offset)
            assert int(body[1])==lo and int(body[2])==hi
            assert core.BODY.size+sum(body[5:])==size
            cursor+=size;last=hi;entries_total+=1
        assert cursor==len(raw)
        files+=1;max_fraction=max(max_fraction,len(raw)/budget)
    return dict(files=files,directory_entries=entries_total,max_capacity_fraction=max_fraction,
                byte_or_overlap_violations=0)

def main():
    rng=np.random.default_rng(2026102302);checks=0;conditions=0
    expirations=0;rejections=0;partial_scopes=0;poison_checks=0;prefix_checks=0
    for case in range(2):
        n=8;c=2;h=rng.random((n,c))<.75
        h[0,:]=True;h[-1,:]=True
        u=np.ones(n,bool);a=records(h,rng)
        head=dict(n_cycles=n,channels=['a','b'],threshold=1.0)
        s=dict(h=h,a=a,eligible=u,header=head)
        for B in (300,500,1000):
            for method in online.METHODS:
                path=OUT/f'online_independent_audit_c{case}_{B}_{method}.arc'
                ar=online.Online(s,B,method,path)
                for lo,hi in ((0,2),(2,4),(4,6),(6,8)):
                    ar.close(lo,hi)
                    now,parts,size=read_snapshot(path)
                    assert now==hi and size==ar.size() and size<=B
                    conditions+=1
                    worlds=np.asarray(list(itertools.product((0,1),repeat=hi)),np.int8)
                    # Poison every preloaded observation after file creation.
                    # Query must rely solely on disk plus diagnostic row flags.
                    source=ar.s;ar.s=None
                    try:
                        for ch in range(c):
                            poss=worlds[[compatible(parts,w,ch) for w in worlds]]
                            assert len(poss)>0
                            nums=np.concatenate([p.numeric[p.numeric['ch']==ch] for p in parts]) if parts else np.empty(0,core.ATOM)
                            retained={int(z['t']) for z in nums}
                            for subset in worlds:
                                idx=np.flatnonzero(subset);r=ar.query(idx,ch)
                                counts=poss[:,idx].sum(1)
                                expected='yes' if counts.min()>0 else 'no' if counts.max()==0 else 'unknown'
                                firsts=[int(idx[np.flatnonzero(w[idx])[0]]) for w in poss if w[idx].any()]
                                certfirst=bool(counts.min()>0 and len(set(firsts))==1)
                                patterns={tuple(int(t) for t in idx[w[idx].astype(bool)]) for w in poss}
                                report=bool(len(patterns)==1 and all(t in retained for t in next(iter(patterns))))
                                assert r['answer']==expected,(case,B,method,hi,ch,idx,r,expected)
                                assert r['first_certified']==certfirst
                                assert not certfirst or r['first_cycle']==firsts[0]
                                assert r['first_numeric_joint']==bool(certfirst and firsts[0] in retained)
                                assert r['complete_report']==report
                                actual=a[(a['ch']==ch)&np.isin(a['t'],idx)]
                                if report:assert r['numeric'].tobytes()==actual.tobytes()
                                partial_scopes+=int(r['cross_boundary'])
                                checks+=1;poison_checks+=1
                    finally:ar.s=source
                expirations+=ar.evictions;rejections+=ar.rejections
                # Future changes cannot alter the first closed prefix file.
                changed=h.copy();changed[2:]=~changed[2:]
                changed_a=records(changed,rng)
                changed_a=np.concatenate((a[a['t']<2],changed_a[changed_a['t']>=2]))
                s2=dict(h=changed,a=changed_a,eligible=u.copy(),header=head.copy())
                one=online.Online(s,B,method,OUT/f'online_independent_audit_prefix1_{case}_{B}_{method}.arc')
                two=online.Online(s2,B,method,OUT/f'online_independent_audit_prefix2_{case}_{B}_{method}.arc')
                one.close(0,2);two.close(0,2)
                assert one.path.read_bytes()==two.path.read_bytes()
                prefix_checks+=1
    result=dict(random_streams=2,channels=2,n_cycles=8,budgets=[300,500,1000],
        snapshot_conditions=conditions,all_subset_query_checks=checks,poisoned_source_query_checks=poison_checks,
        future_perturbation_prefix_checks=prefix_checks,evictions=expirations,rejections=rejections,
        partially_covered_query_checks=partial_scopes,false_or_avoidable_certificates=0,
        formal_directory_check=formal_directory_check(),
        online_sha256=hashlib.sha256(Path(online.__file__).read_bytes()).hexdigest(),
        core_sha256=hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest(),
        independent_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'online_independent_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
