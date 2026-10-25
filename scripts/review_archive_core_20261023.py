"""Finite high-record archives with billed local completeness, 2026-10-23.

Route: SCI applied monitoring-system study. The contribution is an evaluated
resource/query contract, not new compression or certain-answer theory. No
annotations, incident identifiers, or future query scopes enter this module.

All arrays exposed by Archive are decoded from its retained bytes. Numeric
records use the existing 16-byte t/ch/version/score/window-last contract. A
separately compressed usability bitmap distinguishes unavailable inputs from
observed below-threshold inputs; it is charged to every format.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib, itertools, json, struct, time, zlib
import numpy as np
import archive_codec_20261009 as codec

ATOM = codec.ATOM
MAGIC = b'RARC1023'
FRAME = struct.Struct('<8sBI')
# kind,start,stop,width,group-count, support/usability/group/numeric/fill bytes
BODY = struct.Struct('<B9I')
GROUP = np.dtype([('lo','<u4'),('hi','<u4'),('ch','<u2'),('flags','u1'),
                  ('count','<u4'),('first','<u4'),('last','<u4'),
                  ('minimum','<u4'),('maximum','<u4')])
SENTINEL = np.iinfo(np.uint32).max
METHODS = ('full','bitmap_change','bitmap_change_fill','coverage_summary',
           'coverage_fill','adaptive_bitmap_fill','adaptive_coverage_fill','adaptive_full_fill')

@dataclass
class Archive:
    blob: bytes
    header: dict
    method: str
    numeric: np.ndarray
    groups: np.ndarray
    support: object
    usability: np.ndarray
    start: int
    stop: int
    width: int
    feasible: bool = True
    required_bytes: int = 0
    stats: object = None

    @property
    def size(self): return len(self.blob)
    @property
    def bytes(self): return len(self.blob)

def _header(header, method):
    h=dict(header)
    if len(method)>32:raise ValueError('Method identifier exceeds fixed 32-character field')
    h.update(archive_format='finite-review-v1',archive_method=method.ljust(32),
             group_fields=GROUP.descr,
             completeness='complete bucket-channel high count; explicit first/last/min/max roles',
             usability='separate charged channel-shared decision usability bitmap')
    return h

def frame_payload(payload, header, method):
    h=_header(header,method)
    raw=json.dumps(h,sort_keys=True,separators=(',',':')).encode()
    return FRAME.pack(MAGIC,1,len(raw))+raw+payload

def frame_bytes(header, method):
    return len(frame_payload(b'',header,method))

def _usable(eligible,n):
    u=np.asarray(eligible,dtype=bool)
    if u.shape!=(n,):raise ValueError('Usability must be a channel-shared vector of n_cycles entries')
    return u

def _encode(a,h,u,start,stop,width,kind,groups,ids,fill_ids=()):
    """Actual payload; t is absolute, support/usability cover [start,stop)."""
    if kind==1:numeric=codec.encode_soa(a);support=b''
    elif kind==2:numeric=codec.encode_bitmap_numeric(a,stop,h.shape[1]);support=b''
    else:
        numeric=a[np.asarray(ids,dtype=np.int64)].tobytes()
        support=zlib.compress(np.packbits(h[start:stop].T,axis=1,bitorder='little').tobytes(),9) if kind==3 else b''
    ub=zlib.compress(np.packbits(u[start:stop],bitorder='little').tobytes(),9)
    gb=zlib.compress(groups.tobytes(),9) if len(groups) else b''
    fill=a[np.asarray(fill_ids,dtype=np.int64)].tobytes()
    body=BODY.pack(kind,start,stop,width,len(groups),len(support),len(ub),len(gb),len(numeric),len(fill))
    return body+support+ub+gb+numeric+fill

def _summary(a,start,stop,width,c):
    """Every included group describes its whole processed bucket/channel."""
    by={}
    for k,z in enumerate(a):
        by.setdefault(((int(z['t'])-start)//width,int(z['ch'])),[]).append(k)
    groups=[];picked=[]
    for bi,lo in enumerate(range(start,stop,width)):
        hi=min(stop,lo+width)
        for ch in range(c):
            ids=by.get((bi,ch),[])
            if ids:
                zz=np.asarray(ids,dtype=np.int64);vals=a['q'][zz]
                ff,ll,mn,mx=ids[0],ids[-1],int(zz[np.argmin(vals)]),int(zz[np.argmax(vals)])
                groups.append((lo,hi,ch,1,len(ids),int(a['t'][ff]),int(a['t'][ll]),int(a['t'][mn]),int(a['t'][mx])))
                picked.extend((ff,ll,mn,mx))
            else:groups.append((lo,hi,ch,1,0,SENTINEL,SENTINEL,SENTINEL,SENTINEL))
    return np.asarray(groups,dtype=GROUP),np.unique(picked).astype(np.int64)

def _changes(a,tau,width,start,high,stop):
    """Existing parent first/last/min/max + .25tau change reference.

    Parents are contiguous cycles with any eligible channel high (gap zero).
    A chunk closes a parent at its own boundary; an all-history call is exactly
    the previous parent-summary record selection, without incident labels.
    """
    active=high[start:stop].any(axis=1)
    begins=active&~np.r_[False,active[:-1]]
    pp=np.cumsum(begins,dtype=np.int64)-1
    by={}
    for k,z in enumerate(a):by.setdefault((int(pp[int(z['t'])-start]),int(z['ch'])),[]).append(k)
    chosen=[]
    for ids in by.values():
        zz=np.asarray(ids,dtype=np.int64);vals=a['q'][zz]
        chosen.extend((ids[0],ids[-1],int(zz[np.argmin(vals)]),int(zz[np.argmax(vals)])))
        last=ids[0]
        for k in ids[1:]:
            if abs(float(a['q'][k])-float(a['q'][last]))>=.25*tau:chosen.append(k);last=k
    return np.unique(chosen).astype(np.int64)

def encode_payload(atoms, high, eligible, header, method='coverage_summary', *,
                   width=256,start=0,stop=None,budget=None):
    """Return (actual body bytes, stats), charging no shared header here.

    budget is a BODY-only cap. build_archive subtracts its actual framed JSON.
    Supplying budget=None produces an unrestricted candidate for online FIFO.
    Static summary coarsens complete buckets if necessary, then (only when a
    single whole-history bucket still cannot fit) admits complete groups in
    chronological/channel order. Omitted groups confer no completeness.
    """
    if method not in METHODS:raise ValueError(method)
    h=np.asarray(high,dtype=bool);n,c=h.shape;u=_usable(eligible,n)
    stop=n if stop is None else int(stop);start=int(start)
    if not 0<=start<=stop<=n:raise ValueError('Invalid target range')
    a=np.asarray(atoms,dtype=ATOM)
    a=a[(a['t']>=start)&(a['t']<stop)]
    if len(a):a=a[np.lexsort((a['ch'],a['t']))]
    if len(a)!=int(h[start:stop].sum()):raise ValueError('High support and numeric records differ')
    if len(a) and not np.all(h[a['t'],a['ch']]):raise ValueError('Numeric record outside support')
    if np.any(h[~u]):raise ValueError('High support cannot include unusable decisions')
    width=max(1,int(width));empty=np.empty(0,GROUP)
    fulls=[_encode(a,h,u,start,stop,width,k,empty,()) for k in (1,2)]
    full=min(fulls,key=len)
    full_size=len(full)
    base_stats=dict(full_payload_bytes=full_size,input_atoms=len(a),start=start,stop=stop)
    if method=='full' or method.startswith('adaptive_') and (budget is None or full_size<=budget):
        return full,dict(base_stats,kind='full',selected_atoms=len(a),fill_atoms=0,unsaved_atoms=0,
                         width=width,groups=0,slack_bytes=0 if budget is None else budget-full_size)
    actual='bitmap_change_fill' if method=='adaptive_bitmap_fill' else 'coverage_fill' if method in ('adaptive_coverage_fill','adaptive_full_fill') else method
    bitmap=actual.startswith('bitmap_');fill_wanted=actual.endswith('_fill')
    kind=3 if bitmap else 4
    for attempt in range(40):
        if bitmap:groups=empty;ids=_changes(a,float(header.get('threshold',1.0)),width,start,h,stop)
        else:groups,ids=_summary(a,start,stop,width,c)
        payload=_encode(a,h,u,start,stop,width,kind,groups,ids)
        if budget is None or len(payload)<=budget or width>=max(1,stop-start) or bitmap:break
        width=min(max(1,stop-start),width*2)
    if budget is not None and len(payload)>budget:
        # Bitmap is atomic: decline its support service if the bitmap cannot fit.
        # Numeric selection cannot rescue an over-budget mandatory bitmap.
        if bitmap:
            cap=max(0,(budget-(len(payload)-len(ids)*ATOM.itemsize))//ATOM.itemsize)
            ids=ids[:cap];payload=_encode(a,h,u,start,stop,width,kind,groups,ids)
        else:
            # Whole complete groups are admitted, never partially described.
            accepted=[];chosen=[]
            for gr in groups:
                candidate=accepted+[gr]
                roles=[]
                for g in candidate:
                    if g['count']:
                        roles.extend(np.flatnonzero((a['ch']==g['ch'])&np.isin(a['t'],[g['first'],g['last'],g['minimum'],g['maximum']])))
                candids=np.unique(roles).astype(np.int64)
                trial=_encode(a,h,u,start,stop,width,kind,np.asarray(candidate,GROUP),candids)
                if len(trial)>budget:break
                accepted=candidate;chosen=candids
            groups=np.asarray(accepted,GROUP);ids=np.asarray(chosen,dtype=np.int64)
            payload=_encode(a,h,u,start,stop,width,kind,groups,ids)
    base_size=len(payload);remaining=np.setdiff1d(np.arange(len(a)),ids,assume_unique=True)
    fill_ids=np.empty(0,dtype=np.int64)
    if fill_wanted and (budget is None or len(payload)<=budget):
        count=len(remaining) if budget is None else min(len(remaining),max(0,(budget-len(payload))//ATOM.itemsize))
        # Uniform high-record time rank. Entirely label/query independent;
        # no failed-query record is preferentially restored.
        if count:fill_ids=remaining[np.linspace(0,len(remaining)-1,count,dtype=np.int64)]
        payload=_encode(a,h,u,start,stop,width,kind,groups,ids,fill_ids)
    stats=dict(base_stats,kind=actual,selected_atoms=len(ids)+len(fill_ids),fill_atoms=len(fill_ids),
               unsaved_atoms=len(a)-len(ids)-len(fill_ids),width=width,groups=len(groups),
               base_payload_bytes=base_size,slack_bytes=0 if budget is None else budget-len(payload))
    return payload,stats

def decode_payload(payload, header, method='coverage_summary', *,blob=b''):
    kind,start,stop,width,ng,ss,us,gs,ns,fs=BODY.unpack_from(payload)
    pos=BODY.size;parts=[]
    for size in (ss,us,gs,ns,fs):parts.append(payload[pos:pos+size]);pos+=size
    if pos!=len(payload):raise ValueError('Payload framing mismatch')
    supportb,ub,gb,nb,fb=parts;n=int(header['n_cycles']);c=len(header['channels'])
    usability=np.full(n,-1,dtype=np.int8)
    if us:usability[start:stop]=np.unpackbits(np.frombuffer(zlib.decompress(ub),np.uint8),bitorder='little')[:stop-start]
    groups=np.frombuffer(zlib.decompress(gb),GROUP).copy() if ng else np.empty(0,GROUP)
    if len(groups)!=ng:raise ValueError('Group count mismatch')
    support=None
    if kind==5:numeric=np.empty(0,ATOM)
    elif kind==1:numeric=codec.decode_soa(nb)
    elif kind==2:numeric=codec.decode_bitmap_numeric(nb,stop,c)
    else:numeric=np.frombuffer(nb,ATOM).copy()
    if fs:numeric=np.concatenate((numeric,np.frombuffer(fb,ATOM)))
    if len(numeric):
        numeric=numeric[np.lexsort((numeric['ch'],numeric['t']))]
        keys=numeric['t'].astype(np.uint64)*c+numeric['ch']
        if len(np.unique(keys))!=len(keys):raise ValueError('Duplicate numeric records')
    if kind in (1,2,3):
        support=np.full((n,c),-1,dtype=np.int8)
        if kind==3:support[start:stop]=np.unpackbits(np.frombuffer(zlib.decompress(supportb),np.uint8).reshape(c,-1),axis=1,bitorder='little')[:,:stop-start].T
        else:
            support[start:stop]=0
            support[numeric['t'],numeric['ch']]=1
    return Archive(blob,header,method,numeric,groups,support,usability,start,stop,width,
                   feasible=kind!=5,required_bytes=len(blob),stats={})

def decode_archive(blob):
    magic,version,size=FRAME.unpack_from(blob)
    if magic!=MAGIC or version!=1:raise ValueError('Invalid archive')
    head=json.loads(blob[FRAME.size:FRAME.size+size])
    return decode_payload(blob[FRAME.size+size:],head,head['archive_method'].strip(),blob=blob)

def build_archive(atoms,high,eligible,header,budget,method='coverage_summary',*,width=256,start=0,stop=None):
    cost=frame_bytes(header,method)
    payload,stats=encode_payload(atoms,high,eligible,header,method,width=width,start=start,stop=stop,
                                 budget=None if budget is None else int(budget)-cost)
    blob=frame_payload(payload,header,method)
    required=len(blob)
    if budget is not None and required>budget:
        # Persist a framed refusal, not the over-budget candidate. Required
        # bytes remain a cost result and confer no query evidence.
        end=len(high) if stop is None else int(stop)
        payload=BODY.pack(5,start,end,width,0,0,0,0,0,0)
        blob=frame_payload(payload,header,method)
        if len(blob)>budget:raise ValueError('Budget cannot hold the declared service header')
    ar=decode_archive(blob);ar.stats=stats;ar.required_bytes=required
    ar.stats['required_bytes']=required
    ar.stats['stored_bytes']=len(blob)
    return ar

def _state(ar,ch):
    if not hasattr(ar,'_state_cache'):ar._state_cache={}
    if ch in ar._state_cache:return ar._state_cache[ch]
    n=int(ar.header['n_cycles']);s=np.full(n,-1,dtype=np.int8)
    s[ar.usability==0]=0
    if ar.support is not None:s[ar.support[:,ch]>=0]=ar.support[:,ch][ar.support[:,ch]>=0]
    nums=ar.numeric[ar.numeric['ch']==ch]
    s[nums['t']]=1
    constraints=[]
    for gr in ar.groups[ar.groups['ch']==ch]:
        if not gr['flags']&1:continue
        lo,hi,count=int(gr['lo']),int(gr['hi']),int(gr['count'])
        if not count:s[lo:hi]=0;continue
        first,last=int(gr['first']),int(gr['last'])
        s[lo:first]=0;s[last+1:hi]=0
        s[[first,last,int(gr['minimum']),int(gr['maximum'])]]=1
        unknown=np.flatnonzero(s[lo:hi]<0)+lo
        required=count-int(np.count_nonzero(s[lo:hi]==1))
        if not 0<=required<=len(unknown):raise ValueError('Inconsistent retained group')
        if required==0:s[unknown]=0
        elif required==len(unknown):s[unknown]=1
        else:constraints.append((unknown,required))
    result=(s,constraints,nums);ar._state_cache[ch]=result
    return result

def query(ar,idx,ch):
    """Information-relative complete Boolean/first/report service.

    Exactness is relative to support + retained numeric + bucket count and
    extrema roles. Numeric score extrema additionally constrain unknown scores
    but cannot create an exact unretained float32 record.
    """
    ix=np.unique(np.asarray(idx,dtype=np.int64));n=int(ar.header['n_cycles'])
    if not 0<=int(ch)<len(ar.header['channels']) or np.any(ix<0) or np.any(ix>=n):raise ValueError('Out-of-service query')
    s,cons,nums=_state(ar,int(ch));mask=np.zeros(n,dtype=bool);mask[ix]=True
    known_positive=ix[s[ix]==1];possible=ix[s[ix]!=0]
    mincount=len(known_positive);maxcount=len(known_positive)
    constrained=np.zeros(n,dtype=bool);latest_forced=[]
    if len(known_positive):latest_forced.append(int(known_positive[0]))
    for unknown,required in cons:
        constrained[unknown]=True
        inside=unknown[mask[unknown]];outside=len(unknown)-len(inside)
        minimum=max(0,required-outside);maximum=min(required,len(inside))
        mincount+=minimum;maxcount+=maximum
        if minimum:
            # Earliest prefix that must contain a high. At most u-r unknown
            # cells can be low; this gives the latest compatible first.
            latest_forced.append(int(inside[len(unknown)-required]))
    free=ix[(s[ix]<0)&~constrained[ix]];maxcount+=len(free)
    answer='yes' if mincount else 'no' if maxcount==0 else 'unknown'
    earliest=int(possible[0]) if len(possible) else -1
    latest=min(latest_forced) if latest_forced else -1
    first_cert=answer=='yes' and earliest==latest
    witness=nums[np.isin(nums['t'],ix)]
    joint=first_cert and bool(np.any(witness['t']==earliest))
    report=maxcount==len(witness) and mincount==maxcount
    usable=ar.usability[ix]
    return dict(answer=answer,first_certified=bool(first_cert),certified_first=bool(first_cert),
                first_cycle=earliest if first_cert else -1,earliest_possible=earliest,
                latest_possible_first=latest,first_numeric_joint=bool(joint),
                complete_report=bool(report),numeric_count=len(witness),
                numeric_first=int(witness['t'][0]) if len(witness) else -1,
                min_high_count=int(mincount),max_high_count=int(maxcount),
                unusable_count=int(np.count_nonzero(usable==0)),
                usability_unknown_count=int(np.count_nonzero(usable<0)),
                usable_below_count=int(np.count_nonzero((usable==1)&(s[ix]==0))),
                numeric=witness,
                reason='complete' if report else 'first-with-numeric' if joint else
                       'support-only' if answer!='unknown' else 'incomplete-support')

def merge_archives(archives,header):
    """Logical union of disjoint retained chunks, no uncharged evidence.

    Caller must charge shared frame + each payload and its chunk directory.
    This helper only merges decoded contents for query evaluation.
    """
    n=int(header['n_cycles']);c=len(header['channels']);usable=np.full(n,-1,dtype=np.int8)
    support=np.full((n,c),-1,dtype=np.int8);groups=[];nums=[]
    for ar in archives:
        if not ar.feasible:continue
        size=len(ar.usability)
        if size>n:raise ValueError('Chunk extends beyond requested merge horizon')
        good=ar.usability>=0
        if np.any((usable[:size][good]>=0)&(usable[:size][good]!=ar.usability[good])):raise ValueError('Conflicting usability')
        usable[:size][good]=ar.usability[good]
        if ar.support is not None:
            known=ar.support>=0;support[:size][known]=ar.support[known]
        groups.append(ar.groups);nums.append(ar.numeric)
    g=np.concatenate(groups) if groups else np.empty(0,GROUP)
    a=np.concatenate(nums) if nums else np.empty(0,ATOM)
    if len(a):a=a[np.lexsort((a['ch'],a['t']))]
    return Archive(b'',header,'merged',a,g,support,usable,0,n,0)

def _compatible(ar,world,ch=0):
    """Independent finite support oracle, not using _state/query rules."""
    if ar.support is not None:
        z=ar.support[:,ch];known=z>=0
        if np.any(world[known]!=z[known]):return False
    if np.any(world[ar.usability==0]):return False
    for z in ar.numeric[ar.numeric['ch']==ch]:
        if not world[int(z['t'])]:return False
    for g in ar.groups[ar.groups['ch']==ch]:
        lo,hi=int(g['lo']),int(g['hi']);hits=np.flatnonzero(world[lo:hi])+lo
        if len(hits)!=int(g['count']):return False
        if len(hits) and (hits[0]!=g['first'] or hits[-1]!=g['last']):return False
        if len(hits) and (not world[g['minimum']] or not world[g['maximum']]):return False
    return True

def selfcheck():
    """Exhaustive support worlds; soundness and no avoidable refusal.

    Oracle enumerates support only. Exact numeric report is identifiable iff
    all possible support atoms are numerically retained: discarded window-last
    float32 values remain unconstrained even when score extrema coincide.
    """
    start=time.perf_counter();n=6;c=1
    header=dict(n_cycles=n,channels=['c0'],threshold=1.0)
    worlds=np.asarray(list(itertools.product((0,1),repeat=n)),dtype=np.int8)
    queries=[np.flatnonzero(z).astype(np.int64) for z in worlds]
    checks=[];false_cert=0;unnecessary=0;reports=0
    for wi,world in enumerate(worlds):
        h=world[:,None].astype(bool);u=np.ones(n,dtype=bool)
        # A genuine unavailable-input case must be semantically distinct.
        if wi%3==0 and not h[2,0]:u[2]=False
        ti,ch=np.nonzero(h);a=np.empty(len(ti),ATOM)
        a['t']=ti;a['ch']=ch;a['v']=ti//2;a['q']=1+ti*.25;a['x']=ti+.125
        configurations=[('coverage_summary',3,None),('coverage_summary',6,None),
                        ('coverage_fill',6,frame_bytes(header,'coverage_fill')+BODY.size+90),
                        ('bitmap_change',3,None),('bitmap_change_fill',6,None),('full',3,None),
                        ('full',3,frame_bytes(header,'full')+BODY.size)]
        for method,width,B in configurations:
            ar=build_archive(a,h,u,header,B,method,width=width)
            if B is not None:assert ar.size<=B
            restored=decode_archive(ar.blob)
            assert restored.numeric.tobytes()==ar.numeric.tobytes()
            possible=worlds[np.asarray([_compatible(restored,w) for w in worlds])]
            assert len(possible)>0
            for ix in queries:
                r=query(restored,ix,0)
                has=possible[:,ix].any(1) if len(ix) else np.zeros(len(possible),bool)
                expected='yes' if has.all() else 'no' if not has.any() else 'unknown'
                firsts=[int(ix[np.flatnonzero(w[ix])[0]]) for w in possible if w[ix].any()]
                certfirst=bool(has.all() and len(set(firsts))==1)
                wrong=r['answer']!='unknown' and r['answer']!=expected
                wrong|=r['first_certified'] and (not certfirst or r['first_cycle']!=firsts[0])
                avoid=r['answer']=='unknown' and expected!='unknown'
                avoid|=not r['first_certified'] and certfirst
                if wrong:raise AssertionError(('false certificate',wi,method,ix.tolist(),r,expected,firsts))
                if avoid:raise AssertionError(('avoidable unknown',wi,method,ix.tolist(),r,expected,firsts))
                retained=set(int(t) for t in restored.numeric['t'])
                patterns={tuple(int(t) for t in ix[w[ix].astype(bool)]) for w in possible}
                certreport=len(patterns)==1 and all(t in retained for t in next(iter(patterns)))
                if r['complete_report']!=certreport:raise AssertionError(('report completeness',wi,method,ix,r,patterns,retained))
                false_cert+=int(wrong);unnecessary+=int(avoid);reports+=int(certreport)
                checks.append((wi,method,len(ix),expected,certfirst,certreport))
    # Positive witness outside separately complete ranges: Q={1,2,3},
    # known-negative 1,2 and retained high 3 must certify first=3.
    a=np.empty(1,ATOM);a[0]=(3,0,0,2.,3.)
    support=np.full((n,1),-1,np.int8);support[1:3,0]=0
    ar=Archive(b'',header,'constructive',a,np.empty(0,GROUP),support,np.full(n,-1,np.int8),0,n,0)
    r=query(ar,[1,2,3],0);assert r['first_numeric_joint'] and r['first_cycle']==3
    # Usability zero and observed-low zero give the same support answer but
    # distinct billed metadata and user-facing interpretation.
    h=np.zeros((n,1),bool);u=np.ones(n,bool);u[2]=False
    ar=build_archive(np.empty(0,ATOM),h,u,header,None,'full')
    rr=query(ar,[1,2],0)
    assert rr['answer']=='no' and rr['unusable_count']==1 and rr['usable_below_count']==1
    # Absolute-time chunk decode + merge must retain no future evidence.
    h=np.zeros((n,1),bool);h[[1,4],0]=True
    a=np.empty(2,ATOM);a[0]=(1,0,0,2.,1.);a[1]=(4,0,1,3.,4.)
    chunks=[build_archive(a,h,np.ones(n,bool),header,None,'full',start=l,stop=r) for l,r in [(0,3),(3,6)]]
    merged=merge_archives(chunks,header)
    assert query(merged,np.arange(n),0)['complete_report']
    prefix=merge_archives(chunks[:1],header)
    assert query(prefix,[4],0)['answer']=='unknown'
    result=dict(support_worlds=len(worlds),archive_conditions=len(worlds)*len(configurations),
                interval_set_queries=len(checks),false_certificates=false_cert,
                unnecessary_unknowns=unnecessary,complete_reports=reports,
                explicit_cases=['empty','nonempty negative','partial coverage','unavailable input',
                                'positive outside complete range','expired/future suffix','absolute chunk merge'],
                elapsed_seconds=time.perf_counter()-start,
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    out=Path(__file__).resolve().parents[1]/'results/revision_review_20261023/core_semantic_audit.json'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
    return result

if __name__=='__main__':selfcheck()

