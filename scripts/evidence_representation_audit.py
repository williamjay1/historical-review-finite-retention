"""Retrospective archive audit on frozen PCA/ridge scores. No model fitting.

Support and numeric witnesses are different contracts. Labels enter only query
construction after archives are built. All byte limits include common metadata.
"""
from pathlib import Path
import argparse, json, csv, time, zlib, struct, hashlib, shutil
import numpy as np
import pandas as pd
import revision_decision_audit as f
import notification_workflow_analysis as w

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/revision_evidence_representation_20261002'
BUDGETS=[65536,262144]
ATOM=np.dtype([('t','<u4'),('ch','<u2'),('v','<u2'),('q','<f4'),('x','<f4')])
# A run stores channel/version, endpoint times, min/max witness times, and
# first/last/min/max (score, window-last) pairs. Five framing bytes distinguish
# raw and run packets and supply payload length; no free variable-length index.
RUN=struct.Struct('<HHIIIIffffffff')
FRAME=struct.Struct('<BI')
assert ATOM.itemsize==16 and RUN.size==52 and FRAME.size==5
PLAN='''# Evidence representation audit protocol

Route: SCI applied monitoring system design. Primary standards: exact semantic contract, actual packed byte accounting, strong simple storage baselines, independent incident units, and explicit retrospective/online boundaries. No human workload or causal intervention claims.

This is a retrospective redesign after the original notification study, not preregistration. Frozen PCA/ridge seed-0 primary receipts only; no refitting, new threshold selection or new review answers. Pilot: alphabetically first SMD server machine-1-1, plus ESA Mission1 existing Group14 channels 61/62/63 (selected for low native-data inspection cost, not performance). Formal scope, if inexpensive audit remains informative: all 28 SMD devices and both ESA missions with all target channels, two backbones, seed0 (60 frozen fits). Results are descriptive; repeated backbones/channels are not independent incidents. No significance testing.

Archive input: eligible baseline channel highs q[t,j]>=tau, their cycle, channel, latest arrived-review version, float32 normalized score, and completed-window last value. These are 16-byte observable detector records, NOT raw asynchronous telemetry or true fault labels. A common canonical JSON header contains dataset/unit, score and receipt hashes, channels, threshold, clock, review arrivals and version, field schema, query semantics; its actual UTF8 length+4-byte length prefix counts against every budget. Grid support and provenance are therefore not free external side information. Complete raw telemetry costs are reported separately when inspected. The archive sees no incident/affected-channel annotation. Common notifications: local corrected first high per gap0 baseline parent, no extra cooldown, replayed once on original realized tape. Archive construction begins at first baseline high, independently of notification arrival.

Budgets: 64 KiB and 256 KiB total retained detector archive per fit, not per parent and not a deployment-derived capacity. Full high archive and zlib-9 full archive report unrestricted bytes and fit flags. Exact support bitmap stores all decision-channel threshold bits (uncompressed and zlib9), reports numeric-value contract absent. Bitmap is necessary strong comparator; no novelty claimed for packing or zlib. Fixed-seed reservoir keeps floor((B-header)/16) atomic records using standard Algorithm R. First/max summary keeps each parent-channel first and final maximum-score witness (deduplicated), then truncates the selected records chronologically if bytes exceed B. Change summary retains per parent-channel first, last, final max, final min plus score changes >=0.25*tau, with the same truncation rule. Both are explicitly optimistic RETROSPECTIVE references: selecting final extrema before budget truncation is not a causal streaming admission policy. Run reference: within a channel, split contiguous highs at channel-low, ineligibility or provenance change; serialize channel/version as two uint16, first/last/min-witness/max-witness cycle as four uint32, and first/last/min/max score-value pairs as eight float32 (52-byte payload), or all original 16-byte records when their payload is cheaper. Every packet adds a uint8 type and uint32 payload length (5 bytes), including raw fallback packets. The all-history encoding can exceed budget: the budgeted reference admits complete packets in chronological last-high order until overflow. This is an end-of-stream retrospective representation reference; it does NOT certify all evidence in an early temporal prefix, because an unclosed long run can begin before accepted short runs. A query with no retained high is unknown after truncation. Do not claim a new algorithm, real-time causal budget admission, or operational latency based on an offline vectorized build. Point-value query for an interior run is unknown unless that atom is retained; complete run support answers only high existence/earliest cycle, not absence of real faults.

Offline query: each ESA anomaly event ID x annotated affected channel with at least one baseline high at an eligible active decision strictly before own-feedback arrival; SMD incident x each observable high channel under same active-before-own definition, not affected-channel localization. Multiple affected spans of one event/channel are merged into a deduplicated index set. Queries retain disjoint interval/gap support and are clipped to actual active intervals/own cutoff. Unknown annotations are excluded in primary; unknown-label sensitivity is not implemented or claimed. Primary support retention and earliest-hit difference count query pairs and unique event IDs; exact numeric witness retention is separate. Missing answers are unknown, never evidence of normality. Joint notification outcome requires a common notification timestamp in the same active-before-own interval; archived evidence cannot create a lost delivery. Endpoint sensitivity expands query intervals by one scheduled cycle while still excluding ineligible/unknown decisions and every decision at or after own-feedback arrival, clearly distinct from strict active queries. No arbitrary-query full extrema guarantee from whole-run witnesses.

Stop rule: if full archive already fits illustrative pilot budgets, or exact-support simple encoding achieves the task without the proposed reference, stop new-algorithm superiority and retain a diagnostic design/representation boundary contribution. Low synthetic budgets are not evidence of a real storage bottleneck. No human review-time/safety benefit. Errors and delays, if tested, are simulated metadata/retrieval perturbations and do not represent human outcomes. No NASA padding.

Additional strong simple reference: M4-style fixed-time buckets retain each occupied bucket/channel's first, last, minimum-score and maximum-score high record (deduplicated). This is a retrospective fixed-horizon detector-score reference, not a waveform or visual-fidelity claim and not an exact implementation of a database visualization algorithm. The final known horizon T and channel count C determine width: cap=floor((B-H-4)/16), max_bins=floor(cap/(4*C)), width=ceil(T/max_bins). Its own uint32 width costs 4 bytes beyond the unchanged common header; at most four records per bucket/channel guarantee the total budget without chronological truncation. Empty capacity stores no evidence with width zero. All record selection is label-independent. Within-bucket interior query support and earliest evidence are not guaranteed.
'''

