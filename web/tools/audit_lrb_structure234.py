"""Read-only LRB234 slab/window registration diagnosis on accepted233.

Distinguish an actual glass/slab mesh intersection from a floor edge visible
behind glass. Source elevation spot heights are not invented finished-floor
levels. No floor,helix,lift,window or material candidate is manufactured.
"""
from pathlib import Path
import sys,json,hashlib,math,collections
sys.dont_write_bytecode=True
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/lrb-structure234';DATA=ROOT/'data/collections/lrb-structure234'
BASE=ROOT/'result/blender/LSE_campus_detailed_v233.blend';SHA='b1d01b4b74a7f9e33d9bab25e73f51f39361659b9236ca98c34056137d8b6660'
PANES=['LRB233_broad_window_reflective_glass','LRB233_Watkins_reflective_glass'];SLAB='LRB168__LRB_library_floor_slabs'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import update_scene
from refine_plaza_environment231 import state
from refine_streets230 import components
from refine_lrb_structure221 import passage_measurements

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def tree(o):return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices)for p in o.data.polygons])
def measure():
 slab=bpy.data.objects[SLAB];st=tree(slab);reg=json.loads((ROOT/'result/blender/site_geometry.json').read_text());ring=next(b['rings'][0]for b in reg['buildings']if b['code']=='LRB');u=(Vector((*ring[13],0))-Vector((*ring[0],0))).normalized();n=Vector((u.y,-u.x,0));rows=[]
 for name in PANES:
  o=bpy.data.objects[name];world=[o.matrix_world@v.co for v in o.data.vertices]
  for index,group in enumerate(components(o)):
   ids=set(group);points=[world[i]for i in group];z0=min(p.z for p in points);z1=max(p.z for p in points);center=sum(points,Vector())/len(points);front=max(p.dot(n)for p in points);back=min(p.dot(n)for p in points);cp=center+n*(front-center.dot(n));polys=[list(f.vertices)for f in o.data.polygons if set(f.vertices)<=ids]
   pt=BVHTree.FromPolygons(world,polys);overlap=st.overlap(pt);rays=[]
   for base in [-4,0,4,8,12,16]:
    if z1<=base or z0>=base+.32:continue
    z=max(z0,base)+min(z1,base+.32);z/=2
    for sideways in [-.28,0,.28]:
     start=cp+n*.50+u*sideways;start.z=z;hit,_,_,distance=st.ray_cast(start,-n,5)
     rays.append(dict(slabBase=base,slabTop=base+.32,rayZ=z,sideways=sideways,hitPoint=list(hit)if hit is not None else None,slabEdgeBehindFrontPaneMetres=distance-.50 if hit is not None else None,glassThickness=front-back))
   rows.append(dict(object=name,component=index,windowZ=[z0,z1],center=list(center),slabGlassPrimitiveOverlapPairs=len(overlap),verticalWindowBandCrossesSlab=bool(rays),slabEdgeRays=rays))
 write(OUT/'native-window-floor-diagnostic.json',dict(sourceModelSha256=SHA,slab=SLAB,watkinsOutward=list(n),slabIntervals=[[z,z+.32]for z in [-4,0,4,8,12,16]],panes=rows,interpretation='A slab at the same height as glass is a projected visual crossing. Actual primitive overlap and positive rear offset are separately reported;neither proves the real building floor level.'))
 active=bpy.data.collections['LRB_PUBLIC_INTERIOR168_study'].all_objects
 lifts=[]
 for o in active:
  if o.hide_render or o.type!='MESH' or not any(k in o.name.lower()for k in ['lift','landing','helical']):continue
  ps=[o.matrix_world@Vector(p)for p in o.bound_box];lifts.append(dict(object=o.name,z=[min(p.z for p in ps),max(p.z for p in ps)]))
 links=passage_measurements(True);write(OUT/'retained-core-connections.json',dict(links=links,dependentObjects=lifts,scope='Actual accepted221six-floor ramp/gallery support retained;not a surveyed pitch or new accessibility certificate.'))
 return rows,links,lifts

