"""Shared-header bounded chunk experiments; query payloads reopened from disk."""
from pathlib import Path
import argparse,json,struct,time,sys
import numpy as np
import review_archive_core_20261023 as core
import review_experiments_20261023 as driver
import review_fine_stream_20261023 as fine

OUT=driver.OUT;BLOCK=1024
FRAME=struct.Struct('<8sIII');ENTRY=struct.Struct('<IIQIB')
METHODS=['full','bitmap_change','coverage_summary','adaptive']
CODES={'full':1,'bitmap_change':2,'coverage_summary':3,'coverage_fill':4}
DECODE={v:k for k,v in CODES.items()}

class Online:
    def __init__(self,s,B,method,path):
        self.s=s;self.B=B;self.method=method;self.path=path;self.chunks=[];self.now=0
        self.evictions=0;self.rejections=0;self.rows=[];self.peak_open=0;self.peak_transient=0
        self.query_ms=[];self.query_read=[]

    def header(self):return driver.clean_header(self.s['header'],self.now)
    def base_size(self):
        return FRAME.size+len(json.dumps(self.header(),sort_keys=True,separators=(',',':')).encode())
    def size(self):return self.base_size()+len(self.chunks)*ENTRY.size+sum(len(x['payload']) for x in self.chunks)
    def payload(self,a,lo,hi,method,budget=None):
        return core.encode_payload(a,self.s['h'][:hi],self.s['eligible'][:hi],self.header(),method,
                                   start=lo,stop=hi,width=256,budget=budget)[0]
    def close(self,lo,hi):
        self.now=hi;a=self.s['a'];aa=a[(a['t']>=lo)&(a['t']<hi)]
        # Input observations only through this close; full source arrays are
        # preloaded detector inputs and excluded from archive memory accounting.
        self.peak_open=max(self.peak_open,aa.nbytes+(hi-lo)*(self.s['h'].shape[1]+1))
        t=time.perf_counter_ns();ev=0;rejected=False;kind=self.method
        if kind=='adaptive':
            p=self.payload(aa,lo,hi,'full');kind='full'
            if self.size()+ENTRY.size+len(p)>self.B:
                base=self.payload(aa,lo,hi,'coverage_summary');kind='coverage_fill'
                while self.chunks and self.size()+ENTRY.size+len(base)>self.B:
                    self.chunks.pop(0);self.evictions+=1;ev+=1
                remaining=self.B-self.size()-ENTRY.size
                p=self.payload(aa,lo,hi,'coverage_fill',max(0,remaining))
        else:p=self.payload(aa,lo,hi,kind)
        self.peak_transient=max(self.peak_transient,self.size()+len(p)+aa.nbytes)
        if self.base_size()+ENTRY.size+len(p)>self.B:
            self.rejections+=1;rejected=True
        else:
            self.chunks.append(dict(lo=lo,hi=hi,payload=p,kind=kind))
            while self.size()>self.B:
                self.chunks.pop(0);self.evictions+=1;ev+=1
        encode_ms=(time.perf_counter_ns()-t)/1e6
        t=time.perf_counter_ns();self.write();write_ms=(time.perf_counter_ns()-t)/1e6
        self.rows.append(dict(lo=lo,now=hi,bytes=self.size(),chunks=len(self.chunks),evicted=ev,rejected=rejected,
                              encode_ms=encode_ms,write_ms=write_ms,kind=kind))

    def write(self):
        h=json.dumps(self.header(),sort_keys=True,separators=(',',':')).encode()
        start=FRAME.size+len(h)+ENTRY.size*len(self.chunks);entries=[];parts=[]
        for z in self.chunks:
            entries.append(ENTRY.pack(z['lo'],z['hi'],start,len(z['payload']),CODES[z['kind']]))
            parts.append(z['payload']);start+=len(z['payload'])
        blob=FRAME.pack(b'ONRV1023',self.now,len(h),len(entries))+h+b''.join(entries)+b''.join(parts)
        assert len(blob)==self.size()<=self.B
        self.path.parent.mkdir(parents=True,exist_ok=True);self.path.write_bytes(blob)
        assert self.path.stat().st_size==len(blob)

    def query(self,idx,ch):
        start=time.perf_counter_ns();idx=np.unique(idx);parts=[];ranges=[];read=0
        with self.path.open('rb') as f:
            magic,now,hs,n=FRAME.unpack(f.read(FRAME.size));h=json.loads(f.read(hs))
            assert magic==b'ONRV1023' and now==self.now
            entries=[ENTRY.unpack(f.read(ENTRY.size)) for _ in range(n)]
            for lo,hi,offset,size,kind in entries:
                ix=idx[(idx>=lo)&(idx<hi)]
                if not len(ix):continue
                f.seek(offset);blob=f.read(size);read+=len(blob)
                ar=core.decode_payload(blob,h,DECODE[kind]);r=core.query(ar,ix,ch)
                parts.append((ix,r));ranges.append((lo,hi))
        covered=np.zeros(len(idx),bool)
        for lo,hi in ranges:covered|=(idx>=lo)&(idx<hi)
        # Each chunk supplies exact lower/upper count bounds under its own
        # retained information. Missing time ranges are unconstrained worlds.
        minimum=sum(r['min_high_count'] for _,r in parts)
        maximum=sum(r['max_high_count'] for _,r in parts)+int((~covered).sum())
        answer='yes' if minimum else 'no' if maximum==0 else 'unknown'
        possible=[r['earliest_possible'] for _,r in parts if r['max_high_count']]
        if (~covered).any():possible.append(int(idx[~covered][0]))
        earliest=min(possible) if possible else -1
        forced=[r['latest_possible_first'] for _,r in parts if r['min_high_count']]
        latest=min(forced) if forced else -1
        cert=answer=='yes' and earliest==latest
        arrays=[r['numeric'] for _,r in parts if len(r['numeric'])]
        numeric=np.concatenate(arrays) if arrays else np.empty(0,core.ATOM)
        if len(numeric):numeric=numeric[np.argsort(numeric['t'],kind='stable')]
        joint=cert and bool(np.any(numeric['t']==earliest))
        complete=minimum==maximum==len(numeric)
        ms=(time.perf_counter_ns()-start)/1e6;self.query_ms.append(ms);self.query_read.append(read)
        return dict(answer=answer,first_certified=cert,first_cycle=earliest if cert else -1,
                    first_numeric_joint=joint,complete_report=complete,numeric=numeric,
                    missing_cycles=int((~covered).sum()),cross_boundary=bool(covered.any() and (~covered).any()),
                    rejected_hole=bool(any(z['rejected'] and np.any((idx>=z['lo'])&(idx<z['now'])) for z in self.rows)),
                    query_ms=ms,read_bytes=read)

