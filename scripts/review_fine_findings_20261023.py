"""Descriptive finite-archive totals and one real fine SMD task case."""
import json
from pathlib import Path
import pandas as pd
import numpy as np
import review_fine_stream_20261023 as fine
import review_archive_core_20261023 as core

OUT=fine.OUT

def scalar(v):
    return v.item() if isinstance(v,np.generic) else v

def atom(z):
    return {k:scalar(z[k]) for k in z.dtype.names}

def main():
    done=fine.js(OUT/'fine_static_completion.json')
    assert done['passed'] and done['fits_completed']==56 and not done['in_progress']
    pilot=OUT/'fine_static_pilot_completion.json'
    if pilot.exists():
        p=fine.js(pilot)
        p.update(superseded=True,
                 superseded_reason='Exploratory pilot preceded final common-core parent-selection and equal-header fixes; all56 final conditions rerun from scratch.',
                 definitive_completion='fine_static_completion.json')
        pilot.write_text(json.dumps(p,indent=2),encoding='utf-8')
    m=pd.read_csv(OUT/'fine_static_metrics.csv');c=pd.read_csv(OUT/'fine_static_costs.csv')
    q=m[m.family=='full_annotated'];rows=[]
    for (kind,B,method),g in q.groupby(['backbone','budget','method']):
        row=dict(backbone=kind,budget=int(B),method=method,fits=len(g))
        for k in ['queries','positive_queries','negative_queries','certified_yes','certified_no','unknown','joint_first','first_position','first_atom','complete_report','complete_positive','tolerance','any_numeric','false_certificates']:
            row[k]=int(g[k].sum())
        row['actual_bytes']=int(g['bytes'].sum());row['slack_bytes']=int(g['slack'].sum())
        row['retained_atoms']=int(g['retained_atoms'].sum());row['unsaved_atoms']=int(g['unsaved_atoms'].sum())
        row['complete_fit_histories']=int(g.feasible.sum()) if method=='full' else None
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUT/'fine_static_summary.csv',index=False)
    hard=q[(q.unit=='machine-3-4')&(q.backbone=='ridge')]
    # A real currently scored event and annotated dimension, not the older
    # nominal-only notification vignette. Select deterministically from current
    # archived files: a first numeric record retained by coverage but lost by
    # parent-change at64KiB, when such a difference exists.
    s=fine.to_driver_stream('machine-3-4','ridge');B=65536
    folder=OUT/'static/SMD_machine-3-4_ridge_fine'
    archives={k:core.decode_archive((folder/f'{k}_{B}.arc').read_bytes()) for k in ['bitmap_change','coverage_summary','coverage_fill','adaptive_coverage_fill']}
    selected=None
    for query in s['queries']:
        if query['family']!='full_annotated' or not query['positive']:continue
        rr={k:core.query(a,query['idx'],query['channel']) for k,a in archives.items()}
        if rr['coverage_summary']['first_numeric_joint'] and not rr['bitmap_change']['first_numeric_joint']:
            selected=(query,rr);break
    if selected is None:
        query=next(q for q in s['queries'] if q['family']=='full_annotated' and q['positive'])
        selected=(query,{k:core.query(a,query['idx'],query['channel']) for k,a in archives.items()})
    query,responses=selected;ch=query['channel'];ix=query['idx'];reference=s['a'][(s['a']['ch']==ch)&np.isin(s['a']['t'],ix)]
    ev=s['source']['events'][query['incident_id']]
    case=dict(dataset='SMD',unit='machine-3-4',backbone='ridge',cadence='fine',budget=B,
              incident_id=query['incident_id'],channel_0based=int(ch),variable_1based=int(ch+1),
              event_start_sample=ev['first_start'],event_end_exclusive_sample=ev['final_end']+1,
              query_start_cycle=int(ix[0]),query_stop_cycle=int(ix[-1])+1,
              reference_high_records=len(reference),reference_first_atom=atom(reference[0]),
              reference_first_source_sample=int(s['source']['decision_times'][reference[0]['t']]),
              task='replay high-support and reconstruct exact first high record; list missing high-report details',responses={})
    for method,r in responses.items():
        a=archives[method];numbers=r.pop('numeric')
        case['responses'][method]=dict(**r,bytes=a.size,retained_query_high_records=len(numbers),
             first_retained_record=atom(numbers[0]) if len(numbers) else None,
             first_16_retained_records=[atom(z) for z in numbers[:16]])
    (OUT/'fine_task_case.json').write_text(json.dumps(case,indent=2),encoding='utf-8')
    report={'fits':56,'evaluated_queries_full_method_across_two_budgets':int(m[m.method=='full'].queries.sum()),'false_certificates':int(m.false_certificates.sum()),
            'annotated_targets_each_backbone':2254,'binary_events':327,'exact_annotation_events':322,
            'totals':rows,'hard_server_rows':hard.to_dict('records'),
            'source_files_unchanged':done['source_files_unchanged'],
            'script_sha256':fine.sha(__file__)}
    (OUT/'fine_static_summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'false_certificates':report['false_certificates'],'summary_rows':len(rows),
                      'case_incident':case['incident_id'],'case_channel':case['variable_1based'],
                      'source_files_unchanged':done['source_files_unchanged']},indent=2))

if __name__=='__main__':main()
