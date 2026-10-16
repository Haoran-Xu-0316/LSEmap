"""Finite source-platform feasibility review of SAW's remaining lower stair.

Complete223 native remains read-only. Source diagrams are historic and do not
identify every incoming/outgoing riser or intermediate platform datum. The
straight source-section candidate never mutates the current shared model.
"""
from pathlib import Path
import hashlib,json,sys,math
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/saw-circulation224'
DATA=ROOT/'data/collections/saw-circulation224'
BASE=ROOT/'result/blender/LSE_campus_detailed_v223.blend'
SHA='ebe14c658cacb9ef4e19b0fbfd8683610bf53c565f161837d329dfbd0cd9d88b'
GUIDE=ROOT/'data/documents/saw_occupants_guide_2014.pdf'
LEVELS=[0.,3.45,8.1,11.1,14.1,18.]
ANCHORS=np.array([[-65.223399,-15.905616],[-84.252182,28.425],[-55.301,36.609104]])
sys.path.insert(0,str(ROOT/'web/tools'))
def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(value,indent=2)+'\n')
def world(points):
 p=np.array(points);a,b,c=ANCHORS
 return a+(p[:,0:1]-145)/1200*(b-a)+(p[:,1:2]-400)/785*(c-b)
def pixels(points):
 matrix=np.column_stack(((ANCHORS[1]-ANCHORS[0])/1200,(ANCHORS[2]-ANCHORS[1])/785))
 return (np.asarray(points)-ANCHORS[0])@np.linalg.inv(matrix).T+np.array([145,400])

