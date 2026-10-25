"""Actual reversible detector-record archives. Frozen scores, no fitting.

Only immutable metadata is cached for file-query timing. Every query opens and
reads/decompresses its needed payload; all decoded records are discarded.
"""
from pathlib import Path
import argparse, csv, hashlib, json, platform, struct, time, zlib
import numpy as np
import evidence_representation_audit as old

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/revision_archive_task_20261009/codec'
ATOM = old.ATOM
MAGIC = b'EARC1009'
FRAME = struct.Struct('<8sBBI')
ENTRY = struct.Struct('<HIIQII')
U32 = struct.Struct('<I')
KINDS = {'aos_zlib': 1, 'soa_zlib': 2, 'bitmap_numeric': 3, 'chunked_soa': 4}
BLOCK = 1024
BUDGETS = [k*1024 for k in [32,64,128,256,512,1024,2048]]
FIELDS = ['t','ch','v','q','x']
DTYPES = ['<u4','<u2','<u2','<f4','<f4']
BYTE_POPCOUNT=np.asarray([int(k).bit_count() for k in range(256)],dtype=np.uint8)

PROTOCOL = '''# Reversible storage and bounded archive software protocol

Route: SCI applied evidence-archive/system design. No new compression algorithm,
no detector training and no human-effect measurement. This protocol is a new
retrospective analysis, written before the present codec/runtime execution.

Input: all 60 existing seed-0 PCA/ridge frozen fits (28 SMD devices, two ESA
missions). The same eligible baseline-high records as the earlier audit, with
cycle uint32, channel uint16, arrived-review version uint16, score float32 and
completed-window last feature float32 (16 bytes). These are not raw waveforms.
File input sees no event or affected-dimension labels. The existing review tape
is simulated and may have used public labels; no claim of globally label-free
system training is made. Files include actual canonical JSON source/clock/
schema metadata; scores and float32 values must decode bit for bit.

Mature simple layouts: (1) 16-byte array-of-structures zlib9; (2) each t/ch/v/q/x
column compressed independently with zlib9 and actual count/length frames;
(3) compressed full support bitmap plus v/q/x in channel-major high order;
(4) fixed 1024-cycle, per-channel columnar chunks with an actual binary directory
containing channel,start,end,absolute offset,payload length and record count.
All files include framing, metadata and directory bytes. Seven illustrative
total-file budgets are 32,64,128,256,512,1024 and 2048 KiB. They are capacity
parameters, not evidence of field deployment limits. No compressed size is
used as a surrogate for complete telemetry cost.

File correctness: every one of the 240 actual files is reopened by the format
decoder and compared with canonical source record bytes. Queries: 64 fixed
label-free interval queries per fit, covering single-cycle, short, block-crossing
and long intervals, plus ranges around observed detector highs and sampled
no-high points. High selection is not annotation selection. All query expected
records come from reference only after file retrieval. Each codec executes all
64 queries three times (192 reads per fit/codec). Report p50/p95 wall-clock
query latency and actual bytes read, including open/read and decode; hardware,
Python/zlib version, repetition and warm-up are recorded. Operating-system
cache is warm, cold-disk timing is not claimed. Only header/directory metadata
is cached; decoded record payload is not cached. Full formats read the whole
numeric payload; indexed files read relevant channel/time chunks only. This
measures a Python software implementation, not spacecraft timing.

Online prototype: four preselected fits: ESA Mission1 PCA/ridge, SMD machine-1-1
PCA and machine-3-8 ridge. Replay every decision in chronological order at 64,
256 and 1024 KiB, independent of labels. At each cycle append available records
to an open 1024-cycle block; work buffer is separate from persisted capacity.
On close, encode a reversible columnar time block, persist complete chunks,
and FIFO-evict old complete chunks until actual framed file size fits. An
oversized single chunk is rejected and its coverage is unknown. Empty chunks
are persisted and indexed so no-high intervals can be certified. Metadata
directory ranges certify coverage; no free watermark/index is excluded.
Persistent bytes <= B are checked after each decision. Open buffer payload and
Python object memory peaks are separately reported. The input detector array
is preloaded and excluded from archive memory (explicitly documented).
Per-cycle update timing includes appending, capacity checks, and at block close
compression and actual snapshot write. Normal and close-cycle latency are
reported separately; their combined p95 must not conceal rare close costs.

Runtime query as of t sees persisted complete chunks and the open block only
through t. Support is yes for any observed retained high; no requires complete
query-time coverage and no high; missing coverage with no high is unknown.
Earliest is certified only if every time before the first retained high is
covered. A stored witness may remain available without a certified earliest.
V means the declared high-record stream in the query, not all low values.
Query validation checks no wrong certified yes/no/first/value answer against
source. Synthetic cases include empty/overflow/rejection/coverage gaps and
future suffix prefix-invariance. Files/results live only on D; raw sources
are read-only, not redownloaded or changed.
'''

