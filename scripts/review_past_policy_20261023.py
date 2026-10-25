"""Past-only forecast of complete-record archive feasibility.

This is a conditional capacity diagnostic, not a learned deployment policy.
The fixed rule and selected devices are written before execution; labels are
never used by the cost forecast. No detector fitting or new input download.
"""
from pathlib import Path
import argparse, csv, hashlib, json, math, platform, time
import numpy as np
import review_archive_core_20261023 as core
import review_experiments_20261023 as driver
import review_fine_stream_20261023 as fine

ROOT=driver.ROOT;OUT=driver.OUT
DEVICES=('machine-1-1','machine-3-4')
BACKBONES=('pca','ridge')
CAPS=(65536,262144)
BUFFERS=(1.0,1.25)
PROTOCOL='''# Past-only capacity forecast, declared before execution

Scope is preselected for computational relevance: machine-3-4 is the existing
constrained server; machine-1-1 is a previously used inexpensive control. Both
PCA and ridge, paired coarse and fine schedules, plus ESA Mission 1 PCA/ridge
give ten histories. This is a targeted stress/control analysis, not an estimate
of the distribution of deployment capacities or an independent external test.

Record service is unchanged: all eligible high records (t,channel,review
version,float32 score,float32 window-last), and separately charged usability.
For each prefix the full format is the smaller actual byte string among the
existing SOA-zlib and bitmap-plus-values codecs. JSON, framing and usability
bytes are included. This is a growing-history single-file service, not the
fixed-chunk FIFO retention experiment.

At the end of each of the first three equal quarters, predict complete bytes
for the next quarter prefix using only payload sizes already observed:
  predicted_payload_next = payload_now + max(0,payload_now-payload_previous).
The first difference uses the actual empty-prefix payload as its predecessor.
Add the known next scheduled prefix's header cost. The two prespecified rules
multiply predicted_payload_next by 1.0 or 1.25 before adding that header cost.
These multipliers are fixed illustrations, not tuned using later prefixes.
The known schedule horizon/next query time is a planning input, not future
measurements. Header contains no future review-arrival list, source score hash
or incident information. True next cost is computed only for evaluation.

At illustrative 64/256 KiB caps, report true-feasible, false-feasible (promise
would fail), true-infeasible and false-infeasible (missed opportunity). A
forecast is not a guarantee: actual admission must recheck bytes; an incorrect
prediction cannot justify a completeness certificate. This test quantifies
predictability of growth, not human benefits or a measured field bottleneck.

No labels enter the forecasting rule or capacity costs. Existing coarse loader
may read labels to construct its unused event table; no event/query outcome is
passed to a forecast, selector or serializer. Repeated prefixes/backbones and
cadences are related observations and are not independent deployments. Use
descriptive counts, no significance tests or deployment frequency inference.
'''

def write_csv(path,rows):
    if not rows:return
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def future_free_header(header,now):
    h=driver.clean_header(header,now)
    for name in ('review_effective_source_samples','review_effective_cycles','review_sha256',
                 'score_sha256','receipt_sha256'):
        h.pop(name,None)
    return h

def streams(all_smd=False):
    # Paired cadence adapter guarantees shared fitted scores at shared times.
    receipts=fine.smd_receipts()
    pairs=fine.available() if all_smd else [(d,b) for d in DEVICES for b in BACKBONES]
    for entity,backbone in pairs:
        for stride in (10,1):
            d,a,h,hb,head,sel,pp,policy,paths=fine.load_smd(entity,backbone,stride,receipts)
            yield dict(dataset='SMD',unit=entity,backbone=backbone,
                       cadence='paired_coarse' if stride==10 else 'fine',
                       a=a,h=h,eligible=d['eligible'],header=head)
    for suite,p,j in driver.coarse_fits():
        if suite!='ESA' or not all_smd and str(j['arguments']['mission'])!='1':continue
        yield driver.load_coarse(suite,p,j)