def queries(s,now):
    c=s['h'].shape[1];out=[];ages=[0,1,4,16]
    ends=[(f'chunk_{age}',max(0,now-1-age*BLOCK)) for age in ages]
    ends += [(f'fraction_{fraction}',int((now-1)*fraction)) for fraction in (.25,.5,.75)]
    for k,(kind,end) in enumerate(ends):
        for j,length in enumerate((1,64,1024,4096)):
            idx=np.arange(max(0,end-length+1),end+1,dtype=int)
            out.append(dict(idx=idx,channel=(k*7+j*3)%c,age_kind=kind,length=length,trigger='scheduled'))
    # Past high decisions create review triggers; no annotations are consulted.
    ts=np.flatnonzero(s['h'][:now].any(axis=1))
    if len(ts):
        for k in range(8):
            anchor=int(ts[int((len(ts)-1)*k/7)]);ch=int(np.flatnonzero(s['h'][anchor])[k%int(s['h'][anchor].sum())])
            for length in (64,1024):
                end=min(now-1,anchor+length//2);idx=np.arange(max(0,end-length+1),end+1,dtype=int)
                out.append(dict(idx=idx,channel=ch,age_kind='past_high',length=length,trigger='observed_high'))
    return out

def run_one(s,B,method):
    name='_'.join(str(v) for v in driver.key(s).values())+f'_{B}_{method}_b{BLOCK}'
    ar=Online(s,B,method,OUT/'online_snapshots'/f'{name}.arc')
    n=len(s['h']);ends=list(range(BLOCK,n,BLOCK))+[n]
    targets={ends[min(len(ends)-1,int((len(ends)-1)*f))] for f in (.25,.5,.75,1.)}
    detail=[];lo=0
    for hi in ends:
        ar.close(lo,hi);lo=hi
        if hi not in targets:continue
        snapshot=OUT/'online_snapshots'/f'{name}_{hi}.arc';snapshot.write_bytes(ar.path.read_bytes())
        for q in queries(s,hi):
            rr=ar.query(q['idx'],q['channel']);hits,aa=driver.truth(s,q['idx'],q['channel'])
            positive=bool(len(hits));first=int(hits[0]) if positive else -1
            false=(rr['answer']=='yes' and not positive) or (rr['answer']=='no' and positive)
            false|=rr['first_certified'] and (not positive or rr['first_cycle']!=first)
            false|=rr['complete_report'] and rr['numeric'].tobytes()!=aa.tobytes()
            if rr['first_numeric_joint']:false|=rr['numeric'][rr['numeric']['t']==first][0].tobytes()!=aa[0].tobytes()
            assert not false,(name,q,rr)
            age=hi-1-int(q['idx'][-1]);r={k:v for k,v in rr.items() if k!='numeric'}
            detail.append(dict(now=hi,query_start=int(q['idx'][0]),query_end=int(q['idx'][-1]),channel=q['channel'],
                               age=age,age_fraction=age/max(1,hi),age_kind=q['age_kind'],length=q['length'],trigger=q['trigger'],
                               positive=positive,reference_first=first,**r,false_certificate=False))
    base=dict(driver.key(s),budget=B,method=method,block=BLOCK)
    driver.write_csv(OUT/'online_details'/f'{name}.csv.gz',[dict(base,**r) for r in detail])
    driver.write_csv(OUT/'online_flush'/f'{name}.csv',[dict(base,**r) for r in ar.rows])
    pos=[r for r in detail if r['positive']]
    summary=dict(base,queries=len(detail),positive_queries=len(pos),joint_first=sum(r['first_numeric_joint'] for r in pos),
                 complete_positive=sum(r['complete_report'] for r in pos),unknown=sum(r['answer']=='unknown' for r in detail),
                 false_certificates=0,bytes=ar.size(),max_bytes=max(z['bytes'] for z in ar.rows),
                 evictions=ar.evictions,rejections=ar.rejections,retained_chunks=len(ar.chunks),
                 earliest_retained=min([z['lo'] for z in ar.chunks]+[n]),peak_open_bytes=ar.peak_open,
                 tracked_transient_bytes=ar.peak_transient,
                 close_p95_ms=float(np.percentile([r['encode_ms']+r['write_ms'] for r in ar.rows],95)),
                 query_p95_ms=float(np.percentile(ar.query_ms,95)),mean_payload_read=float(np.mean(ar.query_read)))
    return summary

def streams(pilot):
    for suite,p,j in driver.coarse_fits():
        unit=str(j['arguments']['mission']) if suite=='ESA' else j['entity'];bb=j['arguments']['backbone'] if suite=='ESA' else j['backbone']
        if (suite=='ESA' and unit=='1') or (suite=='SMD' and unit=='machine-3-4' and bb=='ridge'):
            if pilot and suite!='SMD':continue
            yield driver.load_coarse(suite,p,j)
    yield fine.to_driver_stream('machine-3-4','ridge',stride=1)

def main():
    global BLOCK
    p=argparse.ArgumentParser();p.add_argument('--pilot',action='store_true');p.add_argument('--block',type=int,default=1024);args=p.parse_args();BLOCK=args.block
    rows=[];start=time.time()
    for s in streams(args.pilot):
        for B in driver.BUDGETS:
            for method in METHODS:
                row=run_one(s,B,method);rows.append(row)
                print(json.dumps(dict(row,elapsed=round(time.time()-start,2))),flush=True)
                driver.write_csv(OUT/(f'online_pilot_b{BLOCK}.csv' if args.pilot else f'online_summary_b{BLOCK}.csv'),rows)

if __name__=='__main__':main()
