from pathlib import Path
import json, sys, time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import evidence_representation_audit as old
import review_archive_core_20261023 as core
rows=[]
for suite,p,j in old.f.receipts():
    unit=str(j['arguments']['mission']) if suite=='ESA' else j['entity']
    kind=j['arguments']['backbone'] if suite=='ESA' else j['backbone']
    seed=j['arguments']['seed'] if suite=='ESA' else j['seed']
    if seed!=0 or kind!='ridge' or (suite,unit) not in [('SMD','machine-3-4'),('ESA','1')]:continue
    d,a,h,hb,head,sel,pp,pol,paths=old.load(suite,p,j)
    _,expected=old.summaries(a,pp,d['tau'])
    actual=core._changes(a,d['tau'],256,0,h,len(h))
    assert np.array_equal(expected,actual)
    methods=['full','bitmap_change','bitmap_change_fill','coverage_summary','coverage_fill','adaptive_full_fill']
    frames=[core.frame_bytes(head,m) for m in methods]
    assert len(set(frames))==1
    rows.append(dict(dataset=suite,unit=unit,backbone=kind,old_change_atoms=len(expected),
                     current_change_atoms=len(actual),same_record_ids=True,
                     method_header_bytes=frames[0],all_six_method_headers_equal=True))
out=ROOT/'results/revision_review_20261023/core_real_parent_equivalence.json'
out.write_text(json.dumps(rows,indent=2))
print(json.dumps(rows),flush=True)
