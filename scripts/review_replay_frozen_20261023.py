"""Rerun executed archive policies from portable frozen service inputs.

Only module-level output paths/budgets/chunk length are redirected in memory;
the frozen core, original drivers and canonical result files are not edited.
Every invocation requires a fresh output directory.
"""
from pathlib import Path
import argparse,ast,csv,datetime,gzip,hashlib,json,math,os,time
import numpy as np
from review_frozen_inputs_20261023 import load_stream,sha

ROOT=Path(__file__).resolve().parents[1]
CANONICAL=ROOT/'results/revision_review_20261023'
PILOT={('ESA','1','ridge','coarse'),('SMD','machine-3-4','ridge','coarse'),
       ('SMD','machine-3-4','ridge','fine')}
ONLINE=PILOT|{('ESA','1','pca','coarse')}
IDENTITY=('dataset','unit','backbone','cadence')

def identity(row):return tuple(str(row[k]) for k in IDENTITY)
def plain(x):
    if isinstance(x,np.generic):return x.item()
    if isinstance(x,Path):return str(x)
    raise TypeError(type(x).__name__)

def read_csv(path):
    op=gzip.open if Path(path).suffix=='.gz' else open
    with op(path,'rt',encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

def value_equal(x,y):
    if str(x)==str(y):return True
    try:
        a=float(x);b=float(y)
        return (math.isnan(a) and math.isnan(b)) or math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)
    except (TypeError,ValueError):return False

def compare_rows(actual,reference,keys,exclude=()):
    index={tuple(str(r[k]) for k in keys):r for r in reference};mismatches=[]
    for row in actual:
        key=tuple(str(row[k]) for k in keys);expected=index.get(key)
        if expected is None:mismatches.append(dict(key=key,reason='missing canonical row'));continue
        for field,value in row.items():
            if field in exclude:continue
            if field not in expected or not value_equal(value,expected[field]):
                mismatches.append(dict(key=key,field=field,actual=value,canonical=expected.get(field)))
    return dict(rows=len(actual),mismatches=mismatches,passed=not mismatches)