def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')

def writecsv(path, rows):
    if not rows:return
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def receipts():
    return [z for z in old.f.receipts() if
            (z[2]['arguments']['backbone'] if z[0]=='ESA' else z[2]['backbone']) in ['pca','ridge'] and
            (z[2]['arguments']['seed'] if z[0]=='ESA' else z[2]['seed'])==0]

def prefix(header, kind):
    hb=json.dumps(header,sort_keys=True,separators=(',',':')).encode()
    return FRAME.pack(MAGIC,1,KINDS[kind],len(hb))+hb

def encode_soa(a):
    cols=[zlib.compress(np.asarray(a[k],dtype=t).tobytes(),9) for k,t in zip(FIELDS,DTYPES)]
    return struct.pack('<6I',len(a),*[len(x) for x in cols])+b''.join(cols)

def decode_soa(blob):
    n,*lengths=struct.unpack('<6I',blob[:24]);pos=24;a=np.empty(n,ATOM)
    for k,t,sz in zip(FIELDS,DTYPES,lengths):
        raw=zlib.decompress(blob[pos:pos+sz]);pos+=sz
        if len(raw)!=n*np.dtype(t).itemsize:raise ValueError('Invalid column byte count')
        a[k]=np.frombuffer(raw,dtype=t)
    if pos!=len(blob):raise ValueError('Unused trailing column bytes')
    return a

