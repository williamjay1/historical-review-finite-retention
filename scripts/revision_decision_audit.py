"""Post-result, descriptive decision audit. Immutable fitted scores; no deployment tuning."""
from __future__ import annotations
import argparse, csv, hashlib, json, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/revision_20261001/decision_audit'
GRID = [1., 1.1, 1.25, 1.5, 2., 3., 4., 8.]
GAPS = [0, 1, 3]
COOLDOWNS = [3, 6]
RULES = ['recognition', 'active_before_own', 'affected_before_own']
FROZEN = ['base','threshold','joint_nn','local_nn','constrained','constrained_nn',
          'joint_uncapped','no_veto','no_crossfit','no_duration','feedback_mil','mil_p25','mil_p10','mil_p05']
NAMES = FROZEN + [f'uniform_{v:g}' for v in GRID]
BURDENS = ['nominal_flagged_cycles'] + [f'nominal_notifications_gap{g}' for g in GAPS]

def readj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def ids(v): return json.dumps(sorted(str(x) for x in v), separators=(',',':'))
def jsave(p,v): Path(p).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def flag(v):
    if pd.isna(v): return False
    return str(v).lower() in ('true','1','1.0')

def labels_and_ranges(starts,ends,events):
    # Exact frozen evaluator logic, kept local to avoid importing training runtimes.
    y=np.zeros(len(starts),dtype=np.int8); unknown=np.zeros(len(starts),dtype=bool); ranges=[]
    for e in events:
        spans=[]
        for a,b in e['intervals']:
            i=int(np.searchsorted(ends,a,'left')); k=int(np.searchsorted(starts,b,'right'))
            if i>=k: continue
            spans.append([i,k]); v=2 if e['category']=='anomaly' else 1 if e['category']=='rare' else -1
            if v==-1: unknown[i:k]=True
            else: y[i:k]=np.maximum(y[i:k],v)
        if spans: ranges.append(dict(e,blocks=spans))
    y[unknown&(y!=2)]=-1
    return y,ranges

PLAN = """# Decision audit analysis plan

Written before this audit's pilot/full execution, after primary and threshold-reference outcomes were available. This is a transparent retrospective descriptive audit, not preregistered research.

Route: SCIE applied empirical ML validation. Question: do lower alarm-cycle volumes imply fewer notifications, and how does an explicit evidence-retention requirement alter admissibility and retrospective method choice? Standards are fair frozen-score comparisons, decision timing, relevant-channel evidence and reproducibility. Causal identification and new model training are outside this audit.

Scope: exactly 18 ESA primary fits (.995, budget 4, delay 24 hours, radius 1, memory 256, window 6 hours, scale calibration) and 252 SMD primary fits. The 14 frozen methods and all 8 uniform multipliers 1, 1.1, 1.25, 1.5, 2, 3, 4, 8 are reported. Pilot uses the first sorted ESA and SMD fit and can only change implementation after explicitly documented failures; it cannot choose multipliers, rules, weights or a preferred method.

The notification state machine uses only past/current alarm decisions, eligibility (ESA usable cycles; SMD complete cycles), and cycle indices. Labels never decide when to notify. A notification is sent on the first high cycle, then another is sent only if more than g low cycles intervene, g=0/1/3. An unusable cycle resets an episode. Thus diff(high-cycle indices)>g+1 starts a new episode; unknown annotations do not reset it. This is causally implementable without future data. Offline nominal notification starts require a valid non-anomaly cycle in ESA, and a completely nominal lookback bin in SMD, matching the existing volume definition. They are counts of a specified notification policy, not human hours or operational workload observations. Also report notification starts at nominal decision timestamps for SMD separately.

Event episode-contact means a sent episode contains at least one flagged cycle in that event's audited pre-own-feedback overlap bins; notification-start means the notification itself starts in those bins. Contacts include carried episodes and do not imply repeated notifications. ESA later-rare is the fixed saved cohort with a prior distinct same-class normal review, not proof of persistent memory/prototype reuse. Events still contacted and still receiving starts are reported with IDs. Simple baselines suppress base gap-0 notification starts falling within a fixed 3/6-cycle refractory interval after the last sent notification. They leave scores and frozen review tape unchanged; no claimed closed-loop counterfactual. Their notification-time active-before-own hits are reported separately from decision evidence.

All three decision constraints preserve the identity of every BASE hit: (i) overlap-bin incident recognition, (ii) active-period decision strictly before own feedback, and (iii) ESA affected-channel active-period evidence strictly before own feedback. Criterion (iii) is unavailable for SMD and is skipped, not replaced by global detection. Baseline non-hits are not required; zero baseline hits make a constraint vacuous and are disclosed. The audit retrospectively maximizes burden reduction under each constraint, separately for nominal flagged cycles and each notification policy. Tie order is the frozen receipt order, then increasing uniform multiplier. This oracle exercise illustrates decision-rule sensitivity and must never select deployment thresholds/methods using held-out annotations.

Matched-burden reference: for each frozen method, retain all uniform grid points with burden <= the method's burden; report their best baseline-hit retention count and full maximizing IDs. Matched-retention reference: retain uniform points whose retained baseline-hit set includes the method's retained baseline-hit set; report the minimum achievable grid burden and all tied cuts. No interpolation; no arbitrary tolerance; unattainable matches remain missing. Pareto dominance requires <= burden and a superset of retained baseline incident IDs, with strict improvement in burden or the set. Full points and nondominated IDs are saved.

Four descriptive event categories, for baseline-recognized incidents: complete loss (no recognition); only post-end (recognition but no active-period hit); no annotated affected corroboration (ESA active-period hit without active affected-channel hit); relevant active evidence retained (ESA active affected-channel or SMD active-period hit). Active-before-own retention is an additional clock flag; the fourth category alone does not imply timeliness before own feedback. Cases without a scheduled active decision opportunity are exposed rather than treated as model losses.

Conditional cost: in units of one notification, Delta C = (N_method - N_base) + lambda * L + rho * R, lambda,rho >= 0. L is the number of baseline active-before-own hits newly lost (also provide ESA affected version); R is shared requested review count for feedback methods, zero for base/uniform/cooldown. A fixed shadow tape is used for timing but uniform methods do not need its labels. Feedback costs share the same R even if updates are dormant; use requested and arrived-window counts separately. If B=N_base-N_method>0, benefit holds only when lambda L + rho R < B. Report intercepts and the entire inequality; no hand-picked weights, no artificial time conversion, no false assertion that costs are known. A secondary notification-time L is provided for cooldown because score evidence is unchanged while sent notifications may be delayed/lost.

Aggregation: ESA mission/backbone seed means and ranges; SMD seed means per device, then equally weighted device summaries and device-cluster bootstrap (2,000 draws, fixed seed 20261001) for notification reductions only. Resampling is conditional on fitted models and fixed tapes, not independent seeds/events or a population claim. Counts of fits, devices and incident identities are explicit. No significance testing or multi-comparison winner claims.

Compute: CPU read-only replay, no fitting, API calls or GPU use. Process one fit at a time. Pilot estimates runtime/storage before full replay; all outputs stay on D. Expected output <250 MB and temporary arrays <1 GB. Hash original receipts, scores, channel alarms, event results, reviews, cached complete ESA channel scores, frozen code/protocol and prior analysis reports before/after. Require exact reproduction of saved raw-score burdens and incident outcomes, uniform-one equality, all 14 score alarm sets subsets of base, and annotation/opportunity identities invariant. A subset violation is reported as a failure, not assumed away. Failure excludes no selected result silently: record failure and stop full audit until corrected.
"""

