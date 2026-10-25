"""Nature-style vector figures from executed review-revision tables.

No plotted quantity is transcribed from an image. SciencePlots' MIT-licensed
science/nature styles are combined with explicit Arial, physical print size,
and exact source numerator/denominator CSVs. Native raster backup is 1200 dpi.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, sys
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'results/revision_review_20261023';OUT=R/'artwork'
OUT.mkdir(parents=True,exist_ok=True)
os.environ['MPLCONFIGDIR']=str(ROOT/'temp/mpl_review_20261023')
from figstyle import apply_house_style,audit,mm
import numpy as np
import pandas as pd
from PIL import Image
from matplotlib.font_manager import findfont
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.transforms import Bbox

plt=apply_house_style(styles=('science','no-latex','nature'),fontsize=7)
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial'],
    'mathtext.fontset':'dejavusans','font.size':7,'axes.labelsize':7,
    'axes.titlesize':7,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7,
    'axes.linewidth':.6,'axes.spines.top':False,'axes.spines.right':False,
    'xtick.direction':'out','ytick.direction':'out','xtick.top':False,'ytick.right':False,
    'xtick.major.size':2.8,'ytick.major.size':2.8,'xtick.minor.visible':False,
    'ytick.minor.visible':False,'savefig.bbox':None,'savefig.pad_inches':0,
    'pdf.fonttype':42,'svg.fonttype':'none','figure.facecolor':'white','axes.facecolor':'white'})
COLORS=['#36658C','#BB643A','#2A8576','#786494']
STYLES=['-','--','-.',':'];MARKERS=['o','s','^','D']
ORDER=['full','bitmap_change','bitmap_change_fill','coverage_summary','coverage_fill','adaptive_coverage_fill']
NAMES=['Complete archive','Bitmap + change','Bitmap + fill','Coverage summary','Coverage + fill','Full if fits']

def source_hashes(paths):
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def geometry(fig,axes):
    fig.canvas.draw();renderer=fig.canvas.get_renderer();canvas=fig.bbox
    text=[];seen=set();clipped=[];overlap=[];cross=[];spine=[]
    for t in fig.findobj(match=Text):
        if id(t) in seen or not t.get_visible() or not t.get_text().strip():continue
        seen.add(id(t));box=t.get_window_extent(renderer)
        if not np.isfinite(box.extents).all() or box.width==0 or box.height==0:continue
        record=dict(text=t.get_text(),font_pt=float(t.get_fontsize()),bbox_pixels=box.extents.tolist())
        text.append((record,box))
        if box.x0<canvas.x0-.1 or box.y0<canvas.y0-.1 or box.x1>canvas.x1+.1 or box.y1>canvas.y1+.1:clipped.append(record)
    for i,(r,b) in enumerate(text):
        for rr,bb in text[i+1:]:
            z=Bbox.intersection(b,bb)
            if z is not None and z.width>.25 and z.height>.25:overlap.append([r['text'],rr['text']])
        for j,ax in enumerate(axes):
            for name,s in ax.spines.items():
                if s.get_visible() and s.get_path().transformed(s.get_transform()).intersects_bbox(b,filled=False):spine.append([r['text'],j,name])
            clippedbox=Bbox.intersection(b,ax.bbox)
            if clippedbox is None:continue
            for line in ax.lines:
                if line.get_visible() and line.get_path().transformed(line.get_transform()).intersects_bbox(clippedbox,filled=False):cross.append([r['text'],j,'line'])
    return dict(all_text=[r for r,b in text],text_text_overlaps=overlap,text_data_intersections=cross,
                text_spine_intersections=spine,clipped_text=clipped,ok=not(overlap or cross or spine or clipped))

def export(fig,stem,axes,sources):
    g=geometry(fig,axes);house=audit(fig,max_width_mm=183,verbose=False)
    (OUT/f'{stem}_geometry_working.json').write_text(json.dumps(g,indent=2),encoding='utf-8')
    assert g['ok'],json.dumps(g,indent=2)
    assert house['ok'],house
    assert all(7<=r['font_pt']<=8 for r in g['all_text'])
    assert fig.get_size_inches()[1]*25.4<=170
    paths={}
    for ext in ('pdf','svg','png'):
        path=OUT/f'{stem}.{ext}';fig.savefig(path,dpi=1200,bbox_inches=None,facecolor='white');paths[ext]=str(path)
    preview=OUT/f'{stem}_preview.png';fig.savefig(preview,dpi=150,bbox_inches=None,facecolor='white')
    pdf=Path(paths['pdf']).read_bytes();svg=Path(paths['svg']).read_text(encoding='utf-8')
    box=re.search(rb'/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]',pdf)
    dimensions=[(float(box[3])-float(box[1]))*25.4/72,(float(box[4])-float(box[2]))*25.4/72]
    assert abs(dimensions[0]-183)<.001
    assert '<image' not in svg and b'/Subtype /Image' not in pdf and b'/Subtype /Type3' not in pdf
    with Image.open(paths['png']) as im:pixels=list(im.size);dpi=list(im.info['dpi'])
    assert min(dpi)>1199
    g.update(files=paths,preview=str(preview),pdf_physical_mm=dimensions,raster_pixels=pixels,raster_dpi=dpi,
             font_file=findfont('Arial',fallback_to_default=False),svg_editable_text_elements=svg.count('<text'),
             svg_raster_images=svg.count('<image'),pdf_raster_images=pdf.count(b'/Subtype /Image'),
             pdf_type3_fonts=pdf.count(b'/Subtype /Type3'),house_style=house,source_hashes=source_hashes(sources),
             source_style='https://github.com/garrettj403/SciencePlots',
             reference_commit='b9b16959570bd2fbc9ff5118bacc423c3bddd592',
             vision_review='pending actual preview inspection')
    (OUT/f'{stem}_geometry.json').write_text(json.dumps(g,indent=2,default=str),encoding='utf-8')
    plt.close(fig)
    return dict(stem=stem,ok=True,files=paths,preview=str(preview),dimensions_mm=dimensions)

def panel(fig,x,y,letter,title):
    fig.text(x-.060,y,letter,fontsize=8,fontweight='bold',va='bottom')
    fig.text(x,y,title,fontsize=7,fontweight='bold',va='bottom')

def figure1():
    source=R/'all_static_costs.csv';tasksource=R/'static_task_summary.csv'
    costs=pd.read_csv(source);tasks=pd.read_csv(tasksource)
    complete=costs[['dataset','unit','backbone','cadence','full_bytes']].drop_duplicates()
    assert len(complete)==116
    groups=[('SMD','coarse','Coarse SMD (56 fits)',COLORS[0],'-'),
            ('SMD','fine','Fine SMD (56 fits)',COLORS[1],'--')]
    fig=plt.figure(figsize=(mm(183),mm(110)))
    left=fig.add_axes([.105,.315,.345,.455]);right=fig.add_axes([.675,.315,.280,.455])
    plotted=[];handles=[]
    for ds,cadence,label,color,ls in groups:
        z=complete[(complete.dataset==ds)&(complete.cadence==cadence)].sort_values('full_bytes')
        assert len(z)==56
        x=z.full_bytes.to_numpy()/1024;y=np.arange(1,len(z)+1)/len(z)
        left.step(np.r_[1,x],np.r_[0,y],where='post',color=color,lw=1.05,ls=ls)
        handles.append(Line2D([0],[0],color=color,lw=1.05,ls=ls,label=label))
        for rank,(_,r) in enumerate(z.iterrows(),1):
            plotted.append(dict(panel='a',dataset=ds,cadence=cadence,unit=r.unit,backbone=r.backbone,
                                method='full',metric='empirical cumulative fraction',numerator=rank,
                                denominator=len(z),x_kib=r.full_bytes/1024,value=rank/len(z)))
    esa=complete[complete.dataset=='ESA'];assert len(esa)==4
    left.plot(esa.full_bytes/1024,np.full(4,-.045),'|',color='#454545',ms=6,mew=1.0,ls='none')
    handles.append(Line2D([0],[0],color='#454545',marker='|',ms=6,mew=1.,ls='none',label='ESA (4 histories; rug)'))
    for _,r in esa.iterrows():
        plotted.append(dict(panel='a',dataset='ESA',cadence=r.cadence,unit=r.unit,backbone=r.backbone,
                            method='full',metric='individual storage rug',numerator=np.nan,denominator=4,
                            x_kib=r.full_bytes/1024,value=-.045))
    left.set_xscale('log',base=2);left.set_xlim(1,4096);left.set_ylim(-.08,1.03)
    left.set_xticks([1,4,16,64,256,1024,4096],['1','4','16','64','256','1,024','4,096'])
    left.set_yticks([0,.25,.5,.75,1],['0','0.25','0.50','0.75','1.00'])
    left.set_xlabel('Complete encoded history (KiB)',labelpad=8)
    left.set_ylabel('Fraction of SMD histories',labelpad=7)
    for cap in (64,256,1024):
        left.axvline(cap,color='#A9ADB1',ls=(0,(2,3)),lw=.55,zorder=-5)
        left.text(cap,1.07,str(cap),transform=left.get_xaxis_transform(),ha='center',va='bottom',fontsize=7)
    fig.text(.105,.850,'Illustrative capacities (KiB)',fontsize=7,va='bottom')
    panel(fig,.105,.925,'a','Complete-record storage')
    panel(fig,.675,.925,'b','Fine SMD, 256 KiB')
    tx=tasks[(tasks.dataset=='SMD')&(tasks.cadence=='fine')&(tasks.budget==262144)&(tasks.family=='full_annotated')]
    for k,method in enumerate(ORDER):
        z=tx[tx.method==method];assert len(z)==2,(method,len(z))
        den=int(z.positive_queries.sum());assert den==2329
        for offset,metric,color,marker in [(-.11,'joint_first',COLORS[0],'o'),(.11,'complete_positive',COLORS[1],'s')]:
            num=int(z[metric].sum());value=num/den
            right.plot(value,k+offset,marker=marker,ms=4,lw=0,ls='none',mew=.7,
                       mfc=color if marker=='o' else 'white',mec=color,zorder=3)
            plotted.append(dict(panel='b',dataset='SMD',cadence='fine',unit='pooled',backbone='pca+ridge',
                                method=method,metric=metric,numerator=num,denominator=den,
                                x_kib=256,value=value))
    right.set_yticks(range(6),NAMES);right.set_ylim(5.65,-.65);right.set_xlim(-.03,1.04)
    right.set_xticks([0,.25,.5,.75,1],['0','0.25','0.50','0.75','1.00'])
    right.set_xlabel('Positive queries answered',labelpad=8)
    right.tick_params(axis='y',length=0,pad=6)
    fig.legend(handles=handles,loc='lower left',bbox_to_anchor=(.105,.035),borderaxespad=0,
               ncol=1,handlelength=2.6,labelspacing=.6)
    outcomes=[Line2D([0],[0],color=COLORS[0],marker='o',ms=4,ls='none',label='Certified first + numeric record'),
              Line2D([0],[0],color=COLORS[1],marker='s',ms=4,mfc='white',ls='none',label='Complete numeric report')]
    fig.legend(handles=outcomes,loc='lower left',bbox_to_anchor=(.675,.065),borderaxespad=0,
               ncol=1,handlelength=1.1,labelspacing=.7)
    pd.DataFrame(plotted).to_csv(OUT/'figure1_source_data.csv',index=False)
    return export(fig,'figure1_storage_task',[left,right],[source,tasksource])

def figure2():
    source=R/'online_age_summary.csv';summary=R/'online_summary_b1024.csv'
    z=pd.read_csv(summary)
    assert len(z)==32,'Wait for complete shared online replay before plotting'
    ages=pd.read_csv(source)
    selected=ages[(ages.dataset=='SMD')&(ages.unit=='machine-3-4')&
                  (ages.backbone=='ridge')&(ages.cadence=='fine')&(ages.budget==262144)]
    policies=['full','bitmap_change','coverage_summary','adaptive']
    names=['Complete archive','Bitmap + change','Coverage summary','Adaptive full / summary']
    age_order=['0–1%','1–25%','25–50%','50–75%','75–100%']
    assert len(selected)==20
    assert set(selected.method)==set(policies)
    assert set(selected.age_group)==set(age_order)
    expected_den=[25,37,38,24,10]
    fig=plt.figure(figsize=(mm(183),mm(110)))
    left=fig.add_axes([.105,.335,.365,.455]);right=fig.add_axes([.600,.335,.365,.455])
    fig.text(.105,.930,'Fine SMD · machine-3-4 · ridge · 256 KiB',fontsize=7,va='bottom')
    panel(fig,.105,.845,'a','First evidence with numeric record')
    panel(fig,.600,.845,'b','Complete numeric report')
    plotted=[];handles=[]
    for k,(policy,name,color,ls,marker) in enumerate(zip(policies,names,COLORS,STYLES,MARKERS)):
        zz=selected[selected.method==policy].set_index('age_group').loc[age_order]
        assert list(zz.positive_queries)==expected_den
        assert int(zz.positive_queries.sum())==134
        total=z[(z.dataset=='SMD')&(z.unit=='machine-3-4')&(z.backbone=='ridge')&
                (z.cadence=='fine')&(z.budget==262144)&(z.method==policy)]
        assert len(total)==1 and int(total.iloc[0].block)==1024
        for field in ('queries','positive_queries','joint_first','complete_positive'):
            assert int(zz[field].sum())==int(total.iloc[0][field]),(policy,field)
        for ax,metric,panel_name in [(left,'joint_first','a'),(right,'complete_positive','b')]:
            num=zz[metric].to_numpy(dtype=int);den=zz.positive_queries.to_numpy(dtype=int)
            values=np.divide(num,den,out=np.full(den.shape,np.nan,dtype=float),where=den>0)
            # A small horizontal offset keeps equal results visible without changing rates.
            xx=np.arange(5)+(k-1.5)*.065
            ax.plot(xx,values,color=color,ls=ls,lw=.85,marker=marker,ms=3.7,mew=.75,
                    mfc='white' if k%2 else color,clip_on=False,zorder=3+k)
            for j,(age,n,d,v) in enumerate(zip(age_order,num,den,values)):
                plotted.append(dict(panel=panel_name,dataset='SMD',unit='machine-3-4',backbone='ridge',
                                    cadence='fine',budget=262144,block=1024,method=policy,age_group=age,
                                    metric=metric,numerator=int(n),denominator=int(d),value=float(v),
                                    x_category=j,x_display=float(xx[j])))
        handles.append(Line2D([0],[0],color=color,ls=ls,lw=.85,marker=marker,ms=3.7,mew=.75,
                              mfc='white' if k%2 else color,label=name))
    for ax in (left,right):
        ax.set_xlim(-.35,4.35);ax.set_ylim(0,1)
        ax.set_xticks(range(5),age_order)
        ax.set_yticks([0,.25,.5,.75,1],['0','0.25','0.50','0.75','1.00'])
        ax.set_xlabel('Query age (% of observed prefix)',labelpad=8)
        ax.set_ylabel('Fraction of positive queries',labelpad=7)
    fig.legend(handles=handles,loc='lower left',bbox_to_anchor=(.105,.055),borderaxespad=0,
               ncol=2,handlelength=2.7,columnspacing=2.6,labelspacing=.9)
    pd.DataFrame(plotted).to_csv(OUT/'figure2_source_data.csv',index=False)
    return export(fig,'figure2_online_age',[left,right],[source,summary])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--figure1',action='store_true');ap.add_argument('--figure2',action='store_true')
    ap.add_argument('--record-visual-review',action='store_true',help='Only after both generated previews have actually been inspected')
    args=ap.parse_args()
    if args.record_visual_review:
        metadata=dict(style='Nature-style scientific presentation; SciencePlots + explicit Arial geometry',
                      width_mm=183,height_mm=110,ordinary_font_pt=7,panel_letter_pt=8,
                      vector_formats=['PDF (embedded TrueType)','SVG (editable text)'],native_raster_dpi=1200,
                      preview_dpi=150,palette=COLORS,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      inference='Descriptive display; no independence, significance, or deployment-prevalence inference',figures=[])
        for stem in ['figure1_storage_task','figure2_online_age']:
            path=OUT/f'{stem}_geometry.json';g=json.loads(path.read_text(encoding='utf-8'))
            assert g['ok'] and g['house_style']['ok']
            preview=Path(g['preview'])
            g['vision_review']=dict(status='pass',mechanism='Actual preview inspection with native view_image',
                inspected_preview_sha256=hashlib.sha256(preview.read_bytes()).hexdigest(),
                checks=['No overlapping text','No text crossing data lines or spines','No clipped labels',
                        'Legends outside data','Readable Arial text at the stated physical canvas'],
                scope='Visual layout only; values verified from source CSVs, not read from the image')
            path.write_text(json.dumps(g,indent=2,default=str),encoding='utf-8')
            metadata['figures'].append(dict(stem=stem,geometry_report=path.name,
                geometry_ok=g['ok'],visual_qa=g['vision_review'],physical_mm=g['pdf_physical_mm'],
                raster_pixels=g['raster_pixels'],raster_dpi=g['raster_dpi'],source_hashes=g['source_hashes'],
                files={Path(p).name:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in g['files'].values()}))
        (OUT/'artwork_metadata.json').write_text(json.dumps(metadata,indent=2,default=str),encoding='utf-8')
        print(json.dumps(dict(visual_qa='pass',metadata=str(OUT/'artwork_metadata.json')),indent=2));return
    results=[]
    if not args.figure2:results.append(figure1())
    if args.figure2 or not args.figure1:results.append(figure2())
    print(json.dumps(results,indent=2),flush=True)

if __name__=='__main__':main()