def admissible_intervals():
 # Necessary display clearance ranges only. They do not measure actual FFL.
 windows=[(.65,4.35),(5.66,8.81),(9.683793,12.43),(13.72,16.58),(17.59,19.55)];rows=[]
 for index,(lower,upper)in enumerate(zip(windows,windows[1:]),1):
  lo=lower[1]+.05;hi=upper[0]-.32-.05;base=4*index
  rows.append(dict(floor=str(index),acceptedSlabBase=base,acceptedFinish=base+.332,necessarySlabBaseRangeBetweenWatkinsWindows=[lo,hi],hypotheticalShiftRange=[lo-base,hi-base],isMeasuredFloorEvidence=False))
 result=dict(rows=rows,commonUpperFloorShiftRange=[max(r['hypotheticalShiftRange'][0]for r in rows),min(r['hypotheticalShiftRange'][1]for r in rows)],warning='This merely finds where a320mmplate could hide behind the modeled opaque window bands. Choosing one of these heights would be a visual adjustment without sourceFFL,and would break unchanged ramp/lift/furniture relations.')
 write(OUT/'unaccepted-clearance-intervals.json',result);return result

def references():
 refs=[dict(path='data/collections/library-roof-2025/existing-sw-elevation.pdf',date='17April2025,P01,4556-FBR-LR-ZZ-DR-A-111',scope='As Existing exterior spot heights and apertures;19.76ground AOD and24.87stone-band point are not labeled finished-floor levels.'),dict(path='data/collections/library-roof-2025/existing-nw-elevation.pdf',date='17April2025,P01,4556-FBR-LR-ZZ-DR-A-114',scope='Portugal window tiers;no internal slab edges orFFL schedule.'),dict(path='data/collections/library-roof-2025/existing-roof-sections.pdf',date='17April2025,P01,4556-FBR-LR-ZZ-DR-A-115',scope='Roof-only sections,not a section through six occupied levels.'),dict(path='data/documents/library_floor_plans.pdf',url='https://www.lse.ac.uk/asset-library/information/library-floor-plans-pdf.pdf',date='PDF modification19June2025;publication date unspecified',pages=[2,3,4,5,6,7],scope='Six public-level circulation/function diagrams;noFFL,vertical levels or floor-to-window section.'),dict(path='data/collections/library_round5/photos/LRB_9cf4d6340481.jpg',url='https://tyrensakt.com/projects/lse-library/',date='Completed2001project;capture date unknown',scope='Built ramp/gallery/lift topology;not a metric vertical registration to Watkins windows.')]
 for r in refs:r['sha256']=sha(ROOT/r['path'])
 write(DATA/'sources.json',dict(references=refs,newWebLookups=0,evidenceBoundary='Latest exterior geometry issue17April2025;no current2026interior level survey.',historicalImplementation=[dict(path='web/tools/align_library_levels.py',finding='Explicitly estimated4m pitch andG0.32datum'),dict(path='web/tools/align_library_atrium.py',finding='Slab floor tops set to-3.68+4i,thickness0.32m'),dict(path='web/tools/refine_library_roof_survey.py',finding='109remaps facade window heights only against2025elevation;does not calibrate interior floor levels'),dict(path='web/tools/refine_lrb_structure221.py',finding='4m helix and six flat gallery joins share retained floor datums')]))
 return refs

