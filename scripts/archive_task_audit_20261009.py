"""Declared interval queries, certified answers and budgeted archive choices.

No detector fitting. Labels construct evaluation scopes after label-blind
representations are built. A reference match is not itself a certificate.
"""
from pathlib import Path
import csv, gzip, hashlib, json, math, struct, time, zlib
import numpy as np
import pandas as pd
import evidence_representation_audit as e

ROOT=e.ROOT
OUT=ROOT/'results/revision_archive_task_20261009'
BUDGETS=[k*1024 for k in (32,64,128,256,512,1024,2048)]
FIXED=struct.Struct('<BII')  # complete-support flag, support bytes, record bytes

def csvwrite(path,rows):
    if not rows:return
    path.parent.mkdir(parents=True,exist_ok=True)
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'wt',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def feature_file(suite,j):
    return ROOT/'datasets'/f"m{j['arguments']['mission']}_full_b10/features_raw.npy" if suite=='ESA' else Path(j['data']['working_directory'])/'features_raw.npy'

def specs(d,selected,h,labels):
    lookup={s:i for i,s in enumerate(selected)};qs=[];stages=[]
    for ident,ev in d['events'].items():
        if ev['category']!='anomaly':continue
        base=dict(incident_id=str(ident),category=ev['category'])
        merged={};prem={}
        if d['unit'] in ('1','2'):
            for full,pre,ch in ev['affected']:
                if ch in lookup:
                    merged.setdefault(ch,[]).append(full);prem.setdefault(ch,[]).append(pre)
        else:
            key=f"{d['unit']}:{ident}";lab=labels.get(key)
            if lab:
                for ch in lab['dimensions0based']:
                    merged[ch]=[ev['active']];prem[ch]=[ev['activepre']]
            for ch in selected:
                ix=np.asarray(ev['active'],dtype=int)
                qs.append(dict(base,family='full_model',channel=lookup[ch],idx=ix))
        for ch,parts in merged.items():
            for family,parts2 in [('full_annotated',parts),('pre_feedback',prem[ch])]:
                ix=np.unique(np.concatenate(parts2)).astype(int)
                qs.append(dict(base,family=family,channel=lookup[ch],idx=ix))
        allix=np.asarray(ev['active'],dtype=int);preix=np.asarray(ev['activepre'],dtype=int)
        target=sorted(lookup[c] for c in merged)
        fullhigh=bool(h[allix].any()) if len(allix) else False
        prehigh=bool(h[preix].any()) if len(preix) else False
        targethigh=any(bool(h[np.unique(np.concatenate(parts)).astype(int),lookup[ch]].any()) for ch,parts in merged.items())
        targetpre=any(bool(h[np.unique(np.concatenate(parts)).astype(int),lookup[ch]].any()) for ch,parts in prem.items())
        stages.append(dict(base,window_opportunity=bool(len(ev['idx'])),active_opportunity=bool(len(allix)),pre_opportunity=bool(len(preix)),annotated_channels=len(target),full_model_high=fullhigh,pre_model_high=prehigh,full_annotated_high=targethigh,pre_annotated_high=targetpre,full_cycles=len(allix),pre_cycles=len(preix),excluded_own_cutoff_cycles=len(allix)-len(preix)))
    # Workload grid chosen without labels or high/low outcomes. Empty and
    # partly unavailable scopes are retained, not replaced with positive ones.
    T,C=h.shape
    for length in (1,10,100,1000):
        for k in range(16):
            lo=int((T-1)*k/15);hi=min(T,lo+length);ch=(k*7+length)%C
            qs.append(dict(incident_id=f'g{length}_{k}',category='grid',family='grid',channel=ch,idx=np.arange(lo,hi,dtype=int)))
    for ch in (0,C-1):qs.append(dict(incident_id=f'empty_{ch}',category='grid',family='grid',channel=ch,idx=np.array([],dtype=int)))
    for q in qs:
        hit=q['idx'][h[q['idx'],q['channel']]]
        q['hits']=hit;q['positive']=bool(len(hit));q['first']=int(hit[0]) if len(hit) else -1
        q['unusable']=int((~d['eligible'][q['idx']]).sum())
    return qs,stages