def write_plan():
    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/'ANALYSIS_PLAN.md'
    if not p.exists(): p.write_text(PLAN,encoding='utf-8')
    meta=OUT/'plan_receipt.json'
    if not meta.exists(): jsave(meta,dict(created_utc=datetime.now(timezone.utc).isoformat(),sha256=sha(p),stage='post-result retrospective; not preregistered',grid=GRID,gaps=GAPS,cooldowns=COOLDOWNS))

def receipts():
    esa=[]
    for p in sorted((ROOT/'results/runs').glob('*_final_*/run.json')):
        j=readj(p); a=j['arguments']
        if all(a[k]==v for k,v in dict(quantile=.995,budget=4,delay=24,radius=1,memory=256,window_hours=6,score_calibration='scale').items()): esa.append(('ESA',p,j))
    smd=[('SMD',p,readj(p)) for p in sorted((ROOT/'results/smd/runs/18db8f6ac8e5').glob('*/complete.json'))]
    assert len(esa)==18 and len(smd)==252
    return esa+smd

def episodes(mask, eligible, gap):
    """Return high positions, causal episode IDs on highs, and onset positions."""
    pos=np.flatnonzero(mask & eligible)
    if not len(pos): return pos,np.empty(0,np.int32),pos
    breaks=np.cumsum(~eligible,dtype=np.int32)
    new=np.r_[True,(np.diff(pos)>gap+1)|(breaks[pos[1:]]!=breaks[pos[:-1]])]
    return pos,np.cumsum(new,dtype=np.int32)-1,pos[new]

def cooldown_starts(onsets, cycles):
    keep=[]; last=-10**15
    for i in onsets:
        if i-last>cycles: keep.append(int(i)); last=i
    return np.asarray(keep,dtype=np.int64)

def intersections(pos, episode_id, idx, onsets, delivered=None):
    hit=np.intersect1d(pos,idx,assume_unique=True)
    count=0
    if len(hit):
        ep=np.unique(episode_id[np.searchsorted(pos,hit)])
        if delivered is not None: ep=ep[np.isin(ep,delivered)]
        count=len(ep)
    return count,len(np.intersect1d(onsets,idx,assume_unique=True))

