"""Post-result temporal selection diagnostic on frozen score streams.

Owned workflow outputs only. No training, threshold tuning, future objective
selection, new feedback, or native/raw data writes.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, time, ctypes
from ctypes import wintypes
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import revision_decision_audit as frozen
import notification_design as system

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results/revision_notification_design_20261001/workflow"
ORDER=["base","local_nn","constrained","locked_local","locked_constrained"]
SOURCE={"base":"base","local_nn":"local_nn","constrained":"constrained",
        "locked_local":"local_nn","locked_constrained":"constrained"}
FIELDS=["dataset","run","unit","backbone","seed"]

def memory_peak():
    """Windows-reported process peak working set; no optional dependency."""
    size=ctypes.c_size_t
    class Counters(ctypes.Structure):
        _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
            ("PeakWorkingSetSize",size),("WorkingSetSize",size),
            ("QuotaPeakPagedPoolUsage",size),("QuotaPagedPoolUsage",size),
            ("QuotaPeakNonPagedPoolUsage",size),("QuotaNonPagedPoolUsage",size),
            ("PagefileUsage",size),("PeakPagefileUsage",size)]
    get=ctypes.windll.kernel32.GetCurrentProcess
    get.restype=wintypes.HANDLE; get.argtypes=[]
    info=ctypes.windll.psapi.GetProcessMemoryInfo
    info.restype=wintypes.BOOL; info.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    c=Counters();c.cb=ctypes.sizeof(c)
    if not info(get(),ctypes.byref(c),c.cb): raise ctypes.WinError()
    assert c.PeakWorkingSetSize>0
    return int(c.PeakWorkingSetSize)

def policy_id(p): return f"{p['method']}_g{p['parent_gap']}_c{p['cooldown_cycles']}"
def js(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def jdump(p,x): Path(p).write_text(json.dumps(x,indent=2,allow_nan=False),encoding="utf-8")
def packed_ids(x): return json.dumps(sorted(map(str,x)),separators=(",",":"))
def candidates():
    p=js(OUT/"selector_protocol.json")
    assert p["candidate_count"]==21
    assert len(p["candidates"])==21
    return p["candidates"]
def rank(p): return (p["method"]!="base",p["parent_gap"],p["cooldown_cycles"],ORDER.index(p["method"]))

def parent_data(base,eligible,g):
    pos,pid,initial=frozen.episodes(base,eligible,g)
    count=len(initial); first=np.full(count,len(base),np.int64); last=np.full(count,-1,np.int64)
    if len(pos):
        np.minimum.at(first,pid,pos); np.maximum.at(last,pid,pos)
    bad=np.minimum.accumulate(np.where(~eligible,np.arange(len(base)),len(base))[::-1])[::-1]
    close=np.minimum(last+g+1,bad[np.maximum(last,0)]) if count else last
    return dict(pos=pos,pid=pid,initial=initial,first=first,last=last,close=close)

def replay(base,corr,eligible,p,parent=None):
    """Vectorized causal replay. Every prefix is invariant to future values."""
    g=p["parent_gap"]; c=p["cooldown_cycles"]
    assert not np.any(corr & ~base)
    b=parent if parent is not None else parent_data(base,eligible,g)
    count=len(b["initial"]); first_corr=np.full(count,len(base),np.int64)
    if len(b["pos"]):
        valid=corr[b["pos"]]; np.minimum.at(first_corr,b["pid"][valid],b["pos"][valid])
    if p["method"].startswith("locked_"):
        mask=np.zeros(len(base),bool)
        if len(b["pos"]): mask[b["pos"]]=b["pos"]>=first_corr[b["pid"]]
    else: mask=corr & eligible
    _,_,onsets=frozen.episodes(mask,eligible,g)
    starts=frozen.cooldown_starts(onsets,c) if c else onsets
    first_sent=np.full(count,len(base),np.int64)
    if len(starts):
        sid=b["pid"][np.searchsorted(b["pos"],starts)]
        np.minimum.at(first_sent,sid,starts)
    task_parent=b if p["method"].startswith("locked_") else parent_data(mask,eligible,g)
    task_first_sent=np.full(len(task_parent["initial"]),len(base),np.int64)
    if len(starts):
        sid=task_parent["pid"][np.searchsorted(task_parent["pos"],starts)]
        np.minimum.at(task_first_sent,sid,starts)
    delta=np.zeros(len(base)+1,np.int32)
    valid=task_first_sent<len(base)
    if valid.any():
        np.add.at(delta,task_first_sent[valid],1); np.add.at(delta,task_parent["close"][valid],-1)
    task=np.cumsum(delta[:-1])>0
    # A score-restoring lock and parent-keyed delivery-only dedup are equivalent
    # in notification timestamps, but differ in score hits.
    if p["method"].startswith("locked_"):
        dedup=first_corr[first_corr<len(base)]
        dedup=frozen.cooldown_starts(dedup,c) if c else dedup
        assert np.array_equal(starts,dedup)
        assert len(onsets)<=len(b["initial"])
    assert not np.any(mask & ~base)
    return dict(mask=mask,starts=starts,onsets=onsets,task=task,first_sent=first_sent,
                first_corr=first_corr,parent=b,task_parent=task_parent,task_first_sent=task_first_sent)

def self_checks():
    rng=np.random.default_rng(20261001); tests=0
    for _ in range(8):
        base=rng.random(97)<.58; corr=base&(rng.random(97)<.55); eligible=rng.random(97)>.12
        for p in candidates():
            full=replay(base,corr if p["method"]!="base" else base,eligible,p)
            for k in [1,10,38,60,96]:
                pre=replay(base[:k],(corr if p["method"]!="base" else base)[:k],eligible[:k],p)
                assert np.array_equal(pre["mask"],full["mask"][:k])
                assert np.array_equal(pre["starts"],full["starts"][full["starts"]<k])
                assert np.array_equal(pre["task"],full["task"][:k])
                tests+=1
    # Total bound does not give a nominal bound: delayed first high moves
    # from an anomaly timestamp to a normal timestamp within one parent.
    base=np.ones(4,bool); corr=np.array([0,0,1,0],bool); nominal=np.array([0,0,1,1],bool)
    p=dict(method="locked_local",parent_gap=0,cooldown_cycles=0)
    x=replay(base,corr,np.ones(4,bool),p)
    assert x["starts"].tolist()==[2] and nominal[x["starts"]].sum()==1
    assert nominal[frozen.episodes(base,np.ones(4,bool),0)[2]].sum()==0
    return dict(prefix_invariance_checks=tests,synthetic_total_not_nominal_counterexample=True)

def load_data(suite,path,j):
    d=frozen.data_for(suite,path,j); folder=path.parent
    scores=np.load(folder/"scores.npy",mmap_mode="r")
    masks={name:np.asarray(scores[:,j["methods"].index(name)]>=d["tau"])
           for name in ("base","local_nn","constrained")}
    assert all(not np.any(mask&~masks["base"]) for mask in masks.values())
    if suite=="SMD":
        b=j["data"]["block_size"]; d["decision_times"]=(np.arange(len(scores))+1)*b-1
        d["source_offset"]=j["data"]["train_blocks"]
        lookup={str(int(r.event_id)):(int(r.start_sample),int(r.end_sample_exclusive)-1)
                for r in d["saved"][d["saved"].method=="base"].itertuples()}
        original_paths=[Path(j["data"]["working_directory"])/"test_label.txt"]
    else:
        a=j["arguments"]; prep=ROOT/"datasets"/f"m{a['mission']}_{a['subset']}_b{a['block']}"
        ends=np.load(prep/"ends.npy",mmap_mode="r")
        d["decision_times"]=np.asarray(ends[j["offset"]:j["end"]])
        d["source_offset"]=j["offset"]
        meta={str(e["id"]):e for e in js(prep/"events.json")}
        lookup={ident:(min(a for a,b in meta[ident]["intervals"]),
                       max(b for a,b in meta[ident]["intervals"])) for ident in d["events"]}
        original_paths=[prep/"events.json",prep/"ends.npy",prep/"usable.npy"]
    for ident,e in d["events"].items():
        e["first_start"],e["final_end"]=lookup[ident]
    original_paths += [path,folder/"scores.npy",folder/"event_results.csv",folder/"reviews.json"]
    return d,masks,original_paths

def request_schedule(d,j,base):
    """Reconstruct request times, including requests whose labels never arrive."""
    n=len(base); eligible=d["eligible"]; suite="ESA" if "arguments" in j else "SMD"
    if suite=="SMD":
        settings=j["settings"]; budget=float(settings["budget"])
        cap=max(1,int(np.ceil(settings["max_window_samples"]/j["data"]["block_size"])))
        period=float(settings["budget_period_samples"]); delay=settings["delay_samples"]
    else:
        a=j["arguments"]; budget=float(a["budget"])
        cap=max(1,round(a["window_hours"]*3600/d["duration"]))
        period=7*86400*1e9; delay=a["delay"]*3600*1e9
    windows=[]; start=None; lows=0; previous=None
    for i in np.flatnonzero(eligible):
        if previous is not None and i!=previous+1: start=None; lows=0
        previous=i
        if start is None:
            if not base[i]: continue
            start=int(i); lows=0
        lows=0 if base[i] else lows+1
        if lows>=2 or i-start+1>=cap:
            windows.append(dict(start=start,end=int(i)+1,closed=int(i),capped=bool(i-start+1>=cap)))
            start=None; lows=0
    requests=[]; tokens=budget; previous=None; times=d["decision_times"]
    for k,e in enumerate(windows):
        t=int(times[e["closed"]])
        if previous is not None: tokens=min(budget,tokens+(t-previous)*budget/period)
        previous=t
        if tokens<1: continue
        tokens-=1
        arrival=int(np.searchsorted(times,t+max(1,delay),"left"))
        effective=max(arrival,e["end"])
        requests.append(dict(e,id=f"review_{k}",arrival=arrival,effective=effective,request_time=t))
    assert len(windows)==j["candidate_windows"]
    assert len(requests)==j["requested_reviews"]
    return requests

def validate_requests(d,j,requests,folder):
    used=[r for r in requests if r["effective"]<len(d["eligible"])]
    saved=js(folder/"reviews.json")
    assert len(used)==len(saved)==j["arrived_reviews"]
    offset=d["source_offset"]
    for rec,old in zip(used,saved):
        assert rec["id"]==old["id"]
        for key in ("start","end","closed"): assert rec[key]+offset==old[key]
        assert rec["effective"]+offset==old["effective_block"]
        assert rec["capped"]==old["capped"]
    return len(used)

def score_ids(mask,events,lower,upper,cohort):
    return {ident for ident in cohort if np.any(mask[events[ident]["activepre"][
        (events[ident]["activepre"]>=lower)&(events[ident]["activepre"]<upper)]])}
def start_ids(starts,events,lower,upper,cohort):
    st=starts[(starts>=lower)&(starts<upper)]
    return {ident for ident in cohort if len(np.intersect1d(st,events[ident]["activepre"],assume_unique=True))}
def interval_counts(x,d,lower,upper,cohort,reference=None):
    e=d["events"]; mask=x["mask"]; starts=x["starts"][(x["starts"]>=lower)&(x["starts"]<upper)]
    sh=score_ids(mask,e,lower,upper,cohort); nh=start_ids(x["starts"],e,lower,upper,cohort)
    opp={ident for ident in cohort if np.any((e[ident]["activepre"]>=lower)&(e[ident]["activepre"]<upper))}
    task={ident for ident in cohort if np.any(x["task"][e[ident]["activepre"][
        (e[ident]["activepre"]>=lower)&(e[ident]["activepre"]<upper)]])}
    out=dict(interval_decisions=upper-lower,all_notification_starts=len(starts),
             nominal_notification_starts=int(d["nominal"][starts].sum()),
             nominal_decision_notification_starts=int(d["nominal_decision"][starts].sum()),
             all_flagged_cycles=int(mask[lower:upper].sum()),
             nominal_flagged_cycles=int((mask[lower:upper]&d["nominal"][lower:upper]).sum()),
             incident_full_cohort=len(cohort),incident_opportunities=len(opp),
             score_active_before_own_hits=len(sh),notification_active_before_own_hits=len(nh),
             policy_task_open_before_own_contacts=len(task),score_hit_ids=packed_ids(sh),
             notification_hit_ids=packed_ids(nh),opportunity_ids=packed_ids(opp),task_contact_ids=packed_ids(task))
    if reference:
        bs,bn=reference
        out.update(new_score_loss=len(bs-sh),new_notification_start_loss=len(bn-nh),
                   new_score_gain=len(sh-bs),new_notification_start_gain=len(nh-bn),
                   new_score_loss_ids=packed_ids(bs-sh),new_notification_loss_ids=packed_ids(bn-nh))
    return out

def select_row(rows,base_score_ids):
    base=next(r for r in rows if r["policy"]=="base_g0_c0")
    if not base_score_ids: return base,"fallback_empty_baseline_score_evidence"
    valid=[r for r in rows if r["prefix_score_gate"] and r["prefix_start_gate"]]
    assert valid
    winner=min(valid,key=lambda r:(r["nominal_notification_starts"],rank(r)))
    return winner,"minimum_prefix_nominal_starts_with_identity_gates"

def analyze(suite,path,j,oldmetrics,eventwriter=None):
    t0=time.perf_counter(); d,masks,paths=load_data(suite,path,j); n=len(d["eligible"]); cut=int(np.floor(.4*n))
    assert 0<cut<n
    # Last prefix timestamp + 1 is the physical observation boundary. Using
    # first suffix timestamp would leak up to stride-1 still unseen samples.
    boundary=int(d["decision_times"][cut-1])+1
    ev=d["events"]; anomalies={ident for ident,e in ev.items() if e["category"]=="anomaly"}
    complete={ident for ident in anomalies if ev[ident]["final_end"]<boundary}
    primary={ident for ident in anomalies if ev[ident]["first_start"]>=boundary}
    straddle={ident for ident in anomalies if ev[ident]["first_start"]<boundary<=ev[ident]["final_end"]}
    assert complete|primary|straddle==anomalies and not(complete&primary or primary&straddle or complete&straddle)
    shared=dict(dataset=suite,run=path.parent.name,unit=d["unit"],backbone=d["backbone"],seed=d["seed"],
                total_decisions=n,prefix_decisions=cut,suffix_decisions=n-cut,physical_split_boundary=boundary)
    source_seals={str(p):frozen.sha(p) for p in paths}
    request=request_schedule(d,j,masks["base"]); arrived=validate_requests(d,j,request,path.parent)
    qprefix=sum(r["closed"]<cut for r in request); qsuffix=len(request)-qprefix
    arrivals_suffix=sum(cut<=r["effective"]<n for r in request)
    carry_reviews=sum(r["closed"]<cut<=r["effective"]<n for r in request)
    history=dict(prefix_review_requests=qprefix,suffix_review_requests=qsuffix,
                 suffix_review_arrivals=arrivals_suffix,prefix_requested_suffix_arrived=carry_reviews)
    parents={g:parent_data(masks["base"],d["eligible"],g) for g in (0,1,3)}
    parent_membership={}
    for g in (0,1,3):
        dense,_=system.parent_state(masks["base"],d["eligible"],g)
        membership=np.zeros(len(parents[g]["initial"]),np.int32)
        for ident in anomalies:
            ep=np.unique(dense[ev[ident]["active"]]); ep=ep[ep>=0]
            membership[ep]+=1
        parent_membership[f"baseline_parent_episodes_gap{g}"]=len(membership)
        parent_membership[f"baseline_parents_spanning_multiple_anomaly_ids_gap{g}"]=int((membership>1).sum())
        parent_membership[f"max_anomaly_ids_contacted_by_one_base_parent_gap{g}"]=int(membership.max()) if len(membership) else 0
    baseref=replay(masks["base"],masks["base"],d["eligible"],
                  dict(method="base",parent_gap=0,cooldown_cycles=0),parents[0])
    prefix_score=score_ids(baseref["mask"],ev,0,cut,complete)
    prefix_start=start_ids(baseref["starts"],ev,0,cut,complete)
    refs={cohort:(score_ids(baseref["mask"],ev,cut,n,ids),
                  start_ids(baseref["starts"],ev,cut,n,ids))
          for cohort,ids in [("primary",primary),("straddling",straddle)]}
    rows=[]; suffix=[]; checks=0; external_checks=0
    for p in candidates():
        name=p["method"]; x=replay(masks["base"],masks[SOURCE[name]],d["eligible"],p,parents[p["parent_gap"]])
        if name.startswith("locked_"):
            ext=system.lock_diagnostics(masks["base"].astype(np.float32),masks[SOURCE[name]].astype(np.float32),d["eligible"],.5,p["parent_gap"])
            assert np.array_equal(x["mask"],(ext.score>=.5)&d["eligible"])
            assert np.array_equal(x["starts"],ext.trigger)
            assert np.array_equal(x["task"],ext.task_open)
            external_checks+=1
        row=dict(shared,**p,policy=policy_id(p),**interval_counts(x,d,0,cut,complete),**history)
        sh=set(json.loads(row["score_hit_ids"])); nh=set(json.loads(row["notification_hit_ids"]))
        row.update(prefix_score_gate=prefix_score<=sh,prefix_start_gate=prefix_start<=nh,
                   prefix_new_score_loss_ids=packed_ids(prefix_score-sh),
                   prefix_new_notification_loss_ids=packed_ids(prefix_start-nh),
                   base_prefix_score_hit_ids=packed_ids(prefix_score),
                   base_prefix_notification_hit_ids=packed_ids(prefix_start),
                   prefix_gate_nonvacuous=bool(prefix_score))
        rows.append(row)
        if p["cooldown_cycles"]==0 and not name.startswith("locked"):
            old=oldmetrics[(oldmetrics.run==path.parent.name)&(oldmetrics.method==name)]
            assert len(old)==1
            g=p["parent_gap"]; r=old.iloc[0]
            assert len(x["starts"])==r[f"all_notifications_gap{g}"]
            assert int(d["nominal"][x["starts"]].sum())==r[f"nominal_notifications_gap{g}"]
            checks+=1
        # Prefix invariance on real streams, including task/contact state.
        pre=replay(masks["base"][:cut],masks[SOURCE[name]][:cut],d["eligible"][:cut],p)
        assert np.array_equal(pre["mask"],x["mask"][:cut])
        assert np.array_equal(pre["starts"],x["starts"][x["starts"]<cut])
        assert np.array_equal(pre["task"],x["task"][:cut])
        b=x["parent"]; carried=((x["task_first_sent"]<cut)&(x["task_parent"]["close"]>cut))
        delay=x["first_sent"]-b["first"]
        sent=x["first_sent"]<n
        delay=delay[sent]
        for group,ids in [("primary",primary),("straddling",straddle)]:
            metric=dict(shared,**p,policy=policy_id(p),cohort=group,
                        **interval_counts(x,d,cut,n,ids,refs[group]),**history)
            metric.update(feedback_required=name!="base",
                incremental_suffix_review_requests=qsuffix if name!="base" else 0,
                historical_selector_prefix_reviews=qprefix,
                carried_policy_tasks=int(carried.sum()),
                task_open_at_last_prefix_decision=bool(x["task"][cut-1]),
                first_parent_trigger_delay_cycles_median=float(np.median(delay)) if len(delay) else None,
                first_parent_trigger_delay_cycles_max=int(delay.max()) if len(delay) else None,
                restored_high_cycles_suffix=int((x["mask"][cut:]&~masks[SOURCE[name]][cut:]).sum()))
            suffix.append(metric)
            if eventwriter:
                for ident in sorted(ids):
                    e=ev[ident]; active=e["activepre"]; ii=active[(active>=cut)&(active<n)]
                    trigger=np.intersect1d(x["starts"],ii,assume_unique=True)
                    baseactive=baseref["mask"][ii]
                    basestarts=np.intersect1d(baseref["starts"],ii,assume_unique=True)
                    eventwriter.writerow(dict(shared,**p,policy=policy_id(p),cohort=group,event_id=ident,
                        first_start=e["first_start"],final_end=e["final_end"],own_cutoff=e["cutoff"],
                        opportunity=bool(len(ii)),opportunity_decisions=len(ii),
                        score_active_before_own_hit=bool(np.any(x["mask"][ii])),
                        notification_start_active_before_own_hit=bool(len(trigger)),
                        parent_task_open_contact_before_own=bool(np.any(x["task"][ii])),
                        task_already_open_at_first_active_decision=bool(x["task"][ii[0]] and ii[0] not in x["starts"]) if len(ii) else False,
                        baseline_score_hit=bool(np.any(baseactive)),baseline_notification_start_hit=bool(len(basestarts)),
                        score_first_decision_index=int(ii[np.flatnonzero(x["mask"][ii])[0]]) if np.any(x["mask"][ii]) else None,
                        notification_first_decision_index=int(trigger[0]) if len(trigger) else None))
    choice,reason=select_row(rows,prefix_score)
    cid=choice["policy"]
    choice=dict(shared,selected_policy=cid,method=choice["method"],parent_gap=choice["parent_gap"],
                cooldown_cycles=choice["cooldown_cycles"],selection_reason=reason,
                prefix_nominal_starts=choice["nominal_notification_starts"],
                prefix_complete_incidents=len(complete),prefix_baseline_score_hits=len(prefix_score),
                prefix_baseline_notification_hits=len(prefix_start),
                prefix_admissible_candidates=sum(r["prefix_score_gate"] and r["prefix_start_gate"] for r in rows),
                prefix_score_gate=choice["prefix_score_gate"],prefix_start_gate=choice["prefix_start_gate"],
                suffix_primary_incidents=len(primary),suffix_straddling_incidents=len(straddle),**history)
    assert choice["prefix_score_gate"] and choice["prefix_start_gate"]
    for row in suffix: row["selected"]=row["policy"]==cid
    assert all(frozen.sha(p)==h for p,h in source_seals.items())
    return rows,suffix,choice,dict(shared,original_unwrapped_fullstream_checks=checks,
        real_prefix_invariance_checks=21,external_system_lock_checks=external_checks,reconstructed_review_requests=len(request),**parent_membership,
        exact_arrived_review_schedule_checks=arrived,runtime_seconds=time.perf_counter()-t0),source_seals

def write_csv(path,rows):
    if not rows: return
    with Path(path).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def aggregate(target):
    d=pd.read_csv(target/"suffix_metrics.csv"); d=d[d.cohort=="primary"]
    selected=d[d.selected].copy(); selected["comparison"]="selected"
    fixed=d[d.policy.isin(["base_g0_c0","local_nn_g0_c0","constrained_g0_c0",
                           "locked_local_g0_c0","locked_constrained_g0_c0","base_g0_c3","base_g0_c6"])].copy()
    fixed["comparison"]=fixed.policy
    a=pd.concat([selected,fixed],ignore_index=True)
    cols=["all_notification_starts","nominal_notification_starts","all_flagged_cycles","nominal_flagged_cycles",
          "incident_full_cohort","incident_opportunities","score_active_before_own_hits",
          "notification_active_before_own_hits","policy_task_open_before_own_contacts",
          "new_score_loss","new_notification_start_loss","new_score_gain","new_notification_start_gain",
          "incremental_suffix_review_requests","carried_policy_tasks","restored_high_cycles_suffix"]
    collapsed=a.groupby(["dataset","unit","backbone","comparison"])[cols].mean().reset_index()
    smd=collapsed[collapsed.dataset=="SMD"].groupby(["dataset","backbone","comparison"])[cols].sum().reset_index()
    smd["unit"]="all28devices"
    pooled=pd.concat([smd,collapsed[collapsed.dataset=="ESA"]],ignore_index=True)
    pooled["entity_clusters"]=pooled.dataset.map({"SMD":28,"ESA":1})
    # ESA mission results remain separate; do not present two missions as a
    # population bootstrap or pool them as independent fitted replicates.
    collapsed.to_csv(target/"suffix_device_seedmeans.csv",index=False)
    pooled.to_csv(target/"suffix_pooled_seedmeans.csv",index=False)
    costs=[]
    for (dataset,unit,backbone),g in pooled.groupby(["dataset","unit","backbone"]):
        base=g[g.comparison=="base_g0_c0"].iloc[0]
        for _,r in g.iterrows():
            for endpoint in ["all_notification_starts","nominal_notification_starts"]:
                diff=float(r[endpoint]-base[endpoint]); review=float(r.incremental_suffix_review_requests)
                removed=float(base.nominal_flagged_cycles-r.nominal_flagged_cycles)
                for minutes in [5,15,30]:
                    for review_minutes in [5,15,30]:
                        costs.append(dict(dataset=dataset,unit=unit,backbone=backbone,comparison=r.comparison,
                            notification_endpoint=endpoint,additional_notifications_seedmean_total=diff,
                            minutes_per_notification_assumed=minutes,
                            notification_hours_scenario=diff*minutes/60,
                            additional_review_requests_seedmean_total=review,
                            minutes_per_review_assumed=review_minutes,
                            review_hours_scenario=review*review_minutes/60,
                            combined_notification_review_hours_scenario=(diff*minutes+review*review_minutes)/60,
                            newly_lost_score_hits_seedmean_total=float(r.new_score_loss),
                            newly_lost_start_hits_seedmean_total=float(r.new_notification_start_loss),
                            removed_nominal_flagged_cycles_seedmean_total=removed,
                            added_starts_per_removed_nominal_cycle=diff/removed if removed>0 else None,
                            time_costs_observed=False))
    write_csv(target/"suffix_cost_scenarios.csv",costs)
    example=[dict(unit="machine-3-11",backbone="dcvae",seed=1,method="local_nn",gap=0,
                  all_base_starts=105,all_corrected_starts=405,nominal_base_starts=104,
                  nominal_corrected_starts=404,additional_starts=300,
                  minutes_per_additional_notification_assumed=m,hours_scenario=300*m/60,
                  time_costs_observed=False) for m in [5,15,30]]
    write_csv(target/"illustrative_staff_hour_scenarios.csv",example)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["pilot","full"],default="pilot")
    args=ap.parse_args(); target=OUT/args.mode; target.mkdir(parents=True,exist_ok=True)
    preflight=self_checks(); entries=frozen.receipts()
    if args.mode=="pilot": entries=[next(x for x in entries if x[0]=="ESA"),next(x for x in entries if x[0]=="SMD")]
    old=pd.read_csv(ROOT/"results/revision_20261001/decision_audit/full/run_metrics.csv")
    example=old[(old.unit=="machine-3-11")&(old.backbone=="dcvae")&(old.seed==1)&old.method.isin(["base","local_nn"])].set_index("method")
    assert int(example.loc["base","all_notifications_gap0"])==105 and int(example.loc["local_nn","all_notifications_gap0"])==405
    assert int(example.loc["base","nominal_notifications_gap0"])==104 and int(example.loc["local_nn","nominal_notifications_gap0"])==404
    t0=time.perf_counter(); prefix=[]; suffix=[]; choices=[]; audits=[]; seals={}
    fields=FIELDS+["total_decisions","prefix_decisions","suffix_decisions","physical_split_boundary",
        "method","parent_gap","cooldown_cycles","policy","cohort","event_id","first_start","final_end","own_cutoff",
        "opportunity","opportunity_decisions","score_active_before_own_hit","notification_start_active_before_own_hit",
        "parent_task_open_contact_before_own","task_already_open_at_first_active_decision","baseline_score_hit","baseline_notification_start_hit",
        "score_first_decision_index","notification_first_decision_index"]
    with (target/"suffix_events.csv").open("w",newline="",encoding="utf-8") as f:
        eventwriter=csv.DictWriter(f,fieldnames=fields);eventwriter.writeheader()
        for k,(suite,path,j) in enumerate(entries):
            p,s,c,a,source_seals=analyze(suite,path,j,old,eventwriter)
            prefix.extend(p); suffix.extend(s); choices.append(c);audits.append(a)
            seals.update(source_seals)
            if k%20==0 or k+1==len(entries):
                print("WORKFLOW",k+1,len(entries),suite,path.parent.name,"selected",c["selected_policy"],
                      "elapsed",round(time.perf_counter()-t0,2),flush=True)
    write_csv(target/"prefix_candidate_metrics.csv",prefix)
    write_csv(target/"suffix_metrics.csv",suffix);write_csv(target/"selector_choices.csv",choices)
    write_csv(target/"fit_audit.csv",audits);aggregate(target)
    # Digests were captured before every fit's numerical policy analysis.
    changed={p:{"before":h,"after":frozen.sha(p)} for p,h in seals.items() if frozen.sha(p)!=h}
    assert not changed
    receipt=dict(completed=True,mode=args.mode,fits=len(entries),candidates_per_fit=21,
        prefix_candidate_rows=len(prefix),suffix_candidate_cohort_rows=len(suffix),
        selected_rows=len(choices),stage="post-result temporal selection diagnostic; previously inspected original data",
        protocol_sha256=frozen.sha(OUT/"selector_protocol.json"),
        script_sha256=frozen.sha(Path(__file__)),created_utc=datetime.now(timezone.utc).isoformat(),
        synthetic_checks=preflight,all_real_prefix_checks_passed=True,
        all_original_unwrapped_counts_exact=True,all_arrived_review_schedules_exact=True,
        all_prefix_identity_gates_or_explicit_fallback_satisfied=True,
        suffix_policy_selection_performed=False,suffix_state_reset=False,
        source_hashes=seals,source_changes=changed,peak_working_set_bytes=memory_peak(),
        runtime_seconds=time.perf_counter()-t0)
    jdump(target/"receipt.json",receipt)
    print("COMPLETED",args.mode,len(entries),round(receipt["runtime_seconds"],2),flush=True)
if __name__=="__main__": main()