def local_import_closure(script_dir,seeds):
    """Conservative AST closure, including imports inside optional functions."""
    script_dir=Path(script_dir);pending=list(seeds);seen={};external=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        path=script_dir/(name+'.py')
        if not path.exists():external.add(name);continue
        imports=set();tree=ast.parse(path.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.update(a.name.split('.')[0] for a in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module:imports.add(node.module.split('.')[0])
        local=sorted(n for n in imports if (script_dir/(n+'.py')).is_file())
        external.update(imports-set(local))
        seen[name]=dict(file=path.name,sha256=sha(path),local_imports=local)
        pending.extend(local)
    return dict(scope='Conservative recursive AST closure, including optional-function imports',
                local_modules=[seen[k] for k in sorted(seen)],nonlocal_import_roots=sorted(external))

def compare_results(output,reference,mode,costs,metrics,summaries,block):
    if not reference.is_dir():return dict(status='not_run',reason='Canonical reference directory absent')
    checks={};key=list(IDENTITY)+['budget','method']
    if mode=='static':
        paths=[reference/'all_static_costs.csv',reference/'all_static_metrics.csv']
        if not all(p.is_file() for p in paths):return dict(status='not_run',reason='Canonical static CSVs absent')
        checks['costs']=compare_rows(costs,read_csv(paths[0]),key,exclude=['build_seconds'])
        checks['metrics']=compare_rows(metrics,read_csv(paths[1]),key+['family'],exclude=['build_seconds'])
        subdirs=['static','static_details']
    else:
        path=reference/f'online_summary_b{block}.csv'
        if not path.is_file() and block==256:path=reference/'online_pilot_b256.csv'
        if not path.is_file():return dict(status='not_run',reason='Canonical chunk-size summary absent')
        checks['summary']=compare_rows(summaries,read_csv(path),key+['block'],exclude=['close_p95_ms','query_p95_ms'])
        subdirs=['online_snapshots','online_details','online_flush']
    file_checks=[]
    for subdir in subdirs:
        for actual in sorted((output/subdir).rglob('*')):
            if not actual.is_file():continue
            canonical=reference/actual.relative_to(output)
            row=dict(file=str(actual.relative_to(output)))
            if not canonical.is_file():row.update(passed=False,reason='Canonical counterpart missing')
            elif actual.suffix=='.arc':row.update(passed=sha(actual)==sha(canonical),check='byte-exact archive')
            else:
                aa=read_csv(actual);bb=read_csv(canonical)
                excluded={'query_ms','encode_ms','write_ms'}
                # Static detail files combine both canonical budgets; a replay
                # may deliberately select only one. Compare the selected
                # condition groups, never unrelated canonical conditions.
                group_fields=[k for k in list(IDENTITY)+['budget','method','block']
                              if aa and bb and k in aa[0] and k in bb[0]]
                if group_fields:
                    groups={tuple(str(r[k]) for k in group_fields) for r in aa}
                    bb=[r for r in bb if tuple(str(r[k]) for k in group_fields) in groups]
                failed=[]
                if len(aa)!=len(bb):failed.append('row count differs')
                else:
                    for i,(a,b) in enumerate(zip(aa,bb)):
                        for k,v in a.items():
                            if k not in excluded and (k not in b or not value_equal(v,b[k])):
                                failed.append(dict(row=i,field=k,actual=v,canonical=b.get(k)))
                row.update(passed=not failed,check='non-timing CSV fields',rows=len(aa),
                           selected_group_fields=group_fields,mismatches=failed[:20])
            file_checks.append(row)
    checks['files']=file_checks
    passed=all(v['passed'] for k,v in checks.items() if k!='files') and all(r['passed'] for r in file_checks)
    return dict(status='pass' if passed else 'fail',checks=checks,timings_compared=False)

def run(args):
    inputs=args.inputs.resolve();manifest=json.loads((inputs/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['completed'] and manifest['all_reopened_and_exact']
    output=args.output.resolve()
    if output.exists():raise FileExistsError(f'Use a fresh output directory: {output}')
    if output.is_relative_to(inputs):raise ValueError('Replay output must be separate from frozen inputs')
    output.mkdir(parents=True,exist_ok=False)
    import review_experiments_20261023 as driver
    import review_archive_core_20261023 as core
    import review_online_20261023 as online
    driver.OUT=output;driver.BUDGETS=[int(k)*1024 for k in args.budget_kib]
    online.OUT=output;online.BLOCK=args.block
    core_before=sha(Path(core.__file__))
    assert core_before==manifest['core_sha256'],'Frozen core differs from input provenance'
    seeds=['review_replay_frozen_20261023','review_frozen_inputs_20261023',
           'review_experiments_20261023','review_archive_core_20261023','review_online_20261023']
    closure=local_import_closure(ROOT/'scripts',seeds)
    (output/'local_import_closure.json').write_text(json.dumps(closure,indent=2),encoding='utf-8')
    selected=[]
    for row in manifest['files']:
        ident=identity(row)
        if args.mode=='online' and ident not in ONLINE:continue
        if args.pilot and ident not in PILOT:continue
        if args.unit and row['unit'] not in args.unit:continue
        if args.cadence and row['cadence'] not in args.cadence:continue
        if args.backbone and row['backbone'] not in args.backbone:continue
        selected.append(row)
    if not selected:raise ValueError('No matching frozen streams')
    started=time.perf_counter();costs=[];metrics=[];summaries=[]
    protocol=dict(mode=args.mode,inputs=str(inputs),output=str(output),code_root=str(ROOT),
                  script_directory=str(Path(__file__).resolve().parent),
                  selected_streams=[identity(r) for r in selected],
                  budgets=driver.BUDGETS,block=args.block,pilot=args.pilot,no_training=True,
                  record_scope='Frozen high-score service records; selected window-last observations; no original raw-loader reads')
    (output/'replay_protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    for row in selected:
        path=inputs/row['file'];assert sha(path)==row['sha256']
        s=load_stream(path)
        if args.mode=='static':
            cc,mm=driver.static_one(s,core);costs.extend(cc);metrics.extend(mm)
            driver.write_csv(output/'static_costs.csv',costs);driver.write_csv(output/'static_metrics.csv',metrics)
        else:
            for budget in driver.BUDGETS:
                for method in online.METHODS:
                    rr=online.run_one(s,budget,method);summaries.append(rr)
                    driver.write_csv(output/f'online_summary_b{args.block}.csv',summaries)
        print(json.dumps(dict(stream=identity(s),elapsed_seconds=round(time.perf_counter()-started,2))),flush=True)
    comparison=compare_results(output,args.reference.resolve(),args.mode,costs,metrics,summaries,args.block)
    receipt=dict(protocol,completed=True,streams=len(selected),cost_rows=len(costs),metric_rows=len(metrics),
        online_conditions=len(summaries),elapsed_seconds=time.perf_counter()-started,comparison=comparison,
        frozen_core_unchanged=core_before==sha(Path(core.__file__)),core_sha256=core_before,
        wrapper_sha256=sha(Path(__file__)),input_manifest_sha256=sha(inputs/'manifest.json'),
        closure_modules=len(closure['local_modules']),scope='Only the explicitly selected streams/conditions were rerun')
    (output/'replay_completion.json').write_text(json.dumps(receipt,indent=2,default=plain),encoding='utf-8')
    assert receipt['frozen_core_unchanged']
    assert comparison['status']!='fail',f'Canonical mismatch; see {output}/replay_completion.json'
    print(json.dumps({k:v for k,v in receipt.items() if k!='comparison'},indent=2,default=plain),flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['static','online'],required=True)
    parser.add_argument('--inputs',type=Path,default=CANONICAL/'frozen_inputs')
    parser.add_argument('--output',type=Path,required=True,help='New directory; an existing path is refused')
    parser.add_argument('--reference',type=Path,default=CANONICAL,help='Read-only canonical result directory for comparison')
    parser.add_argument('--pilot',action='store_true',help='ESA1 ridge + hard SMD ridge at both cadences')
    parser.add_argument('--block',type=int,default=1024)
    parser.add_argument('--budget-kib',type=int,nargs='+',default=[64,256],choices=[64,256])
    parser.add_argument('--unit',nargs='+');parser.add_argument('--cadence',nargs='+',choices=['coarse','fine'])
    parser.add_argument('--backbone',nargs='+',choices=['pca','ridge'])
    args=parser.parse_args()
    if args.block<1:parser.error('--block must be positive')
    run(args)

if __name__=='__main__':main()