def data_for(suite,p,j):
    folder=p.parent; saved=pd.read_csv(folder/'event_results.csv')
    if suite=='ESA':
        a=j['arguments']; lo,hi=j['offset'],j['end']; tau=j['threshold']
        d=ROOT/'datasets'/f"m{a['mission']}_{a['subset']}_b{a['block']}"
        starts=np.load(d/'starts.npy',mmap_mode='r'); ends=np.load(d/'ends.npy',mmap_mode='r'); usable=np.load(d/'usable.npy',mmap_mode='r')
        y,ranges=labels_and_ranges(starts,ends,readj(d/'events.json'))
        eligible=np.asarray(usable[lo:hi],bool); valid=eligible&(y[lo:hi]>=0); nominal=valid&(y[lo:hi]!=2)
        base=saved[saved.method=='base'].copy(); mapping={e['id']:e for e in ranges}; ev={}
        qpath=ROOT/'cache'/f"m{a['mission']}_{a['subset']}_b{a['block']}_final_{j['model_code_hash']}"/f"{a['backbone']}_s{a['seed']}_scores.npy"
        q=np.load(qpath,mmap_mode='r'); channels=j['data']['channels']; assert q.shape[1]==len(channels)<=64
        packed=np.load(folder/'channel_alarms.npy',mmap_mode='r'); assert packed.dtype==np.uint64
        for _,r in base.iterrows():
            ident=str(r['id']); e=mapping[ident]
            idx=np.unique(np.concatenate([np.arange(max(x,lo)-lo,min(z,hi)-lo) for x,z in e['blocks'] if x<hi and z>lo]))
            idx=idx[valid[idx]]
            if e['category']=='rare': idx=idx[y[lo+idx]==1]
            active=np.zeros(len(idx),bool)
            for st,en in e['intervals']: active|=(ends[lo+idx]>=st)&(ends[lo+idx]<=en)
            cutoff=hi if pd.isna(r.own_feedback_arrival_block) else int(r.own_feedback_arrival_block)
            pre=idx[lo+idx<cutoff]; act=idx[active]; actpre=act[lo+act<cutoff]
            affected=[]
            if e['category']=='anomaly':
                for ch,st,en in e.get('channel_intervals',[]):
                    ia=max(lo,int(np.searchsorted(ends,st,'left'))); ib=min(hi,int(np.searchsorted(starts,en,'right')))
                    if ia>=ib: continue
                    ii=np.arange(ia-lo,ib-lo); ii=ii[valid[ii]]
                    aa=ii[(ends[lo+ii]>=st)&(ends[lo+ii]<=en)]
                    affected.append((aa,aa[lo+aa<cutoff],channels.index(ch)))
            ev[ident]=dict(category=e['category'],idx=idx,pre=pre,active=act,activepre=actpre,affected=affected,
                repeated_rare=flag(r.previous_different_event_same_class_reviewed),cutoff=cutoff,
                opportunity=bool(len(actpre)),affected_opportunity=bool(any(len(z) for _,z,_ in affected)))
        unit=str(a['mission']); backbone=a['backbone']; seed=a['seed']; duration=float(np.median(np.diff(ends))/1e9)
        return dict(tau=tau,eligible=eligible,valid=valid,nominal=nominal,nominal_decision=nominal,events=ev,saved=saved,
                    unit=unit,backbone=backbone,seed=seed,q=q,qpath=qpath,packed=packed,lo=lo,duration=duration)
    labels=np.loadtxt(Path(j['data']['working_directory'])/'test_label.txt',dtype=np.int8)
    n=j['data']['test_blocks']; b=j['data']['block_size']; times=(np.arange(n)+1)*b-1; starts=np.arange(n)*b
    nominal=np.all(labels[:n*b].reshape(n,b)==0,axis=1); ev={}
    for _,r in saved[saved.method=='base'].iterrows():
        ident=str(int(r.event_id)); a,z=int(r.start_sample),int(r.end_sample_exclusive)
        ix=np.flatnonzero((starts<z)&(times>=a)); act=np.flatnonzero((times>=a)&(times<z))
        cutoff=int(r.own_feedback_effective_decision_sample) if not pd.isna(r.own_feedback_effective_decision_sample) else len(labels)+b
        ev[ident]=dict(category='anomaly',idx=ix,pre=ix[times[ix]<cutoff],active=act,activepre=act[times[act]<cutoff],affected=[],
                      repeated_rare=False,cutoff=cutoff,opportunity=bool(len(act[times[act]<cutoff])),affected_opportunity=None)
    return dict(tau=j['model']['threshold'],eligible=np.ones(n,bool),valid=np.ones(n,bool),nominal=nominal,
                nominal_decision=labels[times]==0,events=ev,saved=saved,unit=j['entity'],backbone=j['backbone'],seed=j['seed'],duration=b)

