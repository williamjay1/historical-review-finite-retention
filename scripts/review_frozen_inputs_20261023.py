"""Portable, exact frozen inputs for the archive-service revision.

Loading requires only NumPy and the Python standard library. Exporting uses the
existing source adapters, without fitting, editing raw data, or downloading.
The package contains selected high-score records, not full telemetry/windows.
"""
from pathlib import Path
import argparse, hashlib, json, platform, shutil, time
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/revision_review_20261023/frozen_inputs'
SCHEMA='archive-review-frozen-input-v1'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def plain(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,Path):return str(value)
    if isinstance(value,dict):return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [plain(v) for v in value]
    return value

def canonical(value):
    return json.dumps(plain(value),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def text_array(value):return np.frombuffer(canonical(value),dtype=np.uint8).copy()
def read_json(array):return json.loads(array.tobytes().decode('utf-8'))

def encode_queries(queries,high):
    kinds=[];starts=[];steps=[];counts=[];offsets=[0];explicit=[];metadata=[]
    for q in queries:
        idx=np.asarray(q['idx'],dtype=np.int64)
        assert idx.ndim==1
        is_arithmetic=len(idx)<=2 or np.all(np.diff(idx)==idx[1]-idx[0])
        kinds.append(0 if is_arithmetic else 1)
        starts.append(int(idx[0]) if len(idx) else 0)
        steps.append(int(idx[1]-idx[0]) if len(idx)>1 else 1)
        counts.append(len(idx))
        if not is_arithmetic:explicit.extend(idx.tolist())
        offsets.append(len(explicit))
        md={k:plain(v) for k,v in q.items() if k not in ('idx','hits')}
        md['_frozen_hits_from_support']='hits' in q
        if 'hits' in q:assert np.array_equal(np.asarray(q['hits']),idx[high[idx,int(q['channel'])]])
        metadata.append(md)
    return dict(query_kind=np.asarray(kinds,np.uint8),query_start=np.asarray(starts,'<i8'),
                query_step=np.asarray(steps,'<i8'),query_count=np.asarray(counts,'<i8'),
                query_offsets=np.asarray(offsets,'<i8'),query_explicit=np.asarray(explicit,'<i8'),
                query_metadata_utf8=text_array(metadata))

def load_stream(path):
    """Return a driver-compatible frozen stream, without original data paths.

    Exact query indices, support, original high atoms, header and evaluation
    stages are recovered. Annotation metadata is for offline evaluation only.
    No object arrays or pickle deserialization are used.
    """
    path=Path(path)
    with np.load(path,allow_pickle=False) as data:
        meta=read_json(data['identity_utf8']);assert meta.pop('schema')==SCHEMA
        shape=tuple(int(x) for x in data['high_shape'])
        h=np.unpackbits(data['high_bits'],bitorder='little',count=int(np.prod(shape))).reshape(shape).astype(bool)
        eligible=np.unpackbits(data['eligible_bits'],bitorder='little',count=shape[0]).astype(bool)
        atoms=data['atoms'].copy();header=read_json(data['header_utf8']);stages=read_json(data['stages_utf8'])
        query_meta=read_json(data['query_metadata_utf8']);queries=[]
        for i,md in enumerate(query_meta):
            count=int(data['query_count'][i])
            if data['query_kind'][i]==0:
                idx=int(data['query_start'][i])+np.arange(count,dtype=np.int64)*int(data['query_step'][i])
            else:
                lo,hi=data['query_offsets'][i:i+2]
                idx=data['query_explicit'][int(lo):int(hi)].copy()
            assert len(idx)==count
            hits_from_support=md.pop('_frozen_hits_from_support')
            md['idx']=idx
            if hits_from_support:md['hits']=idx[h[idx,int(md['channel'])]]
            queries.append(md)
    return dict(meta,a=atoms,h=h,eligible=eligible,header=header,queries=queries,stages=stages,
                source={'frozen_service_inputs':True,'file':path.name})

def assert_roundtrip(original,reopened):
    for key in ('dataset','unit','backbone','cadence'):assert str(original[key])==str(reopened[key])
    assert original['a'].dtype==reopened['a'].dtype
    assert original['a'].shape==reopened['a'].shape
    assert original['a'].tobytes()==reopened['a'].tobytes()
    assert np.array_equal(original['h'],reopened['h'])
    assert np.array_equal(original['eligible'],reopened['eligible'])
    assert canonical(original['header'])==canonical(reopened['header'])
    assert canonical(original['stages'])==canonical(reopened['stages'])
    assert len(original['queries'])==len(reopened['queries'])
    for q,r in zip(original['queries'],reopened['queries']):
        assert set(q)==set(r)
        for key in q:
            if isinstance(q[key],np.ndarray):assert np.array_equal(q[key],r[key]),key
            else:assert canonical(q[key])==canonical(r[key]),key

def save_stream(s,path):
    h=np.asarray(s['h'],dtype=bool);eligible=np.asarray(s['eligible'],dtype=bool)
    assert h.ndim==2 and eligible.shape==(h.shape[0],)
    identity={k:str(s[k]) for k in ('dataset','unit','backbone','cadence')}
    np.savez_compressed(path,identity_utf8=text_array(dict(identity,schema=SCHEMA)),
        atoms=s['a'],high_shape=np.asarray(h.shape,'<i8'),high_bits=np.packbits(h.reshape(-1),bitorder='little'),
        eligible_bits=np.packbits(eligible,bitorder='little'),header_utf8=text_array(s['header']),
        stages_utf8=text_array(s['stages']),**encode_queries(s['queries'],h))
    reopened=load_stream(path);assert_roundtrip(s,reopened)
    return dict(identity,file=Path(path).name,sha256=sha(path),bytes=Path(path).stat().st_size,
        atoms=len(s['a']),atom_dtype=plain(s['a'].dtype.descr),atom_payload_bytes=s['a'].nbytes,
        atom_payload_sha256=hashlib.sha256(s['a'].tobytes()).hexdigest(),cycles=h.shape[0],channels=h.shape[1],
        high_count=int(h.sum()),high_packed_bytes=(h.size+7)//8,eligible_packed_bytes=(len(eligible)+7)//8,
        queries=len(s['queries']),stages=len(s['stages']),header_sha256=hashlib.sha256(canonical(s['header'])).hexdigest(),
        roundtrip_exact=True)

README='''# Frozen archive-service inputs

This portable package contains 116 executed source histories: 60 coarse histories
(56 SMD device/backbone combinations and four ESA mission/backbone combinations)
plus the 56 paired fine-cadence SMD histories. It is sufficient to rerun the
declared static archive-service tasks without accessing original local raw-data
paths. No detector is fitted by export or loading.

These are **derived service records**, not the complete original raw datasets.
Each structured atom preserves the recorded cycle, channel, context version,
float32 score and selected original completed-window-last observation. The last
field is a selected source observation; it is not a synthetic value. The package
does not include full windows, below-threshold numeric histories or fitted model
objects, and cannot reproduce arbitrary rescoring or a changed lower threshold.

Per NPZ: `atoms` is the exact structured 16-byte high-record array; `high_bits`
is row-major support packed with little bit order; `high_shape` gives its shape;
`eligible_bits` separately stores one input-usability bit per cycle. Canonical
UTF-8 JSON preserves the charged header, evaluation stages and query metadata.
Query index arrays use an exact arithmetic progression where possible and an
explicit int64 fallback otherwise. The query `hits` array, when present in the
source, is restored exactly from its frozen scope and high-support array. NPZs
contain no object arrays and are read with `allow_pickle=False`.

Use `load_stream(path)` from `scripts/review_frozen_inputs_20261023.py`. Loading
requires only NumPy and Python's standard library, and does not import the source
adapters. The result provides `a`, `h`, `eligible`, `header`, `queries`, `stages`
and dataset/unit/backbone/cadence identity. Every written file was reopened and
checked for byte-exact atoms, exact support/usability, exact query indices and
metadata, and canonical-equivalent header/stages. `manifest.json` contains file
hashes and the core/loader/exporter source hashes. Package byte counts are NPZ
transport sizes, **not** the budgeted archive sizes reported by the experiment.

Annotation-derived event/channel scopes and stages are offline evaluation inputs.
The lossless package preserves them for reproduction; they must not be passed to
online retention or compression decisions. The fixed grid queries are separate.
Fine and coarse streams retain their distinct cycle clocks; ESA released times
are transformed benchmark coordinates and do not establish physical deadlines.

## Attribution and licences

ESA inputs are derived from ESA-ADB v2, released by the European Space Agency and
benchmark contributors at https://zenodo.org/records/15237121 . Original dataset
and benchmark: https://github.com/kplabs-pl/ESA-ADB and De Canio et al., *The ESA
Anomaly Dataset: Advancing Telemetry Anomaly Detection*,
https://arxiv.org/abs/2406.17826 . Data are subject to CC BY 3.0 IGO:
https://creativecommons.org/licenses/by/3.0/igo/ . Retain credit and the licence
link and comply with its IGO-specific terms. Changes include frozen detector
scoring, threshold selection of records, cycle indexing, feedback-context tags
and selection of last-window observations. No ESA endorsement is implied. The
repository code licence does not replace the data licence.

SMD inputs are derived from the Server Machine Dataset, NetManAIOps/OmniAnomaly,
fixed repository revision 7fb0e0acf89ea49908896bcc9f9e80fcfff6baf4. The separately
verified dataset-specific MIT licence (copyright 2021 NetManAIOps-SMD) and its
source receipt are retained under `licences/`. These are the dataset licence,
not an inference from the repository code licence. Retain its copyright and
permission notice when redistributing copies or substantial portions. Derived
changes are the same scoring/record selection and cadence transformations
described above; SMD interpretation labels provide offline query scopes rather
than physical causal-root ground truth.

This package is a local reproducibility artefact. No public upload, DOI or third-
party release is asserted or performed by creating it.
'''

def export_all():
    import review_experiments_20261023 as driver
    import review_fine_stream_20261023 as fine
    import review_archive_core_20261023 as core
    if shutil.disk_usage(ROOT).free<1_000_000_000:raise RuntimeError('Less than 1 GB available on D work disk')
    OUT.mkdir(parents=True,exist_ok=True);begin=time.perf_counter();rows=[]
    sources={p.name:sha(p) for p in [Path(__file__),Path(driver.__file__),Path(fine.__file__),Path(core.__file__)]}
    def persist(s):
        name='_'.join(str(s[k]) for k in ('dataset','unit','backbone','cadence'))+'.npz'
        row=save_stream(s,OUT/name);rows.append(row)
        print('FROZEN_INPUT',len(rows),name,row['atoms'],row['bytes'],flush=True)
    for suite,p,j in driver.coarse_fits():persist(driver.load_coarse(suite,p,j))
    receipts=fine.smd_receipts()
    for entity,kind in fine.available():persist(fine.to_driver_stream(entity,kind,receipts=receipts))
    assert len(rows)==116 and sum(r['cadence']=='coarse' for r in rows)==60
    assert sum(r['cadence']=='fine' for r in rows)==56
    assert sum(r['dataset']=='ESA' for r in rows)==4
    licences=OUT/'licences';licences.mkdir(exist_ok=True)
    existing=ROOT/'results/revision_evidence_representation_20261002/licenses'
    for name in ('SMD_DATASET_LICENSE.txt','SMD_DATASET_LICENSE_SOURCE.json'):
        shutil.copyfile(existing/name,licences/name)
    (OUT/'README.md').write_text(README,encoding='utf-8')
    manifest=dict(schema=SCHEMA,completed=True,streams=len(rows),total_bytes=sum(r['bytes'] for r in rows),
        total_atoms=sum(r['atoms'] for r in rows),total_queries=sum(r['queries'] for r in rows),
        elapsed_seconds=time.perf_counter()-begin,python=platform.python_version(),numpy=np.__version__,
        core_sha256=sources[Path(core.__file__).name],source_sha256=sources,all_reopened_and_exact=True,
        no_training=True,no_raw_dataset_bundle=True,contains_selected_original_windowlast_values=True,
        source_files_unchanged=all(sha(ROOT/'scripts'/name)==value for name,value in sources.items()),
        notes='Derived service inputs; transport NPZ size is not the experimental retained-byte cost.',files=rows)
    assert manifest['source_files_unchanged']
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export',action='store_true');args=parser.parse_args()
    if args.export:export_all()
    else:print('Import load_stream(path) to load; use --export to write the 116 frozen inputs.')
