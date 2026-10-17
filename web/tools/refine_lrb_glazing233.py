"""Bounded LRB glazing candidate, fixed for Blender's Text Editor.

Compare reduced diffuse opaque proxies with restrained dielectric transmission
through the two Watkins glass batches. Clear the floor-connected232entry leaves.
Only copied material bindings change; no room or backing is manufactured.
"""
from pathlib import Path
import sys,json,hashlib,math
sys.dont_write_bytecode=True
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v232.blend'
OUT=ROOT/'result/blender/lrb-glazing233'
DATA=ROOT/'data/collections/lrb-glazing233'
SHA='1f6ed3da66011e057233697fe8753374a55918d8c4278d56670cbd81192ae2a8'
PREFIX='LRB233_'
SOURCES=['LRB196_FINISH_GLASS181_LRB_NEXT_broad_window_glass','SITE232_EST_LRB_glazing_with_entry_aperture','SITE232_EST_LRB_paired_glazed_entry_leaves']
NAMES=['LRB233_broad_window_reflective_glass','LRB233_Watkins_reflective_glass','LRB233_floor_connected_entry_glass']
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,update_scene,set_layer_hidden
from refine_plaza_environment231 import state
from refine_51l_exterior204 import geometry_signature,finish_state
from refine_portsmouth_exterior207 import material_fingerprint
from refine_streets230 import components

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def shader(m):return next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
def preserve(before,added,materials):
 after=state()
 assert len(before['objects'])==8502 and len(before['rooms'])==34
 for key in ['objects','materials','owners','modifiers','props','visibility','rooms']:
  assert {n:after[key][n]for n in before[key]}==before[key],key
 assert set(after['objects'])-set(before['objects'])==set(added)
 assert set(after['materials'])-set(before['materials'])==set(materials)
 assert sha(BASE)==SHA
 return dict(sourceObjectsUnchanged=8502,protectedSpaces=34,protectedSpaceObjects=len(set().union(*(set(v)for v in before['rooms'].values()))),allOriginalGeometryUVTransformsMaterialBindingsUnchanged=True,allOriginalMaterialNodesUnchanged=True,allOriginalModifiersPropertiesOwnershipUnchanged=True,allOriginalVisibilityRestored=True,baselineBytesUnchanged=True)

def backing_diagnostic():
 """Report actual inherited floor support, not a fabricated room enclosure."""
 slab=bpy.data.objects['LRB168__LRB_library_floor_slabs']
 t=BVHTree.FromPolygons([slab.matrix_world@v.co for v in slab.data.vertices],[list(p.vertices)for p in slab.data.polygons])
 o=bpy.data.objects[SOURCES[-1]];points=[o.matrix_world@v.co for v in o.data.vertices]
 c=sum(points,Vector())/len(points)
 # Infer street frame from existing door leaves. G finish extends behind them.
 reg=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
 ring=next(b['rings'][0]for b in reg['buildings']if b['code']=='LRB')
 origin,end=[Vector((*ring[i],0))for i in [0,13]];u=(end-origin).normalized();outward=Vector((u.y,-u.x,0))
 checks=[]
 for depth in [.30,.80,1.50]:
  p=c-outward*depth;p.z=1.0;hit=t.ray_cast(p,Vector((0,0,-1)),2)
  assert hit[0]is not None and abs(hit[0].z-.32)<.002,(depth,hit)
  checks.append(dict(point=list(p),floorHit=list(hit[0]),floorObject=slab.name))
 panes=[]
 objects=[o for col in ['LRB_EXTERIOR','LRB_PUBLIC_INTERIOR168_study']for o in bpy.data.collections[col].all_objects if o.type=='MESH'and not o.hide_render and o.name not in SOURCES]
 trees=[(o,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(f.vertices)for f in o.data.polygons]))for o in objects]
 for name in SOURCES:
  source=bpy.data.objects[name]
  for index,group in enumerate(components(source)):
   points=[source.matrix_world@source.data.vertices[i].co for i in group];center=sum(points,Vector())/len(points);z0=min(p.z for p in points);z1=max(p.z for p in points)
   start=center-outward*.12;hits=[]
   for obj,bt in trees:
    hit,_,face,distance=bt.ray_cast(start,-outward,20)
    if hit is not None:hits.append(dict(object=obj.name,distance=distance+.12,point=list(hit),material=obj.data.materials[obj.data.polygons[face].material_index].name))
   hits.sort(key=lambda r:r['distance'])
   down=t.ray_cast(start+Vector((0,0,.02)),Vector((0,0,-1)),30);up=t.ray_cast(start,Vector((0,0,1)),30)
   panes.append(dict(source=name,component=index,boundsZ=[z0,z1],center=list(center),nearestInwardSurfaces=hits[:4],floorDown=list(down[0])if down[0]is not None else None,slabUp=list(up[0])if up[0]is not None else None,slabDatumsCrossingPane=[z for z in [-4,0,4,8,12,16]if z0<z+.32 and z1>z]))
 write(OUT/'pane-backing-diagnostic.json',dict(panes=panes,scope='Active native triangle geometry along inherited Watkins outward normal;floor datums are inherited estimates,not as-built registration.'))
 return dict(paneBackingDiagnostic='pane-backing-diagnostic.json',paneComponents=len(panes),entryChecks=checks,largeWindowClearanceDecision='Limited transmission candidate: expose inherited public structure without fabricated peripheral rooms;report crossing floor datums per pane.',noNewBackingOrRooms=True,externalWindowRowsEstimated=True)