def run_one(suite,p,j,notify_writer):
    d=data_for(suite,p,j); folder=p.parent; scores=np.load(folder/'scores.npy',mmap_mode='r'); tau=d['tau']
    assert j['methods']==FROZEN and scores.shape[1]==14
    masks=[np.asarray(scores[:,k]>=tau) for k in range(14)]
    masks += [np.asarray(scores[:,0]>=mul*tau) for mul in GRID]
    assert np.array_equal(masks[0],masks[14]); assert all(not np.any(m&~masks[0]) for m in masks)
    originals=[p,folder/'scores.npy',folder/'event_results.csv',folder/'reviews.json']
    originals += [folder/'metrics.json',folder/'channel_alarms.npy',d['qpath']] if suite=='ESA' else [folder/'metrics.csv',Path(j['data']['working_directory'])/'test_label.txt']
    seals={str(x.relative_to(ROOT)):sha(x) for x in originals}
    if suite=='ESA':
        q=d['q']; lo=d['lo']
        for a in range(0,len(scores),8192): assert np.array_equal(q[lo+a:lo+min(a+8192,len(scores))].max(1),scores[a:min(a+8192,len(scores)),0])
    else: assert seals[str((Path(j['data']['working_directory'])/'test_label.txt').relative_to(ROOT))]==j['data']['label_working_copy_sha256']
    refpath=ROOT/'results/threshold_reference_20260930'/('esa' if suite=='ESA' else 'smd')/folder.name/'events.csv'
    refs=pd.read_csv(refpath); combined=pd.concat([d['saved'],refs[refs.method!='base']],ignore_index=True)
    idcol='id' if suite=='ESA' else 'event_id'; combined['_id']=combined[idcol].map(lambda v:str(v) if suite=='ESA' else str(int(v)))
    stored=combined.set_index(['method','_id']); originalmetrics=readj(folder/'metrics.json') if suite=='ESA' else pd.read_csv(folder/'metrics.csv').set_index('method').to_dict('index')
    metric=[]; eventrows=[]; evidence={}; notify_hits={}
    shared=dict(dataset=suite,run=folder.name,unit=d['unit'],backbone=d['backbone'],seed=d['seed'])
    nominal=d['nominal']; request=int(j['requested_reviews']); arrived=int(j['arrived_reviews'])
    for k,(name,mask) in enumerate(zip(NAMES,masks)):
        epoints={r:set() for r in RULES}; notification_pointsets={g:set() for g in GAPS}
        row=dict(shared,method=name,nominal_flagged_cycles=int((mask&nominal).sum()),nominal_cycles=int(nominal.sum()),
                 flagged_cycles=int((mask&d['eligible']).sum()),review_requests=(request if name in FROZEN[1:] else 0),review_arrivals=(arrived if name in FROZEN[1:] else 0))
        row['later_rare_events']=sum(e['repeated_rare'] for e in d['events'].values())
        if name in FROZEN:
            savedvolume=originalmetrics[name]['false_alarm_hours']/ (d['duration']/3600) if suite=='ESA' else originalmetrics[name]['nominal_flagged_bins']
            assert np.isclose(row['nominal_flagged_cycles'],savedvolume,atol=1e-7), (folder.name,name,'burden')
        policies={g:episodes(mask,d['eligible'],g) for g in GAPS}
        for g,(pos,ep,onsets) in policies.items():
            row[f'all_notifications_gap{g}']=len(onsets)
            row[f'nominal_notifications_gap{g}']=int(nominal[onsets].sum())
            row[f'nominal_decision_notifications_gap{g}']=int(d['nominal_decision'][onsets].sum())
            row[f'nominal_contacts_gap{g}']=intersections(pos,ep,np.flatnonzero(nominal),onsets)[0]
            row[f'later_rare_contacted_events_gap{g}']=0; row[f'later_rare_started_events_gap{g}']=0
            row[f'later_rare_notification_starts_gap{g}']=0; row[f'later_rare_episode_contacts_gap{g}']=0
        for ident,e in d['events'].items():
            isfault=e['category']=='anomaly'
            hit=bool(mask[e['idx']].any()); act=bool(mask[e['active']].any()); pre=bool(mask[e['activepre']].any()); aff=False; affany=False
            if isfault and suite=='ESA':
                for ai,pi,ch in e['affected']:
                    if k<14:
                        bit=np.left_shift(np.uint64(1),np.uint64(ch)); cm=j['channel_methods'].index(name)
                        affany |= bool(np.any((d['packed'][ai,cm]&bit)!=0)); aff |= bool(np.any((d['packed'][pi,cm]&bit)!=0))
                    else:
                        affany |= bool(np.any(d['q'][d['lo']+ai,ch]>=GRID[k-14]*tau)); aff |= bool(np.any(d['q'][d['lo']+pi,ch]>=GRID[k-14]*tau))
            if isfault:
                old=stored.loc[(name,ident)]
                assert hit==flag(old.detected) and act==flag(old.active_event_detected),(folder.name,name,ident,'recognition')
                activecol='active_detected_before_own_feedback' if suite=='ESA' else 'active_event_detected_before_own_feedback'
                assert pre==flag(old[activecol]),(folder.name,name,ident,'active-before')
                assert e['opportunity']==flag(old['active_decision_opportunity_before_own_feedback' if suite=='ESA' else 'active_before_own_feedback_opportunity'])
                if suite=='ESA': assert aff==flag(old.active_affected_channel_detected_before_own_feedback) and affany==flag(old.active_affected_channel_detected),(folder.name,name,ident,'affected')
                if hit: epoints['recognition'].add(ident)
                if pre: epoints['active_before_own'].add(ident)
                if aff: epoints['affected_before_own'].add(ident)
                cat='complete_loss' if not hit else 'only_post_end' if not act else 'no_annotated_affected_corroboration' if suite=='ESA' and not affany else 'relevant_active_evidence_retained'
                eventrows.append(dict(shared,method=name,incident_id=ident,recognized=hit,active_any=act,active_before_own=pre,
                    affected_active_any=(affany if suite=='ESA' else None),affected_before_own=(aff if suite=='ESA' else None),
                    active_before_own_opportunity=e['opportunity'],affected_before_own_opportunity=e['affected_opportunity'],evidence_category=cat))
            if isfault or e['repeated_rare']:
                for g,(pos,ep,onsets) in policies.items():
                    contacts,starts=intersections(pos,ep,e['pre'],onsets)
                    timely_start=bool(np.intersect1d(onsets,e['activepre'],assume_unique=True).size)
                    if timely_start and isfault: notification_pointsets[g].add(ident)
                    notify_writer.writerow(dict(shared,method=name,gap_cycles=g,cooldown_cycles=0,incident_id=ident,category=e['category'],
                        later_rare=e['repeated_rare'],preown_episode_contacts=contacts,preown_notification_starts=starts,
                        active_before_own_notification_start=timely_start))
                    if e['repeated_rare']:
                        row[f'later_rare_contacted_events_gap{g}']+=int(contacts>0); row[f'later_rare_started_events_gap{g}']+=int(starts>0)
                        row[f'later_rare_notification_starts_gap{g}']+=starts; row[f'later_rare_episode_contacts_gap{g}']+=contacts
        for r in RULES: row[f'{r}_hit_count']=len(epoints[r]); row[f'{r}_hit_ids']=ids(epoints[r])
        for g in GAPS: row[f'active_before_own_notification_hits_gap{g}']=len(notification_pointsets[g])
        evidence[name]=epoints; notify_hits[name]=notification_pointsets
        metric.append(row)
    base=metric[0]
    for row in metric:
        row['alarm_cycles_removed']=base['flagged_cycles']-row['flagged_cycles']
        for g in GAPS:
            row[f'extra_nominal_notifications_gap{g}']=row[f'nominal_notifications_gap{g}']-base[f'nominal_notifications_gap{g}']
            row[f'notification_increase_with_subset_gap{g}']=row[f'extra_nominal_notifications_gap{g}']>0
    for c in COOLDOWNS:
        pos,ep,onsets=episodes(masks[0],d['eligible'],0); kept=cooldown_starts(onsets,c); delivered=ep[np.searchsorted(pos,kept)]
        row=dict(shared,method=f'base_cooldown{c}',nominal_flagged_cycles=base['nominal_flagged_cycles'],nominal_cycles=base['nominal_cycles'],flagged_cycles=base['flagged_cycles'],review_requests=0,review_arrivals=0,
                 cooldown_cycles=c,all_notifications_gap0=len(kept),nominal_notifications_gap0=int(nominal[kept].sum()),
                 nominal_decision_notifications_gap0=int(d['nominal_decision'][kept].sum()),nominal_contacts_gap0=intersections(pos,ep,np.flatnonzero(nominal),kept,delivered)[0],
                 later_rare_contacted_events_gap0=0,later_rare_started_events_gap0=0,later_rare_notification_starts_gap0=0,later_rare_episode_contacts_gap0=0)
        notif=set()
        for ident,e in d['events'].items():
            if e['category']=='anomaly' or e['repeated_rare']:
                contacts,starts=intersections(pos,ep,e['pre'],kept,delivered); timely=bool(np.intersect1d(kept,e['activepre'],assume_unique=True).size)
                if timely and e['category']=='anomaly': notif.add(ident)
                notify_writer.writerow(dict(shared,method=row['method'],gap_cycles=0,cooldown_cycles=c,incident_id=ident,category=e['category'],later_rare=e['repeated_rare'],preown_episode_contacts=contacts,preown_notification_starts=starts,active_before_own_notification_start=timely))
                if e['repeated_rare']:
                    row['later_rare_contacted_events_gap0']+=int(contacts>0); row['later_rare_started_events_gap0']+=int(starts>0); row['later_rare_notification_starts_gap0']+=starts; row['later_rare_episode_contacts_gap0']+=contacts
        row['active_before_own_notification_hits_gap0']=len(notif)
        notify_hits[row['method']]={0:notif}
        row['new_notification_timely_loss']=len(notify_hits['base'][0]-notif)
        metric.append(row)
    acceptance=[]; choice=[]; boundary=[]; matched=[]; costs=[]
    byname={r['method']:r for r in metric}
    applicable=RULES if suite=='ESA' else RULES[:2]
    for rule in applicable:
        bh=evidence['base'][rule]
        retained={name:evidence[name][rule]&bh for name in NAMES}
        for name in NAMES:
            acceptance.append(dict(shared,rule=rule,method=name,accepted=bh.issubset(evidence[name][rule]),
                baseline_hit_count=len(bh),constraint_vacuous=not bh,baseline_hit_ids=ids(bh),retained_baseline_hit_ids=ids(retained[name]),lost_baseline_hit_ids=ids(bh-evidence[name][rule])))
        for burden in BURDENS:
            admissible=[name for name in NAMES if bh.issubset(evidence[name][rule])]
            best=min(admissible,key=lambda name:(byname[name][burden],NAMES.index(name)))
            choice.append(dict(shared,rule=rule,burden=burden,selected_method=best,baseline_burden=base[burden],selected_burden=byname[best][burden],
                reduction_fraction=(1-byname[best][burden]/base[burden]) if base[burden] else None,baseline_hit_count=len(bh),retained_baseline_hit_ids=ids(retained[best]),oracle_not_deployable=True))
            for name in NAMES:
                dominators=[other for other in NAMES if byname[other][burden]<=byname[name][burden] and retained[name].issubset(retained[other]) and (byname[other][burden]<byname[name][burden] or retained[name]!=retained[other])]
                boundary.append(dict(shared,rule=rule,burden=burden,method=name,burden_value=byname[name][burden],baseline_hit_count=len(bh),
                    retained_hit_count=len(retained[name]),retained_baseline_hit_ids=ids(retained[name]),nondominated=not dominators,dominated_by=ids(dominators)))
            for name in FROZEN:
                cuts=[x for x in NAMES[14:] if byname[x][burden]<=byname[name][burden]]
                n=max((len(retained[x]) for x in cuts),default=None); bc=[x for x in cuts if len(retained[x])==n]
                rmatch=[x for x in NAMES[14:] if retained[name].issubset(retained[x])]
                bmin=min((byname[x][burden] for x in rmatch),default=None); rc=[x for x in rmatch if byname[x][burden]==bmin]
                matched.append(dict(shared,rule=rule,burden=burden,method=name,method_burden=byname[name][burden],method_retained_hit_ids=ids(retained[name]),
                    matched_burden_feasible=bool(cuts),matched_burden_best_retention_count=n,matched_burden_best_cuts=ids(bc),
                    matched_burden_retained_ids_by_cut=json.dumps({x:sorted(retained[x]) for x in bc},separators=(',',':')),
                    matched_retention_feasible=bool(rmatch),matched_retention_min_burden=bmin,matched_retention_cuts=ids(rc),
                    uniform_grid_dominates_method=any(byname[x][burden]<=byname[name][burden] and retained[name].issubset(retained[x]) and (byname[x][burden]<byname[name][burden] or retained[x]!=retained[name]) for x in NAMES[14:])))
    for row in metric:
        name=row['method']; cooldown=name.startswith('base_cooldown')
        for gap in ([0] if cooldown else GAPS):
            for rule in ((RULES[1:] if suite=='ESA' else ['active_before_own'])+['notification_active_before_own']):
                loss=len(notify_hits['base'][gap]-notify_hits[name][gap]) if rule=='notification_active_before_own' else 0 if cooldown else len(evidence['base'][rule]-evidence[name][rule])
                B=base[f'nominal_notifications_gap{gap}']-row[f'nominal_notifications_gap{gap}']; R=row['review_requests']
                costs.append(dict(shared,method=name,gap_cycles=gap,loss_endpoint=rule,notification_saving=B,new_untimely_loss=loss,review_requests=R,review_arrivals=row['review_arrivals'],
                    nonnegative_cost_advantage_possible=B>0,lambda_intercept=(B/loss if B>0 and loss else None),rho_intercept=(B/R if B>0 and R else None),
                    advantage_region=f'{loss} * lambda + {R} * rho < {B}; lambda,rho >= 0',
                    lambda_unbounded_if_rho0=bool(B>0 and not loss),rho_unbounded_if_lambda0=bool(B>0 and not R),
                    cooldown_new_notification_timely_loss=row.get('new_notification_timely_loss') if cooldown else None))
    assert seals=={str(x.relative_to(ROOT)):sha(x) for x in originals},'Source file changed'
    return metric,eventrows,acceptance,choice,boundary,matched,costs,dict(shared,passed=True,source_sha256=seals,
                channel_count=(len(j['data']['channels']) if suite=='ESA' else None),uint64_channels=(suite=='ESA'),all_candidates_subset_base=True)