def make_archive(a,h,hb,header,pp,tau,B,method,fm,cp,packets,bmz,seed=20260927):
    """Common scalar framing, billed coverage and actual files per condition."""
    budget_payload=max(0,B-hb-FIXED.size)
    support=b'';ids=np.empty(0,dtype=int);runkeep=[];width=0
    allids=np.arange(len(a));complete=False;exact_support=False
    if method=='bitmap':
        support=bmz;exact_support=True
    elif method=='full_aos':
        numeric=zlib.compress(a.tobytes(),9);ids=allids;complete=True
    elif method=='firstmax':ids=fm[:budget_payload//16]
    elif method=='change':ids=cp[:budget_payload//16]
    elif method=='bucket':
        _,width,pay=e.m4_buckets(a,len(h),h.shape[1],hb+FIXED.size,B)
        ids=np.flatnonzero(np.isin(a['t'].astype(np.uint64)*h.shape[1]+a['ch'],np.frombuffer(pay[4:],dtype=e.ATOM)['t'].astype(np.uint64)*h.shape[1]+np.frombuffer(pay[4:],dtype=e.ATOM)['ch']))
    elif method=='reservoir':
        cap=budget_payload//16
        ids=np.sort(np.random.default_rng(seed).choice(len(a),min(cap,len(a)),replace=False))
    elif method=='runraw':
        used=0
        for p in packets:
            if used+p['bytes']>budget_payload:break
            runkeep.append(p);used+=p['bytes']
        ids=np.unique(np.concatenate([p['ids'] for p in runkeep])).astype(int) if runkeep else ids
        exact_support=len(runkeep)==len(packets)
    elif method.startswith('bitmap_'):
        support=bmz;exact_support=True;remain=budget_payload-len(bmz)
        cap=max(0,remain//16)
        suffix=method[7:]
        if suffix=='change':ids=cp[:cap]
        elif suffix=='reservoir':ids=np.sort(np.random.default_rng(seed).choice(len(a),min(cap,len(a)),replace=False))
        elif suffix=='bucket':
            _,width,pay=e.m4_buckets(a,len(h),h.shape[1],hb+FIXED.size+len(bmz),B)
            picked=np.frombuffer(pay[4:],dtype=e.ATOM)
            ids=np.flatnonzero(np.isin(a['t'].astype(np.uint64)*h.shape[1]+a['ch'],picked['t'].astype(np.uint64)*h.shape[1]+picked['ch']))
        else:raise ValueError(method)
    else:raise ValueError(method)
    if method!='full_aos':
        numeric=b''.join(p['packed'] for p in runkeep) if method=='runraw' else a[ids].tobytes()
        if 'bucket' in method:numeric=struct.pack('<I',width)+numeric
    if method not in ('bitmap','runraw') and len(ids)==len(a):complete=True;exact_support=True
    if method=='full_aos':exact_support=True
    size=hb+FIXED.size+len(support)+len(numeric)
    feasible=size<=B
    if not feasible:
        # Complete archive/bitmap is declined rather than silently clipped.
        return dict(method=method,bytes=size,feasible=False,ids=np.empty(0,dtype=int),runkeep=[],exact_support=False,complete=False,width=width,file=None,support_h=None)
    meta=dict(header,archive_method=method,archive_contract='v2 declared high-support and numeric atoms')
    # Keep original common header length/cost unchanged; method is identified
    # by file manifest. There is no uncharged enlarged JSON in the file.
    hp=json.dumps(header,sort_keys=True,separators=(',',':')).encode()
    blob=struct.pack('<I',len(hp))+hp+FIXED.pack(int(exact_support),len(support),len(numeric))+support+numeric
    assert len(blob)==size
    folder=OUT/'query_archives'/f"{header['dataset']}_{header['unit']}_{header['backbone']}"
    folder.mkdir(parents=True,exist_ok=True);path=folder/f'{method}_{B}.arc';path.write_bytes(blob)
    data=path.read_bytes();off=4+struct.unpack('<I',data[:4])[0]
    flag,slen,nlen=FIXED.unpack(data[off:off+FIXED.size]);off+=FIXED.size
    assert bool(flag)==exact_support and len(data)==off+slen+nlen
    decoded_support=None
    if slen:
        decoded_support=np.unpackbits(np.frombuffer(zlib.decompress(data[off:off+slen]),dtype=np.uint8).reshape(h.shape[1],-1),axis=1,bitorder='little')[:,:len(h)].T.astype(bool)
        assert np.array_equal(decoded_support,h)
    payload=data[off+slen:]
    if method=='full_aos':restored=np.frombuffer(zlib.decompress(payload),dtype=e.ATOM)
    elif method=='runraw':
        rr=[];offset=0
        while offset<len(payload):
            kind,count=e.FRAME.unpack_from(payload,offset);offset+=e.FRAME.size
            chunk=payload[offset:offset+count];offset+=count
            if kind==0:rr.extend(np.frombuffer(chunk,dtype=e.ATOM))
            else:
                ch,v,first,last,mn,mx,*vals=e.RUN.unpack(chunk)
                for t,q,x in zip((first,last,mn,mx),vals[::2],vals[1::2]):rr.append((t,ch,v,q,x))
        restored=np.unique(np.array(rr,dtype=e.ATOM)) if rr else np.empty(0,e.ATOM)
        restored=np.sort(restored,order=['t','ch'])
    else:restored=np.frombuffer(payload[4:] if 'bucket' in method else payload,dtype=e.ATOM)
    assert np.array_equal(restored,a[ids]),(method,len(restored),len(ids))
    if exact_support and decoded_support is None:
        decoded_support=np.zeros_like(h)
        if method=='runraw':
            for packet in runkeep:decoded_support[packet['first']:packet['last']+1,packet['ch']]=True
        else:decoded_support[restored['t'],restored['ch']]=True
        assert np.array_equal(decoded_support,h)
    return dict(method=method,bytes=size,feasible=True,ids=ids,runkeep=runkeep,exact_support=exact_support,complete=complete,width=width,file=str(path),support_h=decoded_support)

def evaluate(ar,a,h,qs):
    ts=[a['t'][ar['ids']][a['ch'][ar['ids']]==ch] for ch in range(h.shape[1])]
    out=[]
    for q in qs:
        ix=q['idx'];ch=q['channel'];hits=q['hits'];positive=q['positive'];ref=q['first']
        wit=np.intersect1d(ts[ch],ix,assume_unique=True)
        supported=e.run_first(ar['runkeep'],q) if ar['method']=='runraw' else (int(wit[0]) if len(wit) else None)
        if ar['exact_support'] and ar['feasible']:
            decoded_hits=ix[ar['support_h'][ix,ch]]
            supported=int(decoded_hits[0]) if len(decoded_hits) else None
        exact_scope=ar['exact_support'] and ar['feasible']
        empty=not len(ix)
        answer='yes' if supported is not None else ('no' if exact_scope or empty else 'unknown')
        first_cert=supported is not None and (exact_scope or (len(ix) and supported==int(ix[0])))
        false_certificate=(answer=='yes' and not positive) or (answer=='no' and positive) or (first_cert and supported!=ref)
        assert not false_certificate
        wf=bool(len(wit) and ref in wit)
        va=bool(positive and len(wit)==len(hits))
        # Certification uses file-decoded support and retained numeric atoms.
        # va remains an offline fidelity endpoint against the full reference.
        vc=exact_scope and len(decoded_hits)>0 and len(wit)==len(decoded_hits)
        out.append(dict(family=q['family'],incident_id=q['incident_id'],channel=ch,scope_cycles=len(ix),unusable_cycles=q['unusable'],positive=positive,reference_first=ref,retrieved_first=-1 if supported is None else supported,answer=answer,certified_first=first_cert,empirical_first_exact=positive and supported==ref,w_any=bool(len(wit)),w_first=wf,v_all=va,v_certified=vc,high_count=len(hits),numeric_count=len(wit),first_gap_cycles=(supported-ref) if positive and supported is not None else -1,false_certificate=False))
    return out

def summarize(rows,base):
    result=[]
    for family in sorted({x['family'] for x in rows}):
        xx=[x for x in rows if x['family']==family];pos=[x for x in xx if x['positive']];neg=[x for x in xx if not x['positive']]
        result.append(dict(base,family=family,queries=len(xx),positive_queries=len(pos),negative_queries=len(neg),empty_queries=sum(x['scope_cycles']==0 for x in xx),unusable_queries=sum(x['unusable_cycles']>0 for x in xx),certified_yes=sum(x['answer']=='yes' for x in pos),certified_no=sum(x['answer']=='no' for x in neg),unknown=sum(x['answer']=='unknown' for x in xx),certified_first=sum(x['certified_first'] for x in pos),empirical_first_exact=sum(x['empirical_first_exact'] for x in pos),w_any=sum(x['w_any'] for x in pos),w_first=sum(x['w_first'] for x in pos),v_all=sum(x['v_all'] for x in pos),v_certified=sum(x['v_certified'] for x in pos),false_certificate=sum(x['false_certificate'] for x in xx),max_first_gap_cycles=max([x['first_gap_cycles'] for x in pos]+[-1])))
    return result

def run():
    begin=time.perf_counter();OUT.mkdir(exist_ok=True,parents=True)
    labels=json.loads((OUT/'smd_labels/trusted_incident_dimensions.json').read_text())
    metrics=[];events=[];stages=[];costs=[];endpoints=[];drivers=[];random=[];manif=[]
    fits=[(s,p,j) for s,p,j in e.f.receipts() if (j['arguments']['backbone'] if s=='ESA' else j['backbone']) in ('pca','ridge') and (j['arguments']['seed'] if s=='ESA' else j['seed'])==0]
    for count,(suite,p,j) in enumerate(fits,1):
        d,a,h,hb,header,selected,pp,policy,paths=e.load(suite,p,j)
        base=dict(dataset=suite,unit=d['unit'],backbone=d['backbone']);qs,ss=specs(d,selected,h,labels)
        stages.extend([dict(base,**x) for x in ss]);fm,cp=e.summaries(a,pp,d['tau']);packets=e.runs(a)
        bmz=zlib.compress(np.packbits(h.T,axis=1,bitorder='little').tobytes(),9)
        # Actual six-feature extension, without reconstructing an unsaved
        # predictor or attributing causation. Last duplicates are avoided.
        lo=d['lo'] if suite=='ESA' else j['data']['train_blocks']
        ff=np.load(feature_file(suite,j),mmap_mode='r')[lo:lo+len(h)]
        feature_values=np.asarray(ff[a['t'],a['ch']],dtype='<f4')
        assert np.array_equal(feature_values[:,1],a['x'])
        rich=np.empty(len(a),dtype=[('t','<u4'),('ch','<u2'),('v','<u2'),('q','<f4'),('features','<f4',(6,))])
        for field in ('t','ch','v','q'):rich[field]=a[field]
        rich['features']=feature_values
        richsize=hb+FIXED.size+len(zlib.compress(rich.tobytes(),9))
        restored=np.frombuffer(zlib.decompress(zlib.compress(rich.tobytes(),9)),dtype=rich.dtype);assert np.array_equal(restored,rich)
        supportcuts=sum(np.sum(np.diff(a['t'][a['ch']==ch])!=1) for ch in range(h.shape[1]))
        verscuts=sum(np.sum((np.diff(a['t'][a['ch']==ch])==1)&(np.diff(a['v'][a['ch']==ch])!=0)) for ch in range(h.shape[1]))
        costs.append(dict(base,cycles=len(h),channels=h.shape[1],high_atoms=len(a),header_bytes=hb,bitmap_bytes=hb+FIXED.size+len(bmz),full_aos_bytes=hb+FIXED.size+len(zlib.compress(a.tobytes(),9)),rich_aos_bytes=richsize,rich_raw_bytes=hb+FIXED.size+len(rich.tobytes()),firstmax_bytes=hb+FIXED.size+len(fm)*16,change_bytes=hb+FIXED.size+len(cp)*16,runraw_bytes=hb+FIXED.size+sum(x['bytes'] for x in packets),runs=len(packets),support_cuts=int(supportcuts),version_only_cuts=int(verscuts),parent_count=int(pp.max()+1)))
        detail=[]
        methods=['full_aos','bitmap','firstmax','change','bucket','reservoir','runraw','bitmap_change','bitmap_bucket','bitmap_reservoir']
        for B in BUDGETS:
            for method in methods:
                ar=make_archive(a,h,hb,header,pp,d['tau'],B,method,fm,cp,packets,bmz)
                rec=evaluate(ar,a,h,qs);key=dict(base,budget=B,method=method,bytes=ar['bytes'],feasible=ar['feasible'],bucket_width=ar['width'])
                metrics.extend(summarize(rec,key));detail.extend([dict(key,**x) for x in rec])
                manif.append(dict(key,path=ar['file'],complete_support=ar['exact_support'],complete_numeric=ar['complete']))
                for family in ('full_annotated','full_model','pre_feedback'):
                    target={}
                    for x in rec:
                        if x['family']==family and x['positive']:target.setdefault(x['incident_id'],[]).append(x)
                    for ident,rr in target.items():
                        k=len(rr);wa=sum(x['w_any'] for x in rr);wf=sum(x['w_first'] for x in rr)
                        events.append(dict(key,family=family,incident_id=ident,positive_channels=k,w_any_channels=wa,w_first_channels=wf,any_w=wa>0,all_w=wa==k,no_w=wa==0,fraction_w=wa/k))
        # Same original interval identities, expanded cohort and intersections
        # separated. Only full annotated scopes are perturbed, no own cutoff.
        orig=[q for q in qs if q['family']=='full_annotated'];oq={(q['incident_id'],q['channel']) for q in orig if q['positive']}
        for q in orig:
            ix=q['idx'];ex=np.unique(np.r_[ix,ix-1,ix+1]);ex=ex[(ex>=0)&(ex<len(h))];ex=ex[d['eligible'][ex]&d['valid'][ex]]
            hits=ex[h[ex,q['channel']]];ident=(q['incident_id'],q['channel'])
            if not len(hits):cohort='neither_positive'
            elif ident in oq:cohort='intersection'
            else:cohort='new_positive'
            for name,ids in [('firstmax',fm),('change',cp)]:
                wit=np.intersect1d(a['t'][ids][a['ch'][ids]==q['channel']],ex)
                endpoints.append(dict(base,incident_id=q['incident_id'],channel=q['channel'],method=name,cohort=cohort,original_positive=q['positive'],expanded_positive=bool(len(hits)),original_w=e.retained_first(a,ids,q) is not None,expanded_w=bool(len(wit)),original_first=q['first'],expanded_first=int(hits[0]) if len(hits) else -1))
        for q in orig:
            if not q['positive']:continue
            ch=q['channel'];ix=q['idx'];ref=q['first'];par=int(pp[ref]);pi=np.flatnonzero(pp==par)
            witness=e.retained_first(a,fm,q);multi=sum(bool(np.intersect1d(ev['active'],pi).size) for ev in d['events'].values() if ev['category']=='anomaly')
            drivers.append(dict(base,incident_id=q['incident_id'],channel=ch,query_cycles=len(ix),query_highs=len(q['hits']),parent_length=len(pi),parent_anomaly_count=multi,channel_high_density=float(h[:,ch].mean()),firstmax_missing=witness is None,firstmax_first_exact=witness==ref,firstmax_gap=-1 if witness is None else witness-ref))
        # Targeted reservoir variability; repeats are not additional incidents.
        for B in (65536,262144):
            k=min(len(a),max(0,(B-hb-FIXED.size)//16));queries=[q for q in orig if q['positive']]
            for seed in (1,2,3,4,5):
                ids=np.sort(np.random.default_rng(seed).choice(len(a),k,replace=False))
                actual=sum(e.retained_first(a,ids,q) is not None for q in queries)
                def miss(m):
                    if len(a)-m<k:return 0.0
                    if k==0:return 1.0
                    n=len(a);return math.exp(math.lgamma(n-m+1)-math.lgamma(n-m-k+1)-math.lgamma(n+1)+math.lgamma(n-k+1))
                expected=sum(1-miss(len(q['hits'])) for q in queries)
                random.append(dict(base,budget=B,seed=seed,queries=len(queries),retained=actual,expected_retained=expected,N=len(a),k=k))
        csvwrite(OUT/'query_rows'/f'{suite}_{d["unit"]}_{d["backbone"]}.csv.gz',detail)
        print(f'{count}/60 {suite} {d["unit"]} {d["backbone"]}: {len(qs)} queries, {len(a)} atoms',flush=True)
    for name,rows in [('metrics',metrics),('events',events),('stages',stages),('cost',costs),('endpoint_cohorts',endpoints),('failure_drivers',drivers),('reservoir_repeats',random),('archive_manifest',manif)]:csvwrite(OUT/f'{name}.csv',rows)
    result=dict(fits=len(fits),budgets=BUDGETS,metric_rows=len(metrics),event_rows=len(events),archive_conditions=len(manif),actual_files=sum(bool(x['path']) for x in manif),false_certificates=sum(x['false_certificate'] for x in metrics),elapsed_seconds=time.perf_counter()-begin,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'QUERY_COMPLETION.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)

if __name__=='__main__':run()