def render():
 s=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=s;c=bpy.data.objects.new('LRB234_DIAGNOSTIC_CAMERA',bpy.data.cameras.new('LRB234_DIAGNOSTIC_CAMERA'));s.collection.objects.link(c);s.camera=c;c.data.clip_end=1500;c.data.sensor_fit='VERTICAL';eye=Vector((26,-27,14));target=Vector((45.5,-.88,11));c.location=eye;c.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler();c.data.lens=c.data.sensor_height/(2*math.tan(math.radians(38)/2))
 old=s.world;w=old.copy();w.name='LRB234_DIAGNOSTIC_WORLD';s.world=w;bg=next(n for n in w.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[1].default_value=.65;e=w.node_tree.nodes.new('ShaderNodeTexEnvironment');e.image=bpy.data.images.load(str(ROOT/'web/public/environment/kloppenheim-daylight-1k.hdr'),check_existing=True);w.node_tree.links.new(e.outputs['Color'],bg.inputs[0]);active=sorted(o.name for o in s.objects if not o.hide_render and o!=c)
 s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True;s.render.resolution_x=1100;s.render.resolution_y=825;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX';s.render.filepath=str(OUT/'accepted233-Watkins-window-floor.png');bpy.ops.render.render(write_still=True)
 s.world=old;bpy.data.objects.remove(c,do_unlink=True);bpy.data.cameras.remove(bpy.data.cameras['LRB234_DIAGNOSTIC_CAMERA']);bpy.data.worlds.remove(w)
 return dict(position=[26,14,27],target=[45.5,11,.88],fov=38,allNativeContextRetained=True,activeContextObjects=len(active),activeContextNamesSha256=hashlib.sha256('\n'.join(active).encode()).hexdigest(),scope='One actual233diagnostic image;no artificial before/after duplicate because nothing was changed.')

def run():
 OUT.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True);assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();before=state();assert len(before['objects'])==8529 and len(before['rooms'])==34
 refs=references();panes,links,lifts=measure();intervals=admissible_intervals();view=render();assert state()==before
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();assert state()==before;assert sha(BASE)==SHA
 offsets=[p['slabEdgeBehindFrontPaneMetres']for r in panes for p in r['slabEdgeRays']if p['slabEdgeBehindFrontPaneMetres']is not None]
 summary=dict(paneComponents=len(panes),verticallyCrossedComponents=sum(r['verticalWindowBandCrossesSlab']for r in panes),componentsWithPrimitiveOverlap=sum(r['slabGlassPrimitiveOverlapPairs']>0 for r in panes),primitiveOverlapPairs=sum(r['slabGlassPrimitiveOverlapPairs']for r in panes),slabEdgeRayHits=len(offsets),slabEdgeBehindFrontPaneRange=[min(offsets),max(offsets)]if offsets else None)
 report=dict(version=234,building='LRB',status='source-floor-datum-unresolved-read-only',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,targetCollection='LRB_PUBLIC_INTERIOR168_study',destinationCollection='LRB_PUBLIC_INTERIOR168_study',componentPath=None,componentSha256=None,addedObjects=[],archivedObjects=[],changedObjects=[],addedFingerprints={},replacementMaterialBindings={},summary=summary,diagnostics=['native-window-floor-diagnostic.json','retained-core-connections.json','unaccepted-clearance-intervals.json'],references=refs,sourceManifest=str((DATA/'sources.json').relative_to(ROOT)),decision='Do not move floors or cut floor edges without a registered section/FFL schedule.233transparency exposed a pre-existing unregistered interior/exterior level relationship,not a new floor displacement.',sourceFindings=['Public floor4m pitch is explicitly an estimate in37;38sets six slab tops at-3.68+4i.','109independently remaps external window rows to2025existing elevation;it does not establish corresponding internal floor levels.','2025elevation point heights are not labeledFFL;roof sections omit the occupied-storey stack;official floor plans omit heights.','221current flat joins,finishes,helix andlift depend on the retained floor datums. A slab-only shift would leave those physical connections behind.'],unacceptedVisualAdjustment=intervals,verification=dict(acceptedNativeIndependentlyReopened=True,sourceObjectsVerified=8529,sourceMaterialsVerified=len(before['materials']),protectedSpaces=34,protectedSpaceMembers=len(set().union(*(set(v)for v in before['rooms'].values()))),allOriginalGeometryUVTransformsMaterialBindingsNodesModifiersPropertiesOwnersVisibilityAndSpaceMembershipUnchanged=True,baselineBytesUnchanged=True,noComponentManufactured=True),view=view,previews=['accepted233-Watkins-window-floor.png'],requiredEvidence=['A building section registering Watkins/Portugal window sills/heads,local street/Gdatum and internalFFLs acrossG–4.','The helix/gallery/lift stop levels tied to the same vertical datum,plus actual slab thickness/edge setback.','Current architectural floor plans distinguishing public slab edges/voids from function-guide colours.'],limitations=['Necessary non-glazed clearance ranges are mathematical model constraints,not measured floor levels or an authorized geometry proposal.','Any actual floor-edge recession or pane intersection measured here describes the modeled233mesh only.','No source supports concealing the issue with a fake backing,room or optical darkening.'])
 write(OUT/'audit.json',report);write(OUT/'verification.json',report['verification'])
 for p in OUT.glob('*.blend*'):p.unlink()
 print('LRB234_READONLY_VERIFIED',json.dumps(summary),flush=True)
if __name__=='__main__':run()