def source_platform_candidate():
 import pdfplumber
 from shapely.geometry import Polygon,mapping
 from shapely.geometry.polygon import orient
 from shapely.ops import unary_union
 from PIL import Image,ImageDraw
 registration=json.loads((ROOT/'result/blender/saw-floors216/registration.json').read_text())
 source=json.loads((ROOT/'result/blender/saw-circulation218/source-section-correspondence.json').read_text())
 # One finite diagnostic only: all identifiable second-to-third spans, with
 # two genuinely flat inter-run joins. No curved-ribbon compression, convex
 # hull fill, source clipping, arbitrary inset or changed lift position.
 selected=[(30,[5989,5988,5987,5985,5984,5983,5982,5981,5986]),(30,[5996,5997,5998]),(29,[1763,1762,1761,1760,1759,1758,1757,1756])]
 groups=[];proof=[];last=None
 with pdfplumber.open(GUIDE)as pdf:
  for page_number,indices in selected:
   page=pdf.pages[page_number-1];factor=1501/page.width;reg=registration[str(page_number)];sections=[];meta=[]
   for index in indices:
    line=page.lines[index];raw=np.array(line['pts']);p=(raw@reg['matrix']+reg['offset'])*factor;q=world(p)
    if last is not None and np.linalg.norm(last[0]-q[1])+np.linalg.norm(last[1]-q[0])<np.linalg.norm(last[0]-q[0])+np.linalg.norm(last[1]-q[1]):q=q[::-1];p=p[::-1]
    last=q;sections.append(q);meta.append(dict(page=page_number,lineIndex=index,pdfEndpoints=raw.tolist(),registeredPixelEndpoints=p.tolist(),worldEndpoints=q.tolist(),publishedSpanMetres=float(np.linalg.norm(q[1]-q[0])),lineWidth=line['linewidth'],dash=line.get('dash')))
   groups.append(sections);proof.append(dict(page=page_number,indices=indices,sections=meta))
 intervals=sum(len(g)-1 for g in groups);rise=3/intervals;surfaces=[];step=0;invalid=[]
 for gi,g in enumerate(groups):
  for i,(a,b)in enumerate(zip(g,g[1:])):
   poly=Polygon([a[0],a[1],b[1],b[0]])
   if not poly.is_valid:invalid.append(dict(group=gi,index=i,kind='source_tread_interval'))
   step+=1;surfaces.append(dict(group=gi,kind='source_tread_interval',index=i,top=8.1+rise*step,bottom=8.1+rise*(step-1)-.18,polygon=poly))
  if gi<len(groups)-1:
   a=g[-1];b=groups[gi+1][0];poly=Polygon([a[0],a[1],b[1],b[0]])
   if not poly.is_valid:invalid.append(dict(group=gi,kind='flat_join'))
   surfaces.append(dict(group=gi,kind='flat_join',top=8.1+rise*step,bottom=8.1+rise*step-.18,polygon=poly))
 # Invalid quadrilaterals are recorded, never repaired into a more convenient
 # footprint. Only valid source-defined surfaces enter numerical checks.
 valid=[s for s in surfaces if s['polygon'].is_valid]
 vectors=json.loads((ROOT/'result/blender/saw-floors216/vectors.json').read_text());factor=1501/vectors['32']['pageSize'][0]
 cabins=[Polygon(world(np.array(next(c for c in vectors['32']['candidates']if c['index']==i)['pts'][:-1])*factor))for i in registration['32']['sourceControlCurveIndices']];lifts=unary_union(cabins)
 overlaps=[];lift_hits=[];adjacency=[]
 for i,a in enumerate(valid):
  area=a['polygon'].intersection(lifts).area
  if area>.0001:lift_hits.append(dict(surface=i,kind=a['kind'],areaM2=area))
  if i+1<len(valid):adjacency.append(dict(a=i,b=i+1,planDistanceMetres=a['polygon'].distance(valid[i+1]['polygon'])))
  for j,b in enumerate(valid[i+1:],i+1):
   area=a['polygon'].intersection(b['polygon']).area
   if area>.001:
    lower,upper=sorted([a,b],key=lambda s:s['top']);gap=upper['bottom']-lower['top']
    overlaps.append(dict(a=i,b=j,kindA=a['kind'],kindB=b['kind'],sameLevel=abs(a['top']-b['top'])<.00001,projectedAreaM2=area,verticalGapMetres=gap))
 widths=[s['publishedSpanMetres']for g in proof for s in g['sections']]
 goings=[]
 for g in groups:
  for a,b in zip(g,g[1:]):
   direction=a[1]-a[0];direction/=np.linalg.norm(direction);normal=np.array([-direction[1],direction[0]])
   goings.append(abs(float(np.dot(b.mean(0)-a.mean(0),normal))))
 save('source-section-correspondence.json',dict(sourceGuideSha256=hashlib.sha256(GUIDE.read_bytes()).hexdigest(),flight='2-to-3 finite full-section flat-platform diagnostic',groups=proof,additionalLinesNotIncludedIn218=[dict(page=30,lineIndex=5986),dict(page=29,lineIndex=1762),dict(page=29,lineIndex=1763)],interpretation='Unaccepted pairing. Short end spans may be cut by publication breaks; line spans cannot be asserted as measured clear width or recovered whole-storey riser schedules.'))
 low_headroom=[r for r in overlaps if r['kindA']==r['kindB']=='source_tread_interval'and r['verticalGapMetres']<2.1]
 report=dict(nonlocalTreadHeadroomConflictCount=len(low_headroom),minimumNonlocalTreadGapMetres=min(r['verticalGapMetres']for r in low_headroom),status='rejected_before_native_authoring',candidate='Untrimmed source-line intervals plus two constant-height quadrilateral platforms',sourceIntervals=intervals,diagnosticRiserHeightMetres=rise,flatPlatformCount=2,invalidSourceQuadrilaterals=invalid,sourceSpanMinimumMetres=min(widths),medianParallelGoingMetres=float(np.median(goings)),minimumNormalStationSpacingMetres=min(goings),sourceLiftOverlap=lift_hits,interSurfaceOverlaps=overlaps,adjacency=adjacency,accepted=False,noSourceCropping=True,noLiftMovement=True,noConvexHullJoins=True,completeNativeNotModified=True)
 save('finite-platform-feasibility.json',report)
 # Register both adjacent plans to one lift-fixed coordinate system. Draw
 # source-defined intervals blue, flat joins orange, and lift cabins dark.
 sheet=Image.new('RGB',(1500,850),'white');d=ImageDraw.Draw(sheet)
 for k,page in enumerate([30,29]):
  im=Image.open(ROOT/f'data/previews/saw_occupants_guide_2014_p{page}.png').convert('RGB');r=registration[str(page)];inverse=np.linalg.inv(r['matrix']);offset=-np.array(r['offset'])*factor@inverse
  im=im.transform(im.size,Image.Transform.AFFINE,(inverse[0,0],inverse[1,0],offset[0],inverse[0,1],inverse[1,1],offset[1]),Image.Resampling.BICUBIC);dd=ImageDraw.Draw(im)
  for s in valid:
   ring=pixels(s['polygon'].exterior.coords);dd.line([tuple(p)for p in ring],fill='#c97000'if s['kind']=='flat_join'else'#17678d',width=2)
  for cabin in cabins:dd.line([tuple(p)for p in pixels(cabin.exterior.coords)],fill='#222c36',width=3)
  im=im.crop((570,420,820,635)).resize((740,640));sheet.paste(im,(k*750,100));d.text((k*750+10,12),f'2014 level{32-page}: REJECTED source platform pairing',fill='#aa2222');d.text((k*750+10,40),'BLUE untrimmed riser intervals; ORANGE flat platform joins',fill='black')
 sheet.save(DATA/'finite-platform-source-proof.png')
 print('SAW224_FINITE_PLATFORM_REJECTED',report,flush=True)
 return report,cabins

