"""Review-driven task/retention experiments, frozen inputs, no fitting."""
from pathlib import Path
import argparse, csv, gzip, json, struct, time, hashlib, platform
import numpy as np
import evidence_representation_audit as old
import archive_task_audit_20261009 as tasks
import archive_codec_20261009 as codec

ROOT=old.ROOT;OUT=ROOT/'results/revision_review_20261023'
METHODS=['full','bitmap_change','bitmap_change_fill','coverage_summary','coverage_fill','adaptive_coverage_fill']
BUDGETS=[65536,262144]

def write_csv(path,rows):
    if not rows:return
    path.parent.mkdir(parents=True,exist_ok=True)
    op=gzip.open if path.suffix=='.gz' else open
    with op(path,'wt',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def coarse_fits():
    for suite,p,j in old.f.receipts():
        if (j['arguments']['backbone'] if suite=='ESA' else j['backbone']) not in ('pca','ridge'):continue
        if (j['arguments']['seed'] if suite=='ESA' else j['seed'])!=0:continue
        yield suite,p,j

def load_coarse(suite,p,j):
    d,a,h,hb,header,selected,pp,policy,paths=old.load(suite,p,j)
    labels=json.loads((tasks.OUT/'smd_labels/trusted_incident_dimensions.json').read_text())
    qs,st=tasks.specs(d,selected,h,labels)
    qs=[q for q in qs if q['family'] in ('full_annotated','grid')]
    return dict(dataset=suite,unit=d['unit'],backbone=d['backbone'],cadence='coarse',a=a,h=h,
                eligible=d['eligible'],header=header,queries=qs,stages=st,source=d)

def key(s):return {k:s[k] for k in ['dataset','unit','backbone','cadence']}

def truth(s,idx,ch):
    hits=idx[s['h'][idx,ch]]
    if '_by_channel' not in s:s['_by_channel']={c:s['a'][s['a']['ch']==c] for c in range(s['h'].shape[1])}
    a=s['_by_channel'][ch];aa=a[np.isin(a['t'],idx)]
    return hits,aa

def assess(s,ar,q,core):
    idx=q['idx'];ch=q['channel'];r=core.query(ar,idx,ch)
    hits,aa=truth(s,idx,ch);positive=bool(len(hits));first=int(hits[0]) if positive else -1
    if not hasattr(ar,'_root_numeric'):ar._root_numeric={c:ar.numeric[ar.numeric['ch']==c] for c in range(s['h'].shape[1])}
    channel_numeric=ar._root_numeric[ch]
    numeric=channel_numeric[np.isin(channel_numeric['t'],idx)]
    nr={int(z['t']):z for z in numeric}
    # Tolerance is empirical fidelity, NOT a certificate for discarded values.
    tolerance=False
    if positive:
        target=aa[0]
        tolerance=any(abs(int(z['t'])-first)<=1 and abs(float(z['q'])-float(target['q']))<=.01 and abs(float(z['x'])-float(target['x']))<=.01 and z['v']==target['v'] for z in numeric)
    false=(r['answer']=='yes' and not positive) or (r['answer']=='no' and positive)
    if r['first_certified']:false|=not positive or r['first_cycle']!=first
    if r['first_numeric_joint']:false|=first not in nr or nr[first].tobytes()!=aa[0].tobytes()
    if r['complete_report']:false|=numeric.tobytes()!=aa.tobytes()
    if false:raise AssertionError((key(s),q,r,'false certificate'))
    return dict(family=q.get('family','online'),incident_id=q.get('incident_id',''),channel=ch,
                query_cycles=len(idx),positive=positive,reference_first=first,answer=r['answer'],
                first_certified=r['first_certified'],first_numeric_joint=r['first_numeric_joint'],
                complete_report=r['complete_report'],first_atom_retained=first in nr if positive else False,
                any_numeric=bool(len(numeric)),empirical_tolerance=tolerance,high_count=len(aa),numeric_count=len(numeric),
                unusable_cycles=int((~s['eligible'][idx]).sum()),false_certificate=False)

def summarize(rows,base):
    out=[]
    for family in sorted({r['family'] for r in rows}):
        rr=[r for r in rows if r['family']==family];pos=[r for r in rr if r['positive']];neg=[r for r in rr if not r['positive']]
        out.append(dict(base,family=family,queries=len(rr),positive_queries=len(pos),negative_queries=len(neg),
                        certified_yes=sum(r['answer']=='yes' for r in pos),certified_no=sum(r['answer']=='no' for r in neg),
                        unknown=sum(r['answer']=='unknown' for r in rr),joint_first=sum(r['first_numeric_joint'] for r in pos),
                        first_position=sum(r['first_certified'] for r in pos),first_atom=sum(r['first_atom_retained'] for r in pos),
                        complete_report=sum(r['complete_report'] for r in rr),complete_positive=sum(r['complete_report'] for r in pos),
                        tolerance=sum(r['empirical_tolerance'] for r in pos),any_numeric=sum(r['any_numeric'] for r in pos),
                        unusable_queries=sum(r['unusable_cycles']>0 for r in rr),empty_queries=sum(r['query_cycles']==0 for r in rr),
                        false_certificates=sum(r['false_certificate'] for r in rr)))
    return out

def static_one(s,core):
    base=key(s);costs=[];metrics=[];details=[]
    full=core.build_archive(s['a'],s['h'],s['eligible'],s['header'],2**40,'full')
    complete_bytes=full.size
    for B in BUDGETS:
        for method in METHODS:
            t=time.perf_counter();ar=core.build_archive(s['a'],s['h'],s['eligible'],s['header'],B,method)
            elapsed=time.perf_counter()-t
            ident=dict(base,budget=B,method=method,bytes=ar.size,relative_capacity=B/complete_bytes,
                       full_bytes=complete_bytes,slack=B-ar.size,retained_atoms=len(ar.numeric),
                       unsaved_atoms=len(s['a'])-len(ar.numeric),required_bytes=ar.required_bytes,
                       build_seconds=elapsed,feasible=ar.feasible)
            costs.append(ident)
            folder=OUT/'static'/('_'.join(str(v) for v in base.values()));folder.mkdir(parents=True,exist_ok=True)
            path=folder/f'{method}_{B}.arc';path.write_bytes(ar.blob)
            assert path.stat().st_size==ar.size<=B
            ar=core.decode_archive(path.read_bytes())
            rows=[assess(s,ar,q,core) for q in s['queries']]
            metrics.extend(summarize(rows,ident));details.extend([dict(base,budget=B,method=method,**r) for r in rows])
    name='_'.join(str(v) for v in base.values())
    write_csv(OUT/'static_details'/f'{name}.csv.gz',details)
    return costs,metrics

def clean_header(h,now):
    drop={'n_cycles','review_effective_cycles','review_effective_source_samples','review_sha256','score_sha256','receipt_sha256',
          'packet_types','packet_struct','run_struct','run_witness_order','support_layout','support_bit_order'}
    d={k:v for k,v in h.items() if k not in drop};d['n_cycles']=now
    d['contract']='observed eligible-high stream; input usability retained separately'
    return d

def main():
    ap=argparse.ArgumentParser(description='Coarse static archive comparison. Fine and online have separate drivers.');ap.add_argument('--pilot',action='store_true');args=ap.parse_args()
    import review_archive_core_20261023 as core
    costs=[];metrics=[];begin=time.time()
    for suite,p,j in coarse_fits():
        unit=str(j['arguments']['mission']) if suite=='ESA' else j['entity']
        kind=j['arguments']['backbone'] if suite=='ESA' else j['backbone']
        if args.pilot and not ((suite=='SMD' and unit=='machine-3-4' and kind=='ridge') or (suite=='ESA' and unit=='1' and kind=='ridge')):continue
        s=load_coarse(suite,p,j);cc,mm=static_one(s,core);costs.extend(cc);metrics.extend(mm)
        print(json.dumps(dict(key(s),seconds=round(time.time()-begin,2))),flush=True)
    write_csv(OUT/('static_pilot_costs.csv' if args.pilot else 'static_costs.csv'),costs)
    write_csv(OUT/('static_pilot_metrics.csv' if args.pilot else 'static_metrics.csv'),metrics)
    print('COMPLETE',len(costs),len(metrics),round(time.time()-begin,2),flush=True)

if __name__=='__main__':main()