def save(p,x): p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def csvwrite(p,rows):
    if not rows:return
    with p.open('w',newline='',encoding='utf-8') as h:
        wr=csv.DictWriter(h,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
def setup():
    OUT.mkdir(parents=True,exist_ok=True)
    if not (OUT/'PROTOCOL.md').exists():
        (OUT/'PROTOCOL.md').write_text(PLAN,encoding='utf-8')
        save(OUT/'protocol_receipt.json',dict(protocol_sha256=f.sha(OUT/'PROTOCOL.md'),stage='retrospective, before audit execution',budgets=BUDGETS))
        before=OUT/'before_redesign';before.mkdir()
        for n in ['ESWA_Manuscript.md','ESWA_Manuscript.docx','ESWA_Supplementary.md','ESWA_Supplementary.docx']:
            shutil.copy2(ROOT/'manuscript'/n,before/n)

def load(suite,p,j,group=False):
    d,masks,paths=w.load_data(suite,p,j);n=len(masks['base'])
    if suite=='ESA':
        qp=d['qpath'];lo=d['lo'];ch=j['data']['channels']
        fp=ROOT/'datasets'/f"m{j['arguments']['mission']}_full_b10"/'features_raw.npy'
        q=np.asarray(d['q'][lo:lo+n]);clock={'kind':'released_affine_nanoseconds','origin':int(d['decision_times'][0]),'step':int(round(d['duration']*1e9))}
    else:
        qp=ROOT/'cache/smd'/f"{j['entity']}_{j['backbone']}_s{j['seed']}_scale_{j['model']['cache_sha256'][:16]}"/'scores.npy'
        lo=j['data']['train_blocks'];q=np.asarray(np.load(qp,mmap_mode='r')[lo:lo+n]);ch=[f'variable_{i+1}' for i in range(q.shape[1])]
        fp=Path(j['data']['working_directory'])/'features_raw.npy';clock={'kind':'sample_index','origin':int(d['decision_times'][0]),'step':int(d['duration'])}
    assert np.array_equal(q.max(1),np.load(p.parent/'scores.npy',mmap_mode='r')[:,j['methods'].index('base')])
    selected=[ch.index(f'channel_{k}') for k in (61,62,63)] if group else list(range(len(ch)))
    x=np.asarray(np.load(fp,mmap_mode='r')[lo:lo+n,:,1]);assert q.shape==x.shape
    reviews=f.readj(p.parent/'reviews.json');arrivals=[int(r['effective_block'])-lo for r in reviews]
    assert np.all(np.diff(arrivals)>=0), 'Review arrivals must be ordered for version encoding.'
    version=np.searchsorted(arrivals,np.arange(n),'right').astype(np.uint16)
    assert len(arrivals)<65535
    assert n<=np.iinfo(np.uint32).max and len(selected)<=np.iinfo(np.uint16).max
    assert np.array_equal(d['decision_times'],clock['origin']+np.arange(n,dtype=np.int64)*clock['step']), 'Irregular decision clocks require a charged timeline.'
    high=(q[:,selected]>=d['tau'])&d['eligible'][:,None]
    ti,cj=np.nonzero(high);atoms=np.empty(len(ti),ATOM);atoms['t']=ti;atoms['ch']=cj;atoms['v']=version[ti];atoms['q']=q[ti,np.array(selected)[cj]];atoms['x']=x[ti,np.array(selected)[cj]]
    header={'schema':'detector-evidence-v1','atom_fields':ATOM.descr,'run_struct':RUN.format,'run_witness_order':['first','last','min_score','max_score'],'packet_struct':FRAME.format,'packet_types':{'0':'raw_atoms','1':'run'},'support_layout':'channel_major_byte_padded','support_bit_order':'little','unit':d['unit'],'dataset':suite,'backbone':d['backbone'],'seed':d['seed'],'channels':[ch[k] for k in selected],'clock':clock,'n_cycles':n,'threshold':d['tau'],'receipt_sha256':f.sha(p),'score_sha256':f.sha(qp),'review_sha256':f.sha(p.parent/'reviews.json'),'review_effective_cycles':arrivals,'contract':'eligible baseline-high support; score/window-last witness; no waveform','eligibility':'encoded by absence of high in support; no negative fault claim'}
    hb=json.dumps(header,sort_keys=True,separators=(',',':')).encode();header_bytes=len(hb)+4
    pb=w.parent_data(masks['base'],d['eligible'],0);pp=np.full(n,-1,np.int32);pp[pb['pos']]=pb['pid']
    policy=w.replay(masks['base'],masks['local_nn'],d['eligible'],dict(method='locked_local',parent_gap=0,cooldown_cycles=0),pb)
    # Data labels are used only below this construction boundary.
    return d,atoms,high,header_bytes,header,selected,pp,policy,paths+[qp,fp]

def summaries(atoms,pp,tau):
    """Optimistic retrospective witnesses, NOT a streaming budget policy.

    Global final extrema are selected before chronological truncation. Labels
    are absent, but a future maximum can replace an early admitted witness.
    Consequently no online admission, prefix-invariance or latency is claimed.
    """
    groups={}
    for k,a in enumerate(atoms): groups.setdefault((int(pp[a['t']]),int(a['ch'])),[]).append(k)
    fm=[];cp=[]
    for ids in groups.values():
        z=np.array(ids);vals=atoms['q'][z];mx=int(z[np.argmax(vals)]);mn=int(z[np.argmin(vals)])
        fm.extend([ids[0],mx]);chosen=[ids[0],ids[-1],mx,mn];last=ids[0]
        for k in ids[1:]:
            if abs(float(atoms['q'][k])-float(atoms['q'][last]))>=.25*tau:chosen.append(k);last=k
        cp.extend(chosen)
    return np.unique(fm).astype(np.int64),np.unique(cp).astype(np.int64)

def m4_buckets(atoms,n_cycles,n_channels,header_bytes,budget):
    """Fixed-horizon first/last/min-score/max-score reference with strict bytes."""
    capacity=max(0,(budget-header_bytes-4)//ATOM.itemsize)
    max_bins=capacity//(4*n_channels)
    width=max(1,(n_cycles+max_bins-1)//max_bins) if max_bins else 0
    selected=[]
    if width:
        groups={}
        for k,a in enumerate(atoms):groups.setdefault((int(a['t'])//width,int(a['ch'])),[]).append(k)
        for ids in groups.values():
            z=np.asarray(ids);q=atoms['q'][z]
            selected.extend([ids[0],ids[-1],int(z[np.argmin(q)]),int(z[np.argmax(q)])])
    ids=np.unique(selected).astype(np.int64)
    payload=struct.pack('<I',width)+atoms[ids].tobytes()
    restored=np.frombuffer(payload[4:],dtype=ATOM)
    assert np.array_equal(restored,atoms[ids]) and struct.unpack('<I',payload[:4])[0]==width
    assert len(ids)<=capacity and (header_bytes+len(payload)<=budget or header_bytes+4>budget)
    return restored,width,payload

def runs(atoms):
    packets=[]
    for ch in np.unique(atoms['ch']):
        ii=np.flatnonzero(atoms['ch']==ch);t=atoms['t'][ii];v=atoms['v'][ii]
        cuts=np.r_[0,np.flatnonzero((np.diff(t)!=1)|(v[1:]!=v[:-1]))+1,len(ii)]
        for a,b in zip(cuts[:-1],cuts[1:]):
            ids=ii[a:b];z=atoms['q'][ids]; witnesses=np.unique([ids[0],ids[-1],ids[np.argmin(z)],ids[np.argmax(z)]])
            raw=len(ids)*ATOM.itemsize<=RUN.size
            if raw:
                payload=atoms[ids].tobytes()
            else:
                first,last=atoms[ids[0]],atoms[ids[-1]]
                mn,mx=atoms[ids[np.argmin(z)]],atoms[ids[np.argmax(z)]]
                payload=RUN.pack(int(ch),int(first['v']),int(first['t']),int(last['t']),
                                 int(mn['t']),int(mx['t']),
                                 float(first['q']),float(first['x']),float(last['q']),float(last['x']),
                                 float(mn['q']),float(mn['x']),float(mx['q']),float(mx['x']))
            packed=FRAME.pack(int(not raw),len(payload))+payload
            packets.append(dict(ch=int(ch),first=int(t[a]),last=int(t[b-1]),ids=ids if raw else witnesses,raw=raw,bytes=len(packed),packed=packed))
    packets.sort(key=lambda z:(z['last'],z['ch'],z['first']))
    return packets

def query_specs(d,selected,atoms,high,tolerance=0,include_unknown=False):
    if include_unknown:
        raise ValueError('Unknown-label sensitivity is not implemented; do not report it as completed.')
    rows=[];lookup={v:k for k,v in enumerate(selected)}
    for ident,e in d['events'].items():
        if e['category']!='anomaly':continue
        items=[(ch,idx) for _,idx,ch in e['affected']] if e['affected'] else [(ch,e['activepre']) for ch in selected]
        # ESA events without affected spans are not replaced by all channels.
        if d['unit'] in ('1','2') and not e['affected']:continue
        # Multiple affected spans for one event/channel are one query, not
        # independent observations. Merge and deduplicate their cycle support.
        merged={}
        for ch,idx in items:
            if ch in lookup and len(idx):merged.setdefault(ch,[]).append(np.asarray(idx,dtype=np.int64))
        for ch,parts in merged.items():
            ci=lookup[ch];ix=np.unique(np.concatenate(parts))
            if tolerance:ix=np.unique(np.concatenate([ix,ix-1,ix+1]));ix=ix[(ix>=0)&(ix<len(high))]
            # Tolerance may relax labelled endpoints, never the strict own-
            # feedback boundary. ESA cutoff is an absolute source block;
            # SMD cutoff is an effective source-sample decision timestamp.
            before=(d['lo']+ix<e['cutoff']) if 'lo' in d else (d['decision_times'][ix]<e['cutoff'])
            ix=ix[before & d['eligible'][ix] & d['valid'][ix]]
            hit=ix[high[ix,ci]]
            if not len(hit):continue
            # Keep disjoint interval/gap support as an explicit query index set.
            rows.append(dict(incident_id=ident,channel=ci,idx=ix,first=int(hit[0]),hit_count=len(hit)))
    return rows

def retained_first(a,ids,q):
    z=a[ids];ts=z['t'][z['ch']==q['channel']];inter=np.intersect1d(ts,q['idx'],assume_unique=True)
    return int(inter[0]) if len(inter) else None
def run_first(packets,q):
    best=None
    for z in packets:
        if z['ch']!=q['channel']:continue
        ix=q['idx'];k=int(np.searchsorted(ix,z['first']));
        if k<len(ix) and ix[k]<=z['last']:best=int(ix[k]) if best is None else min(best,int(ix[k]))
    return best

def evaluate(suite,p,j,folder,group=False):
    begin=time.perf_counter();d,a,h,hb,header,selected,pp,policy,paths=load(suite,p,j,group)
    base={'dataset':suite,'unit':d['unit'],'backbone':d['backbone'],'seed':d['seed'],'group':'group14' if group else 'all','run':p.parent.name}
    fm,cp=summaries(a,pp,d['tau']);packets=runs(a);un=np.arange(len(a));qs=query_specs(d,selected,a,h)
    common_start=policy['starts'];runbytes=sum(z['bytes'] for z in packets)+hb
    bm=np.packbits(h.T,axis=1,bitorder='little').tobytes();blob=a.tobytes()
    zipped_atoms=zlib.compress(blob,9);zipped_bitmap=zlib.compress(bm,9)
    restored_atoms=np.frombuffer(zlib.decompress(zipped_atoms),dtype=ATOM)
    assert np.array_equal(restored_atoms,a), 'Complete compressed archive round trip failed.'
    decoded_bitmaps={}
    for name,payload in [('bitmap',bm),('zlib_bitmap',zlib.decompress(zipped_bitmap))]:
        decoded=np.unpackbits(np.frombuffer(payload,dtype=np.uint8).reshape(h.shape[1],-1),axis=1,bitorder='little')[:,:len(h)].T.astype(bool)
        assert np.array_equal(decoded,h), 'Support archive round trip failed.'
        decoded_bitmaps[name]=decoded
    fullbytes=hb+len(blob);zipbytes=hb+len(zipped_atoms);bmb=hb+len(bm);bmzip=hb+len(zipped_bitmap)
    cost=dict(base,cycles=len(h),channels=h.shape[1],high_atoms=len(a),unknown_high_atoms=int(h[~d['valid']].sum()),independent_hit_incidents=len({q['incident_id'] for q in qs}),query_pairs=len(qs),header_bytes=hb,full_bytes=fullbytes,zlib_full_bytes=zipbytes,bitmap_bytes=bmb,zlib_bitmap_bytes=bmzip,firstmax_bytes=hb+len(fm)*16,change_bytes=hb+len(cp)*16,run_reference_bytes=runbytes,run_count=len(packets),notifications=len(common_start),arrived_reviews=len(header['review_effective_cycles']))
    metrics=[];queries=[];bucket_payloads={}
    for budget in BUDGETS:
        cap=max(0,(budget-hb)//16)
        # Algorithm R over input records; explicitly stochastic, fixed audit seed.
        rng=np.random.default_rng(20261002);res=list(range(min(cap,len(a))))
        for k in range(cap,len(a)):
            pick=int(rng.integers(k+1))
            if pick<cap:res[pick]=k
        methods=[('full_archive',un,fullbytes,None,fullbytes<=budget),('zlib_full_archive',un,zipbytes,None,zipbytes<=budget),('reservoir',np.sort(res).astype(np.int64),hb+min(cap,len(a))*16,None,hb<=budget),('first_max',fm[:cap],hb+min(cap,len(fm))*16,None,hb<=budget),('change_summary',cp[:cap],hb+min(cap,len(cp))*16,None,hb<=budget)]
        bucket_atoms,bucket_width,bucket_payload=m4_buckets(a,len(h),h.shape[1],hb,budget)
        bucket_payloads[budget]=bucket_payload
        methods.append(('m4_buckets',np.arange(len(bucket_atoms)),hb+len(bucket_payload),None,hb+4<=budget))
        accepted=[];used=hb
        for z in packets:
            if used+z['bytes']>budget:break
            accepted.append(z);used+=z['bytes']
        kept=np.unique(np.concatenate([z['ids'] for z in accepted])).astype(np.int64) if accepted else np.array([],np.int64)
        methods.append(('run_reference',kept,used,accepted,hb<=budget))
        # A strong exact-support archive; no q/value retrieval claim.
        for name,size in [('bitmap',bmb),('zlib_bitmap',bmzip)]:methods.append((name,np.array([],np.int64),size,'bitmap',size<=budget))
        for name,ids,size,enc,fits in methods:
            retained=0;exact=0;joint=0;diff=[];wit=0;event=set();worst=0
            for q in qs:
                archive=restored_atoms if name=='zlib_full_archive' else bucket_atoms if name=='m4_buckets' else a
                if enc=='bitmap':
                    hits=q['idx'][decoded_bitmaps[name][q['idx'],q['channel']]] if fits else np.array([],np.int64)
                    first=int(hits[0]) if len(hits) else None
                elif enc is not None:first=run_first(enc,q)
                else:first=retained_first(archive,ids,q)
                witness=retained_first(archive,ids,q) if enc!='bitmap' else None
                timely=bool(np.intersect1d(common_start,q['idx']).size)
                ok=first is not None;retained+=ok;exact+=ok and first==q['first'];joint+=ok and timely;wit+=witness is not None
                if ok:diff.append(first-q['first']);event.add(q['incident_id']);worst=max(worst,first-q['first'])
                queries.append(dict(base,budget=budget,method=name,incident_id=q['incident_id'],channel=header['channels'][q['channel']],reference_first=q['first'],retrieved_first=first,retained=ok,earliest_exact=ok and first==q['first'],numeric_witness=witness is not None,common_timely_notification=timely,joint=ok and timely,bytes=size,within_budget=fits))
            metrics.append(dict(base,budget=budget,method=name,bytes=size,within_budget=fits,query_pairs=len(qs),retained_pairs=retained,exact_first_pairs=exact,numeric_witness_pairs=wit,joint_pairs=joint,unique_retained_incidents=len(event),max_first_difference_cycles=worst if diff else None,mean_first_difference_cycles=float(np.mean(diff)) if diff else None,notifications=len(common_start),m4_bucket_width_cycles=bucket_width if name=='m4_buckets' else None))
    sens=[]
    for tol in [0,1]:
        qq=query_specs(d,selected,a,h,tolerance=tol)
        sens.append(dict(base,endpoint_tolerance_cycles=tol,query_pairs=len(qq),incidents=len({z['incident_id'] for z in qq}),firstmax_pairs=sum(retained_first(a,fm,q) is not None for q in qq),firstmax_exact_first=sum(retained_first(a,fm,q)==q['first'] for q in qq)))
    folder.mkdir(parents=True,exist_ok=True);csvwrite(folder/'archive_cost.csv',[cost]);csvwrite(folder/'metrics.csv',metrics);csvwrite(folder/'queries.csv',queries);csvwrite(folder/'endpoint_sensitivity.csv',sens);save(folder/'header.json',header)
    if folder.parent.name=='pilot':
        hblob=json.dumps(header,sort_keys=True,separators=(',',':')).encode()
        hp=struct.pack('<I',len(hblob))+hblob
        assert len(hp)==hb
        for fname,payload in [('full_atoms.bin',blob),('zlib_atoms.bin',zipped_atoms),('support_bitmap.bin',bm),('zlib_support_bitmap.bin',zipped_bitmap),('run_packets.bin',b''.join(z['packed'] for z in packets))]:
            (folder/fname).write_bytes(hp+payload)
        for budget,payload in bucket_payloads.items():(folder/f'm4_buckets_{budget}.bin').write_bytes(hp+payload)
    save(folder/'receipt.json',dict(passed=True,source_sha256={str(x):f.sha(x) for x in paths if x.name!='features_raw.npy'},script_sha256=f.sha(Path(__file__)),wall_seconds=time.perf_counter()-begin,no_training=True,no_label_archive_decisions=True,archives_witness_dtype=str(ATOM),actual_online_p95_measured=False,firstmax_change_are_optimistic_retrospective_references=True,run_payload_bytes=RUN.size,packet_framing_bytes=FRAME.size,run_acceptance_is_end_order_not_certified_temporal_prefix=True,common_notification_sha256=hashlib.sha256(np.asarray(common_start,dtype='<u4').tobytes()).hexdigest()))
    print(suite,d['unit'],d['backbone'],cost['query_pairs'],fullbytes,zipbytes,bmzip,runbytes,round(time.perf_counter()-begin,2),flush=True)
    return cost,metrics,queries,sens

def selfcheck():
    rng=np.random.default_rng(7);cases=0
    for _ in range(20):
        h=rng.random((60,4))>.4;tt,ch=np.nonzero(h);a=np.empty(len(tt),ATOM);a['t']=tt;a['ch']=ch;a['v']=tt//13;a['q']=rng.random(len(tt))+2;a['x']=rng.normal(size=len(tt))
        p=runs(a)
        for ci in range(4):
            for l,r in [(0,59),(10,12),(25,48),(11,11),(49,59)]:
                idx=np.arange(l,r+1);actual=idx[h[idx,ci]];q=dict(channel=ci,idx=idx)
                assert run_first(p,q)==(int(actual[0]) if len(actual) else None)
                cases+=1
        assert sum(x['bytes'] for x in p)<=len(a)*16+FRAME.size*len(p)
        for packet in p:
            kind,length=FRAME.unpack(packet['packed'][:FRAME.size])
            assert len(packet['packed'])==packet['bytes']==FRAME.size+length
            payload=packet['packed'][FRAME.size:]
            if kind==0:
                restored=np.frombuffer(payload,dtype=ATOM)
                assert np.array_equal(restored,a[packet['ids']])
            else:
                record=RUN.unpack(payload)
                assert length==RUN.size and record[0]==packet['ch']
                assert record[2]==packet['first'] and record[3]==packet['last']
        assert np.array_equal(np.unpackbits(np.frombuffer(zlib.decompress(zlib.compress(np.packbits(h.T,axis=1,bitorder='little').tobytes())),np.uint8).reshape(4,-1),axis=1,bitorder='little')[:,:60],h.T)
    # Duplicate ESA affected spans form one incident-channel query, and a +1
    # endpoint tolerance cannot include the own-arrival cycle.
    h=np.ones((8,1),bool)
    d=dict(unit='1',lo=100,eligible=np.ones(8,bool),valid=np.ones(8,bool),events={
        'event':dict(category='anomaly',affected=[(None,np.array([1,2]),4),(None,np.array([2,3]),4)],cutoff=104)})
    q=query_specs(d,[4],None,h,tolerance=1)
    assert len(q)==1 and q[0]['idx'].tolist()==[0,1,2,3]
    d=dict(unit='server',decision_times=np.arange(8)*10+9,eligible=np.ones(8,bool),valid=np.ones(8,bool),events={
        'incident':dict(category='anomaly',affected=[],activepre=np.array([1,2]),cutoff=39)})
    q=query_specs(d,[0],None,h,tolerance=1)
    assert q[0]['idx'].tolist()==[0,1,2]
    cases+=2
    # Score extrema/endpoints do not certify a late interior query, even when
    # all high records fit one perfectly budgeted bucket's four witnesses.
    a=np.empty(10,ATOM);a['t']=np.arange(10);a['ch']=0;a['v']=0
    a['q']=[2,1,100,7,7,7,7,7,4,9];a['x']=np.arange(10)
    kept,width,payload=m4_buckets(a,10,1,20,88)
    assert width==10 and len(payload)+20==88
    assert retained_first(kept,np.arange(len(kept)),dict(channel=0,idx=np.array([8]))) is None
    assert retained_first(kept,np.arange(len(kept)),dict(channel=0,idx=np.array([8,9])))==9
    cases+=2
    return cases

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['pilot','full'],required=True);args=ap.parse_args();setup();start=time.perf_counter();checks=selfcheck()
    rs=[z for z in f.receipts() if (z[2]['arguments']['backbone'] if z[0]=='ESA' else z[2]['backbone']) in ['pca','ridge'] and (z[2]['arguments']['seed'] if z[0]=='ESA' else z[2]['seed'])==0]
    if args.mode=='pilot':rs=[z for z in rs if z[0]=='SMD' and z[2]['entity']=='machine-1-1' or z[0]=='ESA' and str(z[2]['arguments']['mission'])=='1']
    assert len(rs)==(4 if args.mode=='pilot' else 60)
    allrows=[[],[],[],[]]
    for suite,p,j in rs:
        vals=evaluate(suite,p,j,OUT/args.mode/p.parent.name,group=args.mode=='pilot' and suite=='ESA')
        for dest,val in zip(allrows,vals):dest.extend([val] if isinstance(val,dict) else val)
    for name,vals in zip(['archive_cost','metrics','queries','endpoint_sensitivity'],allrows):csvwrite(OUT/args.mode/(name+'.csv'),vals)
    save(OUT/args.mode/'COMPLETION.json',dict(passed=True,fits=len(rs),rows={name:len(z) for name,z in zip(['archive_cost','metrics','queries','endpoint_sensitivity'],allrows)},property_queries=checks,wall_seconds=time.perf_counter()-start,script_sha256=f.sha(Path(__file__)),budget_bytes=BUDGETS,actual_online_latency_measured=False))
if __name__=='__main__':main()