def finalize(report,cabins):
 from shapely.geometry import Polygon
 from shapely.ops import unary_union
 retained=json.loads((OUT/'retained-native-conflicts.json').read_text());assert retained['baselineSha256']==SHA
 conflicts=retained['conflicts'];assert retained['actualLowerTreads']==120 and len(conflicts)==32
 levels=[]
 for flight,(a,b)in enumerate(zip(LEVELS,LEVELS[1:])):
  c=[r for r in conflicts if a<r['top']<=b+.00001];levels.append(dict(fromLevel=flight,toLevel=flight+1,conflictCount=len(c),summedOverlapM2=sum(r['areaM2']for r in c),nativeModified=False))
 save('retained-native-conflicts.json',dict(baselineSha256=SHA,actualLowerTreads=120,remainingConflicts=32,solvedThisRound=0,byFlight=levels,conflicts=conflicts,upperST04Preserved=True))
 refs=json.loads((ROOT/'data/collections/saw-circulation223/sources.json').read_text());catalogue=json.loads((ROOT/'data/catalogue.json').read_text())['records']
 for id in ['exteriors:saw_archdaily_029','exteriors:saw_archdaily_030','exteriors:saw_archdaily_035']:
  r=next(r for r in catalogue if r['id']==id);refs.append(dict(path=r['local_file'],sourceUrl=r['url'],parentUrl=r['parent_url'],sha256=r['sha256'],sourceType='Architect published design drawing, not certified as-built',publicationDate='2014-10-14',current2026ConditionEstablished=False))
 (DATA/'sources.json').write_text(json.dumps(refs,indent=2)+'\n')
 save('audit.json',dict(version=224,status='not_accepted_no_component',auditOnly=True,baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=None,componentSha256=None,addedObjects=[],archivedObjects=[],changedObjects=[],interiorCollection='SAW_PUBLIC_INTERIOR_study',replacesInteriorCollection=None,verification=json.loads((OUT/'native-preservation.json').read_text()),finiteCandidate=report,conflictProof='retained-native-conflicts.json',sourceCorrespondence='source-section-correspondence.json',sourceRefs=refs,sourceProofs=['data/collections/saw-circulation224/architect-level2-3-core.png','data/collections/saw-circulation224/finite-platform-source-proof.png'],findings=['Remaining32native cabin conflicts belong to three lower connections:1-to-2 has15,2-to-3 has6,4-to-5 has11; ground-to-first and third-to-fourth have none.','Architect detailed plans identifyST03, its central Void and changing turns. They do not supply readable per-riser numbers or intermediate landing datums.','Full source enumeration adds page30line5986 and page29lines1762/1763 to the previous2-to-3 excerpt. The final two spans taper to approximately1.59m/0.73m and may be publication-clipped; their ends cannot be adopted as clear stair boundaries.','Literal source quadrilaterals for two horizontal platforms clear the cabins, but the uncut2-to-3 pairing still has6nonlocal tread overlaps below2.1m headroom, lowest1.0553m; second platform overlaps two known tread regions. No source span is cropped to force acceptance.','Official board confirms social rest landings and a separateST04 upper spiral. It gives no labelled correspondence or elevations for these lowerST03turns.'],nextRequiredEvidence='Floor-numbered ST03general arrangement showing both incoming/outgoing runs, up/down arrows and intermediate-platform levels, or a floor-labelled continuous walk-through/registerable built image that identifies the2-to-3 U-turn and4-to-5 inside corner. A drawing that names each riser across publication cut lines is sufficient; generic atrium photographs are not.',limitations=['2014/2015design and historical building sources do not establish2026current condition.','No new geometry is accepted. Widths, rise allocations and candidate joins are diagnostics only.','Native lower32conflicts remain;223ST04geometry, UVs, materials, modifiers and display ownership are unchanged.','No reference photograph is used as a public texture.']))
 (OUT/'actual-lower-treads.tmp.json').unlink(missing_ok=True)
 print('SAW224_AUDIT_ONLY_COMPLETE',levels,flush=True)

if __name__=='__main__':
 finalize(*source_platform_candidate())