def prefix_cost(s,stop):
    a=s['a'][s['a']['t']<stop]
    h=s['h'][:stop];usable=s['eligible'][:stop]
    head=future_free_header(s['header'],stop)
    ar=core.build_archive(a,h,usable,head,2**40,'full')
    assert ar.feasible and ar.numeric.tobytes()==a.tobytes()
    assert np.array_equal(ar.support,h.astype(np.int8))
    assert np.array_equal(ar.usability,usable.astype(np.int8))
    fixed=core.frame_bytes(head,'full')
    return dict(stop=stop,atoms=len(a),bytes=ar.size,header_bytes=fixed,
                payload_bytes=ar.size-fixed,file_sha256=hashlib.sha256(ar.blob).hexdigest())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--all-smd',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    stem='past_policy_all' if args.all_smd else 'past_policy'
    protocol=OUT/f'{stem}_protocol.md'
    declared=PROTOCOL
    if args.all_smd:
        declared+='''
## Recorded census extension after the targeted pilot

The ten-history pilot completed in 12.3 seconds, establishing feasibility.
Before this census execution the scope is expanded to ALL 56 existing SMD
device/backbone identities at BOTH paired schedules (112 histories), plus all
four ESA mission/backbone histories (116 total). This supersedes the selected
scope paragraph above only. The cost definition, forecasts, 1.0/1.25 factors,
quarter boundaries and caps are unchanged; no performance-dependent exclusion
or threshold tuning is permitted. The census is a post-pilot extension, not
preregistration or previously untouched external validation. All failures stay.
'''
    if protocol.exists():
        if protocol.read_text(encoding='utf-8')!=declared:raise RuntimeError('Declared protocol differs')
    else:protocol.write_text(declared,encoding='utf-8')
    began=time.perf_counter();costs=[];rows=[]
    for s in streams(args.all_smd):
        base=driver.key(s);n=len(s['h'])
        ends=[0]+[int(math.ceil(n*k/4)) for k in (1,2,3,4)]
        observed=[prefix_cost(s,t) for t in ends]
        costs.extend([dict(base,quarter=k,**r) for k,r in enumerate(observed)])
        for quarter in (1,2,3):
            current=observed[quarter];previous=observed[quarter-1];actual=observed[quarter+1]
            delta=max(0,current['payload_bytes']-previous['payload_bytes'])
            planned=future_free_header(s['header'],ends[quarter+1])
            known_header=core.frame_bytes(planned,'full')
            for factor in BUFFERS:
                forecast=known_header+math.ceil(factor*(current['payload_bytes']+delta))
                for budget in CAPS:
                    predict=forecast<=budget;truth=actual['bytes']<=budget
                    category=('true_feasible' if truth else 'false_feasible') if predict else ('false_infeasible' if truth else 'true_infeasible')
                    rows.append(dict(base,forecast_quarter=quarter,target_quarter=quarter+1,
                         observed_stop=current['stop'],target_stop=actual['stop'],factor=factor,budget=budget,
                         previous_payload_bytes=previous['payload_bytes'],current_payload_bytes=current['payload_bytes'],
                         observed_payload_increment=delta,known_next_header_bytes=known_header,
                         forecast_bytes=forecast,actual_next_bytes=actual['bytes'],
                         forecast_feasible=predict,actual_feasible=truth,classification=category,
                         signed_relative_error=(forecast-actual['bytes'])/actual['bytes']))
        print(json.dumps(dict(base,quarter_bytes=[r['bytes'] for r in observed[1:]],
                              elapsed_seconds=round(time.perf_counter()-began,2))),flush=True)
    summary=[]
    for dataset in ('SMD','ESA','all'):
        for cadence in ('paired_coarse','fine','coarse','all'):
            for budget in CAPS:
                for factor in BUFFERS:
                    rr=[r for r in rows if (dataset=='all' or r['dataset']==dataset) and (cadence=='all' or r['cadence']==cadence) and r['budget']==budget and r['factor']==factor]
                    if not rr:continue
                    counts={k:sum(r['classification']==k for r in rr) for k in ('true_feasible','false_feasible','true_infeasible','false_infeasible')}
                    summary.append(dict(dataset=dataset,cadence=cadence,budget=budget,factor=factor,
                          predictions=len(rr),histories=len({(r['dataset'],r['unit'],r['backbone'],r['cadence']) for r in rr}),
                          **counts,median_signed_relative_error=float(np.median([r['signed_relative_error'] for r in rr])),
                          max_underforecast_fraction=max(0,max(-r['signed_relative_error'] for r in rr))))
    write_csv(OUT/f'{stem}_prefix_costs.csv',costs)
    write_csv(OUT/f'{stem}_forecasts.csv',rows)
    write_csv(OUT/f'{stem}_summary.csv',summary)
    receipt=dict(passed=True,histories=len(costs)//5,prefix_costs=len(costs),forecast_conditions=len(rows),
                 no_training=True,selection_used_labels=False,forecast_is_guarantee=False,
                 prespecified_devices=sorted({p[0] for p in fine.available()}) if args.all_smd else list(DEVICES),
                 budgets=list(CAPS),fixed_payload_factors=list(BUFFERS),
                 scope='all frozen SMD/ESA histories, paired schedules where available' if args.all_smd else 'ten preselected stress/control histories',
                 elapsed_seconds=time.perf_counter()-began,
                 script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 core_sha256=hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest(),
                 protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
                 python=platform.python_version())
    (OUT/f'{stem}_completion.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt),flush=True)

if __name__=='__main__':main()