def aggregate(metric,events,acceptance,choices,costs,target):
    m=pd.DataFrame(metric); e=pd.DataFrame(events); ac=pd.DataFrame(acceptance); ch=pd.DataFrame(choices); co=pd.DataFrame(costs)
    # Descriptive counts are fit counts; device IDs are separate and seeds are never independent devices.
    accepts=[]
    for (suite,rule,method),g in ac.groupby(['dataset','rule','method']):
        bad=g[~g.accepted]
        accepts.append(dict(dataset=suite,rule=rule,method=method,fits=len(g),accepted_fits=int(g.accepted.sum()),rejected_fits=len(bad),
            vacuous_fits=int(g.constraint_vacuous.sum()),rejected_units=int(bad.unit.nunique()),
            affected_fit_incident_records=sum(len(json.loads(v)) for v in bad.lost_baseline_hit_ids),
            affected_unique_unit_incidents=len({(r.unit,i) for _,r in bad.iterrows() for i in json.loads(r.lost_baseline_hit_ids)})))
    switches=[]; switchdetails=[]
    for suite in ['ESA','SMD']:
        for burden in BURDENS:
            g=ch[(ch.dataset==suite)&(ch.burden==burden)]
            if g.empty: continue
            base=g[g.rule=='recognition'].set_index('run')
            for rule in (RULES[1:] if suite=='ESA' else ['active_before_own']):
                strict=g[g.rule==rule].set_index('run'); changed=base.selected_method!=strict.selected_method
                units=base[changed].unit.nunique(); incidentset=set(); records=0
                for run,r in base[changed].iterrows():
                    hit=ac[(ac.run==run)&(ac.rule==rule)&(ac.method==r.selected_method)].iloc[0]
                    lost=json.loads(hit.lost_baseline_hit_ids); records+=len(lost); incidentset.update((r.unit,x) for x in lost)
                    ss=strict.loc[run]
                    switchdetails.append(dict(dataset=suite,run=run,unit=r.unit,backbone=r.backbone,seed=int(r.seed),burden=burden,
                        stricter_rule=rule,recognition_choice=r.selected_method,stricter_choice=ss.selected_method,
                        recognition_choice_burden=int(r.selected_burden),stricter_choice_burden=int(ss.selected_burden),
                        lost_baseline_hit_ids_by_recognition_choice=hit.lost_baseline_hit_ids))
                switches.append(dict(dataset=suite,burden=burden,comparison=f'recognition_vs_{rule}',fits=len(base),changed_fits=int(changed.sum()),
                    changed_units=int(units),lost_fit_incident_records_in_recognition_choice=records,lost_unique_unit_incidents_in_recognition_choice=len(incidentset),
                    recognition_choices=base.selected_method.value_counts().to_dict(),stricter_choices=strict.selected_method.value_counts().to_dict()))
    categories=[]
    for (suite,method),g in e.groupby(['dataset','method']):
        b=e[(e.dataset==suite)&(e.method=='base')].set_index(['run','incident_id'])
        ix=pd.MultiIndex.from_frame(g[['run','incident_id']]); valid=b.reindex(ix).recognized.to_numpy(dtype=bool)
        h=g[valid]
        categories.append(dict(dataset=suite,method=method,baseline_recognized_fit_incident_records=len(h),
            evidence_categories=h.evidence_category.value_counts().to_dict(),
            active_before_own_retained_fit_incident_records=int(h.active_before_own.sum()),
            affected_before_own_retained_fit_incident_records=(int(h.affected_before_own.sum()) if suite=='ESA' else None)))
    summaries=[]; rng=np.random.default_rng(20261001)
    num=[c for c in m.columns if ('notifications_gap' in c or 'later_rare_' in c or c in ['nominal_flagged_cycles','nominal_cycles','alarm_cycles_removed']) and pd.api.types.is_numeric_dtype(m[c])]
    for suite in ['ESA','SMD']:
        groups=['unit','backbone','method']
        seedmean=m[m.dataset==suite].groupby(groups)[num].mean().reset_index(); seedmean.to_csv(target/f'{suite.lower()}_seed_collapsed.csv',index=False)
        for key,g in seedmean.groupby(['backbone','method'] if suite=='SMD' else ['unit','backbone','method']):
            if suite=='SMD': backbone,method=key; unit='all28'; baseline=seedmean[(seedmean.backbone==backbone)&(seedmean.method=='base')].set_index('unit').sort_index(); h=g.set_index('unit').sort_index(); assert len(h)==len(baseline)
            else: unit,backbone,method=key; baseline=seedmean[(seedmean.unit==unit)&(seedmean.backbone==backbone)&(seedmean.method=='base')].set_index('unit'); h=g.set_index('unit')
            row=dict(dataset=suite,unit=unit,backbone=backbone,method=method,units=len(h),nominal_flagged_cycles_mean=float(h.nominal_flagged_cycles.mean()))
            for gap in ([0] if str(method).startswith('base_cooldown') else GAPS):
                col=f'nominal_notifications_gap{gap}'; bb=baseline[col].to_numpy(); hh=h[col].to_numpy(); red=(1-hh.mean()/bb.mean()) if bb.mean() else None
                row[col+'_mean']=float(hh.mean()); row[f'notification_reduction_gap{gap}']=red
                row[f'later_rare_contacted_events_gap{gap}_mean']=float(h[f'later_rare_contacted_events_gap{gap}'].mean())
                row[f'later_rare_started_events_gap{gap}_mean']=float(h[f'later_rare_started_events_gap{gap}'].mean())
                if suite=='SMD':
                    ix=rng.integers(0,len(bb),size=(2000,len(bb))); den=bb[ix].mean(1); vals=(1-hh[ix].mean(1)/den); row[f'notification_reduction_gap{gap}_ci95']=np.quantile(vals,[.025,.975]).tolist()
            summaries.append(row)
    # Summed finite-horizon costs after seed collapse. Missions remain separate; all SMD devices contribute equally in summation.
    costsummary=[]
    group=['dataset','unit','backbone','method','gap_cycles','loss_endpoint']
    collapsed=co.groupby(group)[['notification_saving','new_untimely_loss','review_requests','review_arrivals']].mean().reset_index()
    for suite in ['ESA','SMD']:
        key=['unit','backbone','method','gap_cycles','loss_endpoint'] if suite=='ESA' else ['backbone','method','gap_cycles','loss_endpoint']
        for names,g in collapsed[collapsed.dataset==suite].groupby(key):
            values=dict(zip(key,names)); B=float(g.notification_saving.sum()); L=float(g.new_untimely_loss.sum()); R=float(g.review_requests.sum())
            costsummary.append(dict(dataset=suite,**values,notification_saving=B,new_untimely_loss=L,review_requests=R,review_arrivals=float(g.review_arrivals.sum()),
                advantage_region=f'{L:g} * lambda + {R:g} * rho < {B:g}; lambda,rho >= 0',
                lambda_intercept=(B/L if B>0 and L else None),rho_intercept=(B/R if B>0 and R else None),nonnegative_cost_advantage_possible=B>0))
    result=dict(stage='Retrospective descriptive post-result audit; not a deployment selection',
        esa_fits=int(m[m.dataset=='ESA'].run.nunique()),smd_fits=int(m[m.dataset=='SMD'].run.nunique()),
        methods=FROZEN,uniform_grid=GRID,gaps=GAPS,cooldowns=COOLDOWNS,
        acceptance=accepts,selection_rule_switches=switches,evidence_categories=categories,notification_summaries=summaries,cost_summaries=costsummary,
        fragmentation=[dict(dataset=suite,method=method,**{f'fits_increased_gap{gap}':int(g[f'notification_increase_with_subset_gap{gap}'].sum()) for gap in GAPS}) for (suite,method),g in m[~m.method.str.startswith('base_cooldown')].groupby(['dataset','method'])],
        inference='Conditional on saved fitted backbones, fixed review streams and observed held-out annotations. No deployment winner, labour-time or causal operational benefit claim.')
    jsave(target/'summary.json',result)
    pd.DataFrame(accepts).to_csv(target/'acceptance_summary.csv',index=False); pd.DataFrame(switches).to_csv(target/'selection_switch_summary.csv',index=False)
    pd.DataFrame(switchdetails).to_csv(target/'selection_switch_details.csv',index=False)
    increases=m[~m.method.str.startswith('base_cooldown')].copy()
    increases=increases[increases[[f'notification_increase_with_subset_gap{g}' for g in GAPS]].fillna(False).any(axis=1)]
    increases.to_csv(target/'notification_increases.csv',index=False)
    pd.DataFrame(categories).to_csv(target/'evidence_category_summary.csv',index=False); pd.DataFrame(costsummary).to_csv(target/'cost_summary.csv',index=False)
    return result

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--phase',choices=['plan','pilot','full'],default='plan'); args=parser.parse_args(); write_plan()
    if args.phase=='plan': print(str(OUT/'ANALYSIS_PLAN.md')); return
    allruns=receipts(); runs=[allruns[0],allruns[18]] if args.phase=='pilot' else allruns
    target=OUT/args.phase; target.mkdir(exist_ok=True)
    inputs=[ROOT/'results/FROZEN_PROTOCOL.json',ROOT/'results/threshold_reference_20260930/summary.json']+list((ROOT/'results').glob('final_analysis*.json'))
    protocol=readj(inputs[0]); inputs += sorted({ROOT/'scripts'/x for suite in ['esa','smd'] for x in protocol[suite]['code_sha256']})
    before={str(p.relative_to(ROOT)):sha(p) for p in inputs}; started=time.time(); collect=[[] for _ in range(8)]
    fields=['dataset','run','unit','backbone','seed','method','gap_cycles','cooldown_cycles','incident_id','category','later_rare','preown_episode_contacts','preown_notification_starts','active_before_own_notification_start']
    failures=[]
    with (target/'event_notifications.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for n,(suite,p,j) in enumerate(runs,1):
            try:
                out=run_one(suite,p,j,writer)
                for k,values in enumerate(out): collect[k].extend(values if isinstance(values,list) else [values])
            except Exception as exc:
                failures.append(dict(dataset=suite,run=p.parent.name,error=repr(exc))); jsave(target/'failures.json',failures); raise
            print(f'{args.phase} {n}/{len(runs)} {suite} {p.parent.name}',flush=True)
    names=['run_metrics','event_evidence','acceptance','oracle_choices','attainable_boundary','matched_uniform_grid','conditional_costs']
    for name,values in zip(names,collect[:7]): pd.DataFrame(values).to_csv(target/f'{name}.csv',index=False)
    result=aggregate(*[collect[k] for k in [0,1,2,3,6]],target)
    after={str(p.relative_to(ROOT)):sha(p) for p in inputs}; assert before==after,'Frozen inputs changed'
    receipt=dict(phase=args.phase,passed=not failures,completed_fits=len(runs),elapsed_seconds=time.time()-started,
        script_sha256=sha(Path(__file__)),plan_sha256=sha(OUT/'ANALYSIS_PLAN.md'),input_sha256=before,run_validation=collect[7],
        output_bytes=sum(p.stat().st_size for p in target.glob('*') if p.is_file()),failures=failures)
    jsave(target/'validation.json',receipt)
    print(json.dumps({k:receipt[k] for k in ['phase','passed','completed_fits','elapsed_seconds','output_bytes']},indent=2),flush=True)
    if args.phase=='pilot':
        jsave(OUT/'PILOT_RESOURCE_ESTIMATE.json',dict(pilot_seconds=receipt['elapsed_seconds'],full_upper_linear_seconds=receipt['elapsed_seconds']*135,
            pilot_output_bytes=receipt['output_bytes'],upper_linear_output_bytes=receipt['output_bytes']*135,cpu_only=True,gpu_hours=0,api_calls=0,storage_drive='D',
            limitation='One ESA and one SMD pilot; ESA expensive long-cycle passes make the balanced linear extrapolation conservative for the 18/252 suite.'))

if __name__=='__main__': main()