def references():
 refs=[dict(path='data/collections/campus_photos_round3/images/LRB/LRB_LAK_geograph_668683.jpg',url='https://www.geograph.org.uk/photo/668683',date='2008-01-23',scope='Daylight Watkins facade has dark,sky-reflecting large windows; no calibrated optical values.'),dict(path='data/建筑图片/LRB_Lionel Robbins Building_Library/01_建筑实拍/exteriors_lse_estate_016.jpg',url='https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate',date='Capture unknown;2025/26 handbook publication is not a photograph date',scope='Official corner photograph supports glazing and visible illumination behind large panes;night light is not a daylight tint sample.'),dict(path='data/collections/library-roof-2025/existing-sw-elevation.pdf',url=None,date='As Existing issue17April2025,P01,4556-FBR-LR-ZZ-DR-A-111',scope='Existing Watkins glazing apertures;not measured optical properties or current2026 condition.'),dict(path='data/documents/library_floor_plans.pdf',url='https://www.lse.ac.uk/asset-library/information/library-floor-plans-pdf.pdf',date='PDF modified2025-06-19;publication date not stated',scope='Official service guide supports inherited G-level library use;not a complete surveyed enclosure.')]
 for r in refs:r['sha256']=sha(ROOT/r['path'])
 write(DATA/'sources.json',dict(references=refs,newWebLookups=0,reviewDate='2026-10-17',latestDatedExteriorGeometryEvidence='17April2025 As Existing drawing;not2026survey',numericOptics='Visual estimate,not calibrated glass specification',referencePhotosNotExported=True))
 return refs

def render(sources,added):
 s=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=s
 c=bpy.data.objects.new(PREFIX+'REVIEW_CAMERA',bpy.data.cameras.new(PREFIX+'REVIEW_CAMERA'));s.collection.objects.link(c);s.camera=c;c.data.clip_end=1500;c.data.sensor_fit='VERTICAL'
 original_world=s.world;world=original_world.copy();world.name=PREFIX+'REVIEW_WORLD';s.world=world;world.use_nodes=True
 nodes=world.node_tree.nodes;bg=next(n for n in nodes if n.type=='BACKGROUND');bg.inputs[1].default_value=.65
 env=nodes.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(ROOT/'web/public/environment/kloppenheim-daylight-1k.hdr'),check_existing=True);world.node_tree.links.new(env.outputs['Color'],bg.inputs[0])
 s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True;s.render.resolution_x=1100;s.render.resolution_y=825;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
 active=sorted(o.name for o in s.objects if not o.hide_render and o not in sources+added+[c])
 jobs=json.loads((ROOT/'web/tools/gallery-views.json').read_text());entry=next(v['view']for v in jobs if v['name']=='lrb-watkins-entrance')
 views=[dict(name='Watkins-entry',**entry),dict(name='large-windows',position=[26,14,27],target=[45.5,11,.88],fov=38)]
 for view in views:
  eye=Vector((view['position'][0],-view['position'][2],view['position'][1]));target=Vector((view['target'][0],-view['target'][2],view['target'][1]));c.location=eye;c.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler();c.data.lens=c.data.sensor_height/(2*math.tan(math.radians(view['fov'])/2))
  for phase in ['before','after']:
   for o in sources:o.hide_render=phase=='after';set_layer_hidden(o,phase=='after')
   for o in added:o.hide_render=phase=='before';set_layer_hidden(o,phase=='before')
   update_scene();s.render.filepath=str(OUT/(phase+'-'+view['name']+'.png'))
   if phase=='after' or not Path(s.render.filepath).exists():bpy.ops.render.render(write_still=True)
 for o in sources:o.hide_render=False;set_layer_hidden(o,False)
 for o in added:o.hide_render=False;set_layer_hidden(o,False)
 s.world=original_world;bpy.data.objects.remove(c,do_unlink=True);bpy.data.cameras.remove(bpy.data.cameras[PREFIX+'REVIEW_CAMERA']);bpy.data.worlds.remove(world)
 return views,dict(allNativeBuildingsCrownsAndPublicInteriorsRetained=True,activeContextObjects=len(active),activeContextNamesSha256=hashlib.sha256('\n'.join(active).encode()).hexdigest(),lighting='Same HDR0.65,native full-campus lights,AgX,Cycles12samples,1100x825')