def encode_bitmap_numeric(a,n,c):
    bits=np.zeros((c,(n+7)//8),dtype=np.uint8)
    for ch in range(c):
        t=a['t'][a['ch']==ch];np.bitwise_or.at(bits[ch],t//8,(1<<(t%8)).astype(np.uint8))
    order=np.lexsort((a['t'],a['ch']));b=a[order]
    cols=[zlib.compress(bits.tobytes(),9)]+[zlib.compress(np.asarray(b[k],dtype=t).tobytes(),9) for k,t in [('v','<u2'),('q','<f4'),('x','<f4')]]
    return struct.pack('<5I',len(a),*[len(z) for z in cols])+b''.join(cols)

def decode_bitmap_numeric(blob,n,c):
    count,*lengths=struct.unpack('<5I',blob[:20]);pos=20;cols=[]
    for size in lengths:cols.append(zlib.decompress(blob[pos:pos+size]));pos+=size
    if pos!=len(blob):raise ValueError('Unused bitmap trailing bytes')
    bitmap=np.frombuffer(cols[0],np.uint8).reshape(c,-1)
    high=np.unpackbits(bitmap,axis=1,bitorder='little')[:,:n]
    ci,ti=np.nonzero(high);a=np.empty(count,ATOM)
    if len(ti)!=count:raise ValueError('Support/numeric count mismatch')
    a['t']=ti;a['ch']=ci
    for k,t,raw in zip(['v','q','x'],['<u2','<f4','<f4'],cols[1:]):
        if len(raw)!=count*np.dtype(t).itemsize:raise ValueError('Numeric column size mismatch')
        a[k]=np.frombuffer(raw,dtype=t)
    return a[np.lexsort((a['ch'],a['t']))]

def build_file(path,kind,a,header):
    n=header['n_cycles'];c=len(header['channels']);hp=prefix(header,kind)
    index_bytes=0;chunk_count=0
    if kind=='aos_zlib':body=U32.pack(len(a))+zlib.compress(a.tobytes(),9)
    elif kind=='soa_zlib':body=encode_soa(a)
    elif kind=='bitmap_numeric':body=encode_bitmap_numeric(a,n,c)
    else:
        groups={}
        for k,z in enumerate(a):groups.setdefault((int(z['ch']),int(z['t'])//BLOCK),[]).append(k)
        chunks=[]
        for (ch,bi),ids in sorted(groups.items()):
            payload=encode_soa(a[np.asarray(ids,dtype=np.int64)])
            chunks.append((ch,bi*BLOCK,min(n,(bi+1)*BLOCK),len(ids),payload))
        index_bytes=4+ENTRY.size*len(chunks);chunk_count=len(chunks)
        off=len(hp)+index_bytes;directory=[];parts=[]
        for ch,lo,hi,count,payload in chunks:
            directory.append(ENTRY.pack(ch,lo,hi,off,len(payload),count));parts.append(payload);off+=len(payload)
        body=U32.pack(len(chunks))+b''.join(directory)+b''.join(parts)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(hp+body)
    return dict(bytes=path.stat().st_size,header_frame_bytes=len(hp),index_bytes=index_bytes,
                payload_bytes=len(body)-index_bytes,chunks=chunk_count)

class ArchiveReader:
    """Cache metadata/index only; each call physically opens and reads payload."""
    def __init__(self,path):
        self.path=Path(path)
        with self.path.open('rb') as f:
            magic,version,kind,sz=FRAME.unpack(f.read(FRAME.size))
            if magic!=MAGIC or version!=1:raise ValueError('Invalid archive frame')
            self.kind=next(k for k,v in KINDS.items() if v==kind)
            self.header=json.loads(f.read(sz));self.payload_start=f.tell()
            self.directory=[]
            if self.kind=='chunked_soa':
                count=U32.unpack(f.read(4))[0]
                for _ in range(count):self.directory.append(ENTRY.unpack(f.read(ENTRY.size)))
        self.file_bytes=self.path.stat().st_size
        self.metadata_bytes=self.payload_start+(4+ENTRY.size*len(self.directory) if self.kind=='chunked_soa' else 0)

    def all(self):
        if self.kind=='chunked_soa':
            parts=[]
            with self.path.open('rb') as f:
                for ch,lo,hi,off,length,count in self.directory:
                    f.seek(off);part=decode_soa(f.read(length))
                    if len(part)!=count or np.any(part['ch']!=ch):raise ValueError('Directory mismatch')
                    parts.append(part)
            a=np.concatenate(parts) if parts else np.empty(0,ATOM)
            return a[np.lexsort((a['ch'],a['t']))]
        with self.path.open('rb') as f:f.seek(self.payload_start);blob=f.read()
        if self.kind=='aos_zlib':
            count=U32.unpack(blob[:4])[0];raw=zlib.decompress(blob[4:]);a=np.frombuffer(raw,ATOM).copy()
            if len(a)!=count:raise ValueError('Atom count mismatch')
            return a
        if self.kind=='soa_zlib':return decode_soa(blob)
        return decode_bitmap_numeric(blob,self.header['n_cycles'],len(self.header['channels']))

    def query(self,ch,lo,hi):
        """Inclusive range; negative and empty intervals are exact no-high."""
        read=0
        if hi<lo:return np.empty(0,ATOM),read
        if not (0<=ch<len(self.header['channels']) and 0<=lo<=hi<self.header['n_cycles']):raise ValueError('Out-of-service query')
        if self.kind=='bitmap_numeric':
            # The monolithic compressed payload must still be read/decoded,
            # but a range query need not materialize all C*T threshold bits
            # or rebuild/sort every channel's records. Rank before the target
            # channel gives its offset into the channel-major numeric columns.
            with self.path.open('rb') as f:f.seek(self.payload_start);blob=f.read()
            read=len(blob);count,*lengths=struct.unpack('<5I',blob[:20]);pos=20
            raw=[]
            for size in lengths:raw.append(zlib.decompress(blob[pos:pos+size]));pos+=size
            if pos!=len(blob):raise ValueError('Unused bitmap trailing bytes')
            packed=np.frombuffer(raw[0],np.uint8).reshape(len(self.header['channels']),-1)
            offset=int(BYTE_POPCOUNT[packed[:ch]].sum(dtype=np.int64))
            ti=np.flatnonzero(np.unpackbits(packed[ch],bitorder='little')[:self.header['n_cycles']])
            left=int(np.searchsorted(ti,lo));right=int(np.searchsorted(ti,hi,side='right'))
            a=np.empty(right-left,ATOM);a['t']=ti[left:right];a['ch']=ch
            for name,dtype,values in zip(['v','q','x'],['<u2','<f4','<f4'],raw[1:]):
                if len(values)!=count*np.dtype(dtype).itemsize:raise ValueError('Numeric column size mismatch')
                a[name]=np.frombuffer(values,dtype=dtype)[offset+left:offset+right]
            return a,read
        if self.kind!='chunked_soa':
            # Opens/reads inside all(); no decoded arrays survive the call.
            a=self.all();read=self.file_bytes-self.payload_start
        else:
            parts=[]
            with self.path.open('rb') as f:
                for c,l,r,off,length,count in self.directory:
                    if c==ch and l<=hi and r>lo:
                        f.seek(off);blob=f.read(length);read+=len(blob);parts.append(decode_soa(blob))
            a=np.concatenate(parts) if parts else np.empty(0,ATOM)
        return a[(a['ch']==ch)&(a['t']>=lo)&(a['t']<=hi)],read

def fixed_queries(a,n,c):
    """Detector-dependent and fixed grids, never event/dimension annotations."""
    rng=np.random.default_rng(20261009);queries=[]
    lengths=[1,8,64,1024,4096]
    for i in range(40):
        lo=int(rng.integers(n));ch=int(rng.integers(c));size=lengths[i%len(lengths)]
        queries.append(dict(ch=ch,lo=lo,hi=min(n-1,lo+size-1),family='fixed_grid'))
    for k in np.linspace(0,max(0,len(a)-1),8).astype(int):
        if len(a):
            z=a[k];t=int(z['t']);queries.append(dict(ch=int(z['ch']),lo=max(0,t-3),hi=min(n-1,t+3),family='around_high'))
        else:queries.append(dict(ch=0,lo=0,hi=0,family='empty_stream'))
    for i in range(8):
        t=min(n-1,(i+1)*BLOCK);queries.append(dict(ch=i%c,lo=max(0,t-2),hi=min(n-1,t+2),family='block_boundary'))
    for i in range(8):
        t=int(rng.integers(n));ch=int(rng.integers(c))
        # Negative points are selected from detector presence, not truth labels.
        for _ in range(100):
            if not np.any((a['t']==t)&(a['ch']==ch)):break
            t=int(rng.integers(n))
        queries.append(dict(ch=ch,lo=t,hi=t,family='sampled_no_high'))
    assert len(queries)==64
    return queries

def selfcheck():
    d=OUT/'synthetic';d.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(90)
    cases=0
    for case in range(12):
        n=30 if case<6 else 2052;c=3;h=rng.random((n,c))<(.01 if case%2 else .8)
        ti,ch=np.nonzero(h);a=np.empty(len(ti),ATOM);a['t']=ti;a['ch']=ch;a['v']=ti//10;a['q']=rng.normal(size=len(a));a['x']=rng.normal(size=len(a))
        if case==0:a=np.empty(0,ATOM)
        header=dict(n_cycles=n,channels=[str(i) for i in range(c)])
        for kind in KINDS:
            p=d/f'{case}_{kind}.arc';build_file(p,kind,a,header);r=ArchiveReader(p)
            assert r.all().tobytes()==a.tobytes()
            for q in fixed_queries(a,n,c):
                got,_=r.query(q['ch'],q['lo'],q['hi'])
                ref=a[(a['ch']==q['ch'])&(a['t']>=q['lo'])&(a['t']<=q['hi'])]
                assert got.tobytes()==ref.tobytes();cases+=1
    return cases

def environment():
    return dict(platform=platform.platform(),machine=platform.machine(),processor=platform.processor(),
                python=platform.python_version(),numpy=np.__version__,zlib_compile=zlib.ZLIB_VERSION,
                zlib_runtime=zlib.ZLIB_RUNTIME_VERSION,cache='warm operating-system cache; metadata only cached',
                input='frozen existing scores; all workload files on D',compression='zlib level 9')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['pilot','full'],default='full');args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);protocol=OUT.parent/'CODEC_RUNTIME_PROTOCOL.md'
    if not protocol.exists():protocol.write_text(PROTOCOL,encoding='utf-8')
    rs=receipts()
    if args.mode=='pilot':rs=[z for z in rs if z[0]=='SMD' and z[2]['entity']=='machine-1-1' or z[0]=='ESA' and str(z[2]['arguments']['mission'])=='1']
    start=time.perf_counter();tests=selfcheck();costs=[];perf=[];query_rows=[];decode=[];source_before={}
    previous_cost={}
    previous=OUT/args.mode/'cost.csv'
    if previous.exists():
        with previous.open(encoding='utf-8') as f:
            previous_cost={(z['run'],z['codec']):int(z['bytes']) for z in csv.DictReader(f)}
    for suite,p,j in rs:
        d,a,h,hb,head,selected,pp,policy,paths=old.load(suite,p,j)
        run=p.parent.name;base=dict(dataset=suite,unit=d['unit'],backbone=d['backbone'],run=run,
                                    cycles=len(h),channels=h.shape[1],high_atoms=len(a))
        queries=fixed_queries(a,len(h),h.shape[1]);folder=OUT/args.mode/run
        for source in paths:
            if source.is_file() and source.name!='features_raw.npy':source_before[str(source)]=old.f.sha(source)
        for kind in KINDS:
            path=folder/(kind+'.arc');t0=time.perf_counter();s=build_file(path,kind,a,head);build_ms=(time.perf_counter()-t0)*1000
            if previous_cost:assert s['bytes']==previous_cost[(run,kind)],'Physical storage cost changed during query-interface repair'
            reader=ArchiveReader(path);restored=reader.all()
            assert restored.tobytes()==a.tobytes(),f'File decode differs: {path}'
            decode.append(dict(base,codec=kind,file_bytes=path.stat().st_size,
                               source_record_sha256=hashlib.sha256(a.tobytes()).hexdigest(),
                               decoded_record_sha256=hashlib.sha256(restored.tobytes()).hexdigest(),
                               file_sha256=old.f.sha(path),all_payload_bits_equal=True))
            del restored
            # One warm pass. Timed repetitions always decode fresh payloads.
            for q in queries:reader.query(q['ch'],q['lo'],q['hi'])
            ms=[];reads=[]
            for rep in range(3):
                for qi,q in enumerate(queries):
                    t0=time.perf_counter_ns();got,read=reader.query(q['ch'],q['lo'],q['hi']);elapsed=(time.perf_counter_ns()-t0)/1e6
                    ref=a[(a['ch']==q['ch'])&(a['t']>=q['lo'])&(a['t']<=q['hi'])]
                    assert got.tobytes()==ref.tobytes()
                    ms.append(elapsed);reads.append(read)
                    if rep==0:query_rows.append(dict(base,codec=kind,query_id=qi,**q,records=len(got),bytes_read=read,
                                                       support='yes' if len(got) else 'no',first=int(got['t'][0]) if len(got) else None,
                                                       V_complete=True,certified=True))
            costs.append(dict(base,codec=kind,**s,build_ms=build_ms))
            perf.append(dict(base,codec=kind,queries=len(queries)*3,repeats=3,p50_ms=float(np.percentile(ms,50)),
                             p95_ms=float(np.percentile(ms,95)),max_ms=max(ms),mean_bytes_read=float(np.mean(reads)),
                             p95_bytes_read=float(np.percentile(reads,95)),metadata_cached_bytes=reader.metadata_bytes,
                             decoded_payload_cached=False,cache='warm OS cache'))
        print(suite,d['unit'],d['backbone'],'atoms',len(a),'files OK',flush=True)
    source_after={p:old.f.sha(Path(p)) for p in source_before};assert source_before==source_after
    writecsv(OUT/args.mode/'cost.csv',costs);writecsv(OUT/args.mode/'query_performance.csv',perf)
    writecsv(OUT/args.mode/'fixed_queries.csv',query_rows);writecsv(OUT/args.mode/'FILE_DECODE_AUDIT.csv',decode)
    fits=[dict(dataset=s,backbone=b,codec=k,budget=B,fits=sum(x['bytes']<=B for x in costs if x['dataset']==s and x['backbone']==b and x['codec']==k),
               total=sum(x['dataset']==s and x['backbone']==b and x['codec']==k for x in costs))
          for s in ['ESA','SMD'] for b in ['pca','ridge'] for k in KINDS for B in BUDGETS]
    writecsv(OUT/args.mode/'budget_feasibility.csv',fits)
    save(OUT/args.mode/'COMPLETION.json',dict(passed=True,fits=len(rs),files=len(decode),cost_rows=len(costs),
          timed_queries=len(perf)*192,unique_file_queries=len(query_rows),synthetic_queries=tests,
          sources_unchanged=len(source_before),source_hashes=source_after,environment=environment(),
          wall_seconds=time.perf_counter()-start,script_sha256=old.f.sha(Path(__file__)),protocol_sha256=old.f.sha(protocol),
          no_training=True,all_actual_files_fully_decoded=True,
          previous_physical_cost_unchanged=bool(previous_cost),bitmap_query='target-channel unpack/rank; compressed payload still fully read'))
    print('completed',args.mode,len(decode),'files',round(time.perf_counter()-start,2),'seconds',flush=True)

if __name__=='__main__':main()
