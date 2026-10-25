"""Common finite archive comparison on 56 existing fine-cadence SMD streams."""
from pathlib import Path
import argparse, json, time
import review_fine_stream_20261023 as fine
import review_experiments_20261023 as driver
import review_archive_core_20261023 as core

ROOT=fine.ROOT;OUT=fine.OUT

def run(pilot=False):
    begin=time.perf_counter();OUT.mkdir(parents=True,exist_ok=True)
    identities=[('machine-3-4','ridge')] if pilot else fine.available()
    receipts=fine.smd_receipts();costs=[];metrics=[];stages=[];completed=[]
    tag='fine_static_pilot' if pilot else 'fine_static'
    sources={p.name:fine.sha(p) for p in [Path(__file__),Path(fine.__file__),Path(driver.__file__),Path(core.__file__)]}
    for entity,kind in identities:
        start=time.perf_counter()
        s=fine.to_driver_stream(entity,kind,receipts=receipts)
        cc,mm=driver.static_one(s,core)
        costs.extend(cc);metrics.extend(mm)
        stages.extend([dict(driver.key(s),**r) for r in s['stages']])
        completed.append(dict(unit=entity,backbone=kind,seconds=time.perf_counter()-start,
                              atoms=len(s['a']),queries=len(s['queries'])))
        driver.write_csv(OUT/f'{tag}_costs.csv',costs)
        driver.write_csv(OUT/f'{tag}_metrics.csv',metrics)
        driver.write_csv(OUT/f'{tag}_stages.csv',stages)
        state={'passed':False,'in_progress':True,'fits_completed':len(completed),
           'fits_planned':len(identities),'source_sha256':sources,'completed':completed,
           'elapsed_seconds':time.perf_counter()-begin,'no_new_training':True,
           'review_tape':'same original coarse review provenance at both cadences',
           'method':driver.METHODS,'budgets':driver.BUDGETS}
        (OUT/f'{tag}_completion.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
        print('FINE_STATIC_DONE',entity,kind,len(s['a']),len(s['queries']),round(time.perf_counter()-start,2),flush=True)
    source_after={p.name:fine.sha(p) for p in [Path(__file__),Path(fine.__file__),Path(driver.__file__),Path(core.__file__)]}
    state.update(passed=True,in_progress=False,cost_rows=len(costs),metric_rows=len(metrics),
                 source_files_unchanged=sources==source_after,source_after_sha256=source_after,
                 elapsed_seconds=time.perf_counter()-begin)
    (OUT/f'{tag}_completion.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    print('FINE_STATIC_COMPLETE',len(completed),len(costs),len(metrics),round(time.perf_counter()-begin,2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pilot',action='store_true');a=p.parse_args()
    run(a.pilot)