def build():
 OUT.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True);assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();before=state();assert len(before['objects'])==8502
 refs=references();backing=backing_diagnostic();sources=[bpy.data.objects[n]for n in SOURCES];assert all(not o.hide_render for o in sources)
 material_cache={};added=[];bindings={};changes=[]
 for source,name in zip(sources,NAMES):
  o=source.copy();o.data=source.data.copy();o.name=name;o.data.name=name;o['originalObject']=source.name;o['destinationCollection']='LRB_EXTERIOR';o['webGeometrySource']=source.get('webGeometrySource',source.name);o['opticsEstimated233']=True;bpy.data.collections['LRB_EXTERIOR'].objects.link(o)
  is_entry=source.name==SOURCES[-1]
  for slot,m in enumerate(source.data.materials):
   key=(m.name,is_entry)
   if key not in material_cache:
    new=m.copy();new.name=PREFIX+('entry_dielectric_'if is_entry else 'limited_transmission_')+str(len(material_cache));p=shader(new)
    p.inputs['Base Color'].default_value=(.84,.88,.88,1)if is_entry else(.055,.072,.077,1)
    p.inputs['Metallic'].default_value=0;p.inputs['Roughness'].default_value=.13;p.inputs['IOR'].default_value=1.5
    p.inputs['Transmission Weight'].default_value=.88 if is_entry else .72
    new['webOpacity']=.30 if is_entry else .76
    p.inputs['Alpha'].default_value=1
    if is_entry:new['webOpacity']=.30;new['webClosedGlazing']=True
    new.diffuse_color=p.inputs['Base Color'].default_value
    new['opticalEstimate']='233 bounded exterior study;photographs show dark reflection and glazing,not measured optics'
    material_cache[key]=new;changes.append(dict(sourceMaterial=m.name,material=new.name,before=finish_state(m),after=finish_state(new),role='Clear floor-connected entry leaf'if is_entry else'Limited transmission reveals accepted public structure;no new peripheral rooms'))
   o.data.materials[slot]=material_cache[key]
  o.hide_render=False;set_layer_hidden(o,False)
  assert geometry_signature(o)==geometry_signature(source)
  bindings[o.name]=[m.name for m in o.data.materials];added.append(o)
 views,context=render(sources,added)
 verification=preserve(before,[o.name for o in added],[m.name for m in material_cache.values()])
 component=OUT/'component.blend';fingerprints={o.name:object_fingerprint(o)for o in added};shapes={o.name:geometry_signature(o)for o in added};material_names=[m.name for m in material_cache.values()]
 bpy.data.libraries.write(str(component),set(added)|set(material_cache.values()),fake_user=True)
 report=dict(version=233,building='LRB',status='bounded-estimated-optics-candidate',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,sourceModelSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection='LRB_EXTERIOR',destinationCollection='LRB_EXTERIOR',displayOwner='LRB_EXTERIOR',addedObjects=NAMES,ownedObjects=NAMES,archivedObjects=SOURCES,changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,materialChanges=changes,backingDiagnostic=backing,references=refs,sourceManifest=str((DATA/'sources.json').relative_to(ROOT)),views=views,productionVisibility=context,verification=verification,changes=['Restore real dielectric transmission only on two232floor-connected entrance leaves.','Use bounded transmission0.72/webOpacity0.76 on retained Watkins large-window geometry,with restrained diffuse tint and daylight reflection.','Existing public structure may be visible;no unseen room layout or backing is fabricated.'],previews=[phase+'-'+v['name']+'.png'for v in views for phase in ['before','after']],limitations=['Numeric tint,reflectance,roughness and opacity are estimates;no measured glass specification.','Large panes now partially reveal inherited public structure;peripheral room partitions remain incomplete and window/floor registration is not newly certified.','Native12sample full-context HDR review differs from browser PMREM rendering;root must confirm production images.','Historic2008daylight photograph and2025existing elevations do not establish present2026condition.','No new floor,backboard,room,opening,UV layout or external form is claimed;three copied meshes replace three existing batches.'])
 write(OUT/'audit.json',report)
 # Reopen baseline independently,then append only the published component.
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(NAMES)
 for o in dst.objects:
  bpy.data.collections['LRB_EXTERIOR'].objects.link(o)
  assert object_fingerprint(o)==fingerprints[o.name]and geometry_signature(o)==shapes[o.name]
  assert[m.name for m in o.data.materials]==bindings[o.name]
 recheck=preserve(before,NAMES,material_names)
 report['verification'].update(recheck);report['verification']['componentIndependentlyAppendedAndVerified']=True;report['verification']['componentSha256']=sha(component)
 write(OUT/'audit.json',report);write(OUT/'verification.json',report['verification'])
 for p in OUT.glob('*.blend1'):p.unlink()
 print('LRB233_COMPONENT_READY',len(NAMES),sha(component),flush=True)
if __name__=='__main__':build()
