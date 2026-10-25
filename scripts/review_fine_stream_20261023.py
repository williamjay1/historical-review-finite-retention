"""Read-only cadence adapters for finite detector-evidence archives.

All scores and source windows already exist.  This module never fits a model,
downloads data, or modifies its input caches.  SMD coarse and fine streams use
the same fitted width-10 PCA/ridge model; a frozen original review tape supplies
the same provenance updates at both cadences.  Labels are read only to construct
retrospective evaluation scopes after the atom stream exists.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, shutil, struct, time, zlib
from pathlib import Path
import numpy as np
import evidence_representation_audit as e
import archive_codec_20261009 as codec

ROOT = e.ROOT
OUT = ROOT / 'results/revision_review_20261023'
FINE_CACHE = ROOT / 'cache/revision_resolution_20261001'
FINE_DATA = ROOT / 'datasets/revision_resolution_20261001'
OLD = ROOT / 'results/revision_20261001/resolution/runs'
TRUSTED = ROOT / 'results/revision_archive_task_20261009/smd_labels/trusted_incident_dimensions.json'

def js(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''): h.update(b)
    return h.hexdigest()

def smd_receipts():
    """Frozen seed-zero original receipts indexed by (device, backbone)."""
    return {(j['entity'], j['backbone']):(p,j)
            for suite,p,j in e.f.receipts()
            if suite=='SMD' and j['backbone'] in ('pca','ridge') and j['seed']==0}

def available():
    """Return 56 paired source identities without loading numerical data."""
    return [(p.parent.parent.name,p.parent.name) for p in sorted(FINE_CACHE.glob('*/*/model.json'))]

def load_smd(entity, backbone, stride=1, receipts=None):
    """Return the legacy e.load-compatible tuple, for fine or paired coarse.

    Tuple: (d, atoms, high[T,C], header_bytes, header, selected_channels,
    parent_id[T], policy=None, input_paths).  ``d['events']`` keeps all 327 binary
    incidents, while ``affected`` only uses the 322 exact-boundary dimension
    annotations.  Coarse/fine provenance is one ORIGINAL coarse review tape.

    The fine time index t is local decision number; source sample is 9+t.
    The coarse sample is 9+10*t.  Raw x equals the completed window's last sample.
    Do not interpret a fine-only support as a recovered original coarse record.
    """
    if stride not in (1,10): raise ValueError('stride must be 1 or 10')
    receipts = smd_receipts() if receipts is None else receipts
    receipt,j = receipts[(entity,backbone)]
    info = js(FINE_DATA/entity/'prepared.json')
    modelpath = FINE_CACHE/entity/backbone/'model.json'; model = js(modelpath)
    qp = FINE_CACHE/entity/backbone/('q_fine.npy' if stride==1 else 'q_coarse.npy')
    q0 = np.load(qp,mmap_mode='r')
    q = np.asarray(q0 if stride==1 else q0[info['train_blocks']:])
    n,c = q.shape; times = 9+np.arange(n,dtype=np.int64)*stride
    original = Path(info['source']); testpath = original/'test.npy'
    values = np.load(testpath,mmap_mode='r')
    assert times[-1]<len(values) and c==38
    tau=float(model['threshold'])
    assert tau==j['model']['threshold'], 'Cadence model threshold must match original frozen fit.'
    reviews_path = receipt.parent/'reviews.json'; reviews=js(reviews_path)
    # Original review effective_block is an absolute train+test block.
    arrival_samples = [(int(r['effective_block'])-info['train_blocks']+1)*10-1 for r in reviews]
    arrivals = np.searchsorted(times,np.asarray(arrival_samples,dtype=np.int64),'left').astype(int).tolist()
    assert len(arrivals)<65535 and np.all(np.diff(arrivals)>=0)
    versions=np.searchsorted(np.asarray(arrivals,dtype=np.int64),np.arange(n),'right').astype('<u2')
    high=q>=tau
    ti,ch=np.nonzero(high); atoms=np.empty(len(ti),e.ATOM)
    atoms['t']=ti; atoms['ch']=ch; atoms['v']=versions[ti]
    atoms['q']=q[ti,ch]; atoms['x']=values[times[ti],ch]
    # Raw window-last verification uses the independent cached width10 features.
    feature_path=FINE_DATA/entity/('features_fine_context.npy' if stride==1 else 'features_coarse.npy')
    features=np.load(feature_path,mmap_mode='r')
    last=features[40:,:,1] if stride==1 else features[info['train_blocks']:,:,1]
    assert last.shape==q.shape and np.array_equal(last,values[times])
    header={'schema':'detector-evidence-cadence-v1','atom_fields':e.ATOM.descr,
       'unit':entity,'dataset':'SMD','backbone':backbone,'seed':0,
       'channels':[f'variable_{k+1}' for k in range(c)],
       'clock':{'kind':'sample_index','origin':9,'step':stride},'n_cycles':n,
       'threshold':tau,'receipt_sha256':sha(receipt),'score_sha256':sha(qp),
       'review_sha256':sha(reviews_path),'review_effective_cycles':arrivals,
       'review_effective_source_samples':arrival_samples,
       'feature_width_samples':10,'scoring_source':'existing shared-cadence fitted model; no new fit',
       'provenance_source':'original coarse frozen review tape, projected causally to selected cadence',
       'contract':'eligible baseline-high support; float32 score and raw window-last witness; no waveform',
       'eligibility':'all scheduled decisions usable; source samples 0..8 have no complete window',
       'record_semantics':'cadence is part of record identity; fine support is newly emitted, not coarse reconstruction'}
    hb=len(json.dumps(header,sort_keys=True,separators=(',',':')).encode())+4
    # Build the observable base parents without any annotations.
    parents=e.w.parent_data(high.any(1),np.ones(n,bool),0)
    pp=np.full(n,-1,np.int32);pp[parents['pos']]=parents['pid']
    # Evaluation boundary: no labels are used in q/high/atoms/header/parents.
    labelpath=original/'test_label.txt'; labels=np.loadtxt(labelpath,dtype=np.int8)
    assert len(labels)==len(values) and np.isin(labels,[0,1]).all()
    starts=np.flatnonzero((labels==1)&np.r_[True,labels[:-1]!=1])
    ends=np.flatnonzero((labels==1)&np.r_[labels[1:]!=1,True])+1
    trusted=js(TRUSTED)
    # The existing original event receipt fixes own-feedback identity/timing.
    import pandas as pd
    saved=pd.read_csv(receipt.parent/'event_results.csv')
    base=saved[saved.method=='base'].set_index('event_id'); events={}
    for ident,(aa,bb) in enumerate(zip(starts,ends)):
        r=base.loc[ident]
        assert int(r.start_sample)==aa and int(r.end_sample_exclusive)==bb
        cutoff=int(r.own_feedback_effective_decision_sample) if pd.notna(r.own_feedback_effective_decision_sample) else len(labels)+10
        active=np.flatnonzero((times>=aa)&(times<bb)); pre=active[times[active]<cutoff]
        # Overlapping feature history is separate from active decision emission.
        ix=np.flatnonzero((times-9<bb)&(times>=aa)); dims=trusted.get(f'{entity}:{ident}')
        affected=[] if dims is None else [(active,pre,int(k)) for k in dims['dimensions0based']]
        events[str(ident)]={'category':'anomaly','idx':ix,'pre':ix[times[ix]<cutoff],
           'active':active,'activepre':pre,'affected':affected,'cutoff':cutoff,
           'first_start':int(aa),'final_end':int(bb-1),'trusted_annotation':dims is not None,
           'dimensions0based':[] if dims is None else dims['dimensions0based']}
    d={'unit':entity,'backbone':backbone,'seed':0,'tau':tau,'eligible':np.ones(n,bool),
       'valid':np.ones(n,bool),'events':events,'decision_times':times,'duration':stride,
       'raw_samples':len(labels),'stride':stride,'fine_shared_model':True,
       'nominal_decision':labels[times]==0,'record_contract':'same 16-byte atom fields; changed schedule'}
    paths=[receipt,qp,modelpath,reviews_path,testpath,labelpath,feature_path,TRUSTED]
    return d,atoms,high,hb,header,list(range(c)),pp,None,paths

def query_specs(d,high,family='full_annotated'):
    """Label-derived offline interval queries; no detector-positive filtering."""
    result=[]
    for ident,event in d['events'].items():
        if family=='full_model': channels=range(high.shape[1])
        else: channels=event['dimensions0based']
        ix=event['activepre'] if family=='pre_feedback' else event['active']
        for ch in channels:
            hit=ix[high[ix,ch]]
            result.append({'incident_id':ident,'family':family,'category':'anomaly','channel':ch,
              'idx':ix,'hits':hit,'positive':bool(len(hit)),'first':int(hit[0]) if len(hit) else -1,
              'unusable':0})
    return result

def to_driver_stream(entity,backbone,stride=1,receipts=None):
    """Map to review_experiments_20261023.load_coarse's exact field schema.

    The grid is intentionally the same 64 fixed interval/channel scopes and
    two empty queries as the coarse archive task.  Labels supply only the
    independent full-event annotation queries and opportunity denominators.
    """
    import archive_task_audit_20261009 as tasks
    d,a,h,hb,header,selected,pp,policy,paths=load_smd(entity,backbone,stride,receipts)
    qs,st=tasks.specs(d,selected,h,js(TRUSTED))
    qs=[q for q in qs if q['family'] in ('full_annotated','grid')]
    return dict(dataset='SMD',unit=entity,backbone=backbone,
                cadence='fine' if stride==1 else 'paired_coarse',a=a,h=h,
                eligible=d['eligible'],header=header,queries=qs,stages=st,source=d)

def audit_smd():
    OUT.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(OUT).free<1_000_000_000: raise RuntimeError('Insufficient free space for output')
    receipts=smd_receipts(); rows=[]; seals=[]; t0=time.perf_counter()
    for entity,kind in available():
        original_receipt,j=receipts[(entity,kind)]
        original_qp=ROOT/'cache/smd'/f"{entity}_{kind}_s0_scale_{j['model']['cache_sha256'][:16]}"/'scores.npy'
        original_q=np.load(original_qp,mmap_mode='r')[j['data']['train_blocks']:]
        paired={}
        for stride in (10,1):
            d,a,h,hb,header,selected,pp,policy,paths=load_smd(entity,kind,stride,receipts)
            queries=query_specs(d,h)
            if stride==10:
                cached=np.load(FINE_CACHE/entity/kind/'q_coarse.npy',mmap_mode='r')[j['data']['train_blocks']:]
                original_maxerr=float(np.max(np.abs(cached-original_q)))
                original_equal=bool(np.array_equal(cached,original_q))
                original_high_discrepancies=int(np.sum((cached>=d['tau'])!=(original_q>=d['tau'])))
                paired['coarse_q']=cached
            else:
                fine=np.load(FINE_CACHE/entity/kind/'q_fine.npy',mmap_mode='r')
                shared=fine[::10][:len(paired['coarse_q'])]
                shared_maxerr=float(np.max(np.abs(shared-paired['coarse_q'])))
                assert np.array_equal(shared,paired['coarse_q'])
            # Use the existing exact reversible layouts and actual on-disk files,
            # including their real canonical header, count and column frames.
            bm=zlib.compress(np.packbits(h.T,axis=1,bitorder='little').tobytes(),9)
            codecs={}
            for layout in ('aos_zlib','soa_zlib','bitmap_numeric'):
                path=OUT/'fine_codec'/entity/kind/f'stride{stride}_{layout}.arc'
                codecs[layout]=codec.build_file(path,layout,a,header)['bytes']
                decoded=codec.ArchiveReader(path).all()
                assert decoded.tobytes()==a.tobytes()
            pq=[q for q in queries if q['positive']]
            row={'dataset':'SMD','unit':entity,'backbone':kind,'stride_samples':stride,
               'source_samples':d['raw_samples'],'decision_cycles':len(h),'channels':h.shape[1],
               'binary_incidents':len(d['events']),'exact_annotation_incidents':sum(v['trusted_annotation'] for v in d['events'].values()),
               'active_opportunity_incidents':sum(bool(len(v['active'])) for v in d['events'].values()),
               'any_high_incidents':sum(bool(h[v['active']].any()) for v in d['events'].values()),
               'annotated_high_incidents':len({q['incident_id'] for q in pq}),
               'annotated_targets':len(queries),'annotated_empty_scopes':sum(not len(q['idx']) for q in queries),
               'annotated_positive_pairs':len(pq),'high_atoms':len(a),'high_density':float(h.mean()),
               'support_runs':int(sum(np.sum(np.r_[True,np.diff(a['t'][a['ch']==ch])!=1]) for ch in range(h.shape[1]) if np.any(a['ch']==ch))),
               'header_bytes':hb,'full_aos_zlib_bytes':codecs['aos_zlib'],
               'full_soa_zlib_bytes':codecs['soa_zlib'],
               'bitmap_bytes':len(bm),'bitmap_plus_values_bytes':codecs['bitmap_numeric'],
               'best_complete_bytes':min(codecs.values()),
               'original_coarse_scores_bit_exact':original_equal,
               'original_coarse_q_max_abs_error':original_maxerr,
               'original_coarse_channel_high_discrepancies':original_high_discrepancies,
               'shared_fine_coarse_scores_max_abs_error':0.0,
               'provenance_tape':'original frozen coarse tape projected to cadence'}
            rows.append(row)
        seals.append({'unit':entity,'backbone':kind,'original_score_sha256':sha(original_qp),
                      'fine_score_sha256':sha(FINE_CACHE/entity/kind/'q_fine.npy'),
                      'coarse_score_sha256':sha(FINE_CACHE/entity/kind/'q_coarse.npy')})
        print('FINE_SOURCE_AUDIT',entity,kind,rows[-2]['high_atoms'],rows[-1]['high_atoms'],flush=True)
    with (OUT/'fine_stream_cost.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    totals=[]
    for kind in ('pca','ridge'):
        for stride in (10,1):
            rr=[r for r in rows if r['backbone']==kind and r['stride_samples']==stride]
            total={k:sum(r[k] for r in rr) for k in ('decision_cycles','binary_incidents','exact_annotation_incidents','active_opportunity_incidents','any_high_incidents','annotated_high_incidents','annotated_targets','annotated_empty_scopes','annotated_positive_pairs','high_atoms','support_runs','full_aos_zlib_bytes','full_soa_zlib_bytes','bitmap_plus_values_bytes','best_complete_bytes')}
            total.update(backbone=kind,stride_samples=stride,fits=len(rr),full_64KiB_fits=sum(r['best_complete_bytes']<=65536 for r in rr),full_256KiB_fits=sum(r['best_complete_bytes']<=262144 for r in rr),full_1MiB_fits=sum(r['best_complete_bytes']<=1048576 for r in rr))
            totals.append(total)
    # Event-local ESA data is described but cannot be passed as full mission.
    esa=[]
    for m in ('1','2'):
        tp=ROOT/f'datasets/revision_esa_resolution_20261001/m{m}/timeline.npz'
        data=np.load(tp);starts=data['starts'];ends=data['ends'];q=data['channel_q']
        step=int(js(ROOT/f'datasets/m{m}_full_b10/complete.json')['step_seconds']*1e9)
        breaks=int(np.sum(np.diff(ends)!=step))
        esa.append({'mission':m,'windows':len(ends),'channels':q.shape[1],
           'internal_schedule_gaps':breaks,'stride_released_ns':step,
           'timeline_sha256':sha(tp),'scope':'event-local union selected with held-out event labels; not a label-blind continuous mission archive',
           'model':'PCA numerical refit on original train input; original PCA weights not persisted',
           'use_in_archive_primary':False,'reason':'Label-selected windows and gaps cannot fairly estimate mission storage or continuous online retention.'})
    report={'passed':True,'fits':len(seals),'paired_conditions':len(rows),'no_new_training':True,
       'elapsed_seconds':time.perf_counter()-t0,'script_sha256':sha(__file__),
       'actual_codec_files':len(rows)*3,'every_codec_roundtrip_bit_exact':True,
       'all_original_coarse_scores_bit_exact':all(r['original_coarse_scores_bit_exact'] for r in rows),
       'total_original_high_discrepancies':sum(r['original_coarse_channel_high_discrepancies'] for r in rows if r['stride_samples']==10),
       'totals':totals,'source_seals':seals,'esa_local_boundary':esa,
       'reconciliation':'327 contiguous binary events remain the model-output cohort; 322 exact-boundary interpretation events supply 2254 annotated dimension targets. These are different denominators, not a correction from 327 to 322.'}
    (OUT/'fine_stream_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_seals',)},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--audit',action='store_true');args=parser.parse_args()
    if args.audit:audit_smd()
    else:print(json.dumps(available(),indent=2))
