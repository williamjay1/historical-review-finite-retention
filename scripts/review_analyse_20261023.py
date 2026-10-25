from pathlib import Path
import json,gzip
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'results/revision_review_20261023'

def main():
    costs=pd.concat([pd.read_csv(O/'static_costs.csv'),pd.read_csv(O/'fine_static_costs.csv')],ignore_index=True)
    metrics=pd.concat([pd.read_csv(O/'static_metrics.csv'),pd.read_csv(O/'fine_static_metrics.csv')],ignore_index=True)
    costs.to_csv(O/'all_static_costs.csv',index=False);metrics.to_csv(O/'all_static_metrics.csv',index=False)
    cols=['queries','positive_queries','negative_queries','certified_yes','certified_no','unknown','joint_first','first_position','first_atom','complete_report','complete_positive','tolerance','any_numeric','false_certificates','unusable_queries','empty_queries']
    agg=metrics.groupby(['dataset','cadence','backbone','budget','method','family'],as_index=False)[cols].sum()
    agg.to_csv(O/'static_task_summary.csv',index=False)
    full=costs[costs.method=='full'].copy();full=full.drop_duplicates(['dataset','cadence','unit','backbone'])
    feas=[]
    for (ds,ca),df in full.groupby(['dataset','cadence']):
        feas.append(dict(dataset=ds,cadence=ca,histories=len(df),fit64=int((df.full_bytes<=65536).sum()),fit256=int((df.full_bytes<=262144).sum()),fit1024=int((df.full_bytes<=1048576).sum()),min_bytes=int(df.full_bytes.min()),median_bytes=float(df.full_bytes.median()),max_bytes=int(df.full_bytes.max())))
    pd.DataFrame(feas).to_csv(O/'complete_feasibility.csv',index=False)
    # Per-device service rates retain devices as descriptive groups, not queries
    # as inferential observations. Zero-positive devices remain explicitly NA.
    aa=metrics[(metrics.family=='full_annotated')&(metrics.dataset=='SMD')].copy()
    aa['joint_rate']=aa.joint_first/aa.positive_queries.replace(0,np.nan)
    aa['report_rate']=aa.complete_positive/aa.positive_queries.replace(0,np.nan)
    aa.to_csv(O/'device_task_rates.csv',index=False)
    tol=aa.groupby(['cadence','budget','method'],as_index=False)[['positive_queries','joint_first','first_atom','tolerance']].sum()
    tol.to_csv(O/'tolerance_summary.csv',index=False)
    on=O/'online_summary_b1024.csv'
    data=dict(static_archives=len(costs),static_aggregate_rows=len(metrics),complete_feasibility=feas,false_certificates=int(metrics.false_certificates.sum()))
    if on.exists() and len(pd.read_csv(on))==32:
        online=pd.read_csv(on);groups=[];frames=[]
        for path in (O/'online_details').glob('*_b1024.csv.gz'):frames.append(pd.read_csv(path))
        dd=pd.concat(frames,ignore_index=True)
        dd['age_group']=pd.cut(dd.age_fraction,[-.001,.01,.25,.5,.75,1.01],labels=['0–1%','1–25%','25–50%','50–75%','75–100%'])
        for keys,df in dd.groupby(['dataset','unit','backbone','cadence','budget','method','age_group'],observed=True):
            pos=df[df.positive];groups.append(dict(zip(['dataset','unit','backbone','cadence','budget','method','age_group'],keys),queries=len(df),positive_queries=len(pos),joint_first=int(pos.first_numeric_joint.sum()),complete_positive=int(pos.complete_report.sum()),unknown=int((df.answer=='unknown').sum()),boundary_queries=int(df.cross_boundary.sum()),rejected_queries=int(df.rejected_hole.sum())))
        pd.DataFrame(groups).to_csv(O/'online_age_summary.csv',index=False)
        strata=[]
        for kind in ['cross_boundary','rejected_hole']:
            for keys,df in dd.groupby(['dataset','unit','backbone','cadence','budget','method',kind]):
                pos=df[df.positive];strata.append(dict(zip(['dataset','unit','backbone','cadence','budget','method','stratum_value'],keys),stratum=kind,queries=len(df),positive_queries=len(pos),joint_first=int(pos.first_numeric_joint.sum()),complete_positive=int(pos.complete_report.sum()),unknown=int((df.answer=='unknown').sum())))
        pd.DataFrame(strata).to_csv(O/'online_boundary_summary.csv',index=False)
        dd.groupby(['dataset','cadence','budget','method','length'],as_index=False).agg(queries=('positive','size'),positive=('positive','sum'),joint=('first_numeric_joint','sum'),unknown=('answer',lambda x:(x=='unknown').sum())).to_csv(O/'online_length_summary.csv',index=False)
        data.update(online_conditions=len(online),online_queries=int(online.queries.sum()),online_false_certificates=int(online.false_certificates.sum()))
    (O/'RESULT_NUMBERS.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps(data,indent=2))
if __name__=='__main__':main()
