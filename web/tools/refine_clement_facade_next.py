"""Register opaque mid-window spandrels in Clement House tall street bays.

Run in Blender's Text Editor. Photographic panel dimensions and finish remain estimates.
"""
from pathlib import Path
import array, hashlib, json, sys, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/clement_facade_next'
OUT.mkdir(parents=True,exist_ok=True)
BASE = ROOT/'result/blender/LSE_campus_detailed_v136.blend'
if not BASE.exists():
    BASE = max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
def open_baseline():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
    if previous:
        for name in previous.get('ownedObjects',[]):
            obj=bpy.data.objects.get(name)
            if obj:
                mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);mesh.use_fake_user=False
                if not mesh.users:bpy.data.meshes.remove(mesh)
        for name in previous.get('archivedObjects',[]):
            obj=bpy.data.objects[name];state=previous['originalVisibility'][name]
            obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:layer.update()
open_baseline()
def fingerprint(obj):
    digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        for data,field,kind,width in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
            values=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,values);digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);digest.update(values.tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
originals={o.name:fingerprint(o) for o in bpy.data.objects}
visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()] for o in bpy.data.objects}
collection=bpy.data.collections['CLM_EXTERIOR']
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());record=next(b for b in site['buildings'] if b['code']=='CLM');points=[Vector(r) for r in [record['rings'][0][i] for i in (5,4,3,2,1)]];centre=Vector(record['center']);segments=[];length=0
for a,b in zip(points,points[1:]):
 u=(b-a).normalized();n=Vector((u.y,-u.x));n=-n if n.dot((a+b)/2-centre)<0 else n;size=(b-a).length;segments.append((length,length+size,a,u,n));length+=size
bay=length/7
low,high,panel_low,panel_high=12.8,18.36,15.37,15.79
centre_z=(panel_low+panel_high)/2
# Match the existing114 transverse location while replacing its narrow black
# divider with the photographed opaque brown zone. No new floor or stone pier.
def frame(s):return next((t for t in segments if s<=t[1]),segments[-1])
def point(s,d,z):
 start,end,a,u,n=frame(s);xy=a+u*(s-start)+n*d;return Vector((xy.x,xy.y,z))
def normal(s):n=frame(s)[4];return Vector((n.x,n.y,0))
def chunks(bm):
 seen=set()
 for seed in bm.verts:
  if seed in seen:continue
  part=[];todo=[seed];seen.add(seed)
  while todo:
   v=todo.pop();part.append(v)
   for e in v.link_edges:
    o=e.other_vert(v)
    if o not in seen:seen.add(o);todo.append(o)
  yield part
source_glass=bpy.data.objects['CLM_D5_tall114_glass_panes'];source_bars=bpy.data.objects['CLM_D5_tall114_metal_bars'];assert not source_glass.hide_render and not source_bars.hide_render
owned_glass=source_glass.copy();owned_glass.data=source_glass.data.copy();owned_glass.name='CLM_NEXT_FACADE_split_tall_panes';owned_glass.data.name=owned_glass.name;collection.objects.link(owned_glass)
bm=bmesh.new();bm.from_mesh(owned_glass.data);parts=list(chunks(bm));assert len(parts)==7
for part in parts:
 assert len(part)==8
 geom=list(part)+list({e for v in part for e in v.link_edges})+list({f for v in part for f in v.link_faces});duplicate=bmesh.ops.duplicate(bm,geom=geom);upper=[v for v in duplicate['geom'] if isinstance(v,bmesh.types.BMVert)];assert len(upper)==8
 for v in part:
  p=owned_glass.matrix_world@v.co
  if p.z>centre_z:p.z=panel_low;v.co=owned_glass.matrix_world.inverted()@p
 for v in upper:
  p=owned_glass.matrix_world@v.co
  if p.z<centre_z:p.z=panel_high;v.co=owned_glass.matrix_world.inverted()@p
bm.to_mesh(owned_glass.data);bm.free();owned_glass.data.update();assert len(owned_glass.data.vertices)==112
panels=source_glass.copy();panels.data=source_glass.data.copy();panels.name='CLM_NEXT_FACADE_opaque_brown_spandrels';panels.data.name=panels.name;collection.objects.link(panels)
for i in range(7):
 s=(i+.5)*bay;n=normal(s)
 for v in list(panels.data.vertices)[i*8:(i+1)*8]:
  p=panels.matrix_world@v.co;p.z=panel_low if p.z<centre_z else panel_high;p+=n*.045;v.co=panels.matrix_world.inverted()@p
mat=bpy.data.materials.new('CLM_NEXT_FACADE_warm_opaque_spandrel');mat.use_nodes=True;mat.diffuse_color=(.26,.16,.11,1);shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Metallic'].default_value=.15;shader.inputs['Roughness'].default_value=.56;panels.data.materials.clear();panels.data.materials.append(mat);panels.data.update()
owned_bars=source_bars.copy();owned_bars.data=source_bars.data.copy();owned_bars.name='CLM_NEXT_FACADE_spandrel_edge_rails';owned_bars.data.name=owned_bars.name;collection.objects.link(owned_bars)
bm=bmesh.new();bm.from_mesh(owned_bars.data);targets=[];untouched=[]
for part in list(chunks(bm)):
 pts=[owned_bars.matrix_world@v.co for v in part];z=sum(p.z for p in pts)/len(pts)
 if abs(z-centre_z)<.001:targets.append(part)
 else:untouched.extend(tuple(v.co) for v in part)
assert len(targets)==7
for part in targets:
 geom=list(part)+list({e for v in part for e in v.link_edges})+list({f for v in part for f in v.link_faces})
 for edge_z in (panel_low,panel_high):
  new=bmesh.ops.duplicate(bm,geom=geom)
  for v in [a for a in new['geom'] if isinstance(a,bmesh.types.BMVert)]:
   p=owned_bars.matrix_world@v.co;p.z=edge_z+(p.z-centre_z)*(.05/.12);v.co=owned_bars.matrix_world.inverted()@p
 bmesh.ops.delete(bm,geom=part,context='VERTS')
bm.to_mesh(owned_bars.data);bm.free();owned_bars.data.update();assert len(owned_bars.data.vertices)==448
from collections import Counter
assert not Counter(untouched)-Counter(tuple(v.co) for v in owned_bars.data.vertices)
owned=[owned_glass,owned_bars,panels];sources=[source_glass,source_bars]
def cast(objects,probes):
 vs=[];fs=[];names=[]
 for o in objects:
  k=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(k+i for i in f.vertices) for f in o.data.polygons);names.extend([o.name]*len(o.data.polygons))
 tree=BVHTree.FromPolygons(vs,fs);results=[]
 for label,s,z in probes:
  hit=tree.ray_cast(point(s,1.2,z),-normal(s),2.5);results.append({'label':label,'s':s,'z':z,'firstObject':names[hit[2]] if hit[2] is not None else None})
 return results
visible=lambda:[o for o in collection.all_objects if o.type=='MESH' and not o.hide_render]
fill=[('panel-'+str(i)+'-'+str(dx),(i+.5)*bay+dx,centre_z) for i in range(7) for dx in (-.7,0,.7)]
lights=[('glass-'+str(i)+'-'+str(z),(i+.5)*bay+.7,z) for i in range(7) for z in (14.0,17.1)]
entry=[('entry-'+str(i)+'-'+str(z),(i+.5)*bay,z) for i in (0,3,6) for z in (.65,1.65,2.65)]
before=cast([o for o in visible() if o not in owned],fill+lights+entry)
for o in sources:o.hide_render=True;o.hide_set(True)
after=cast(visible(),fill+lights+entry)
assert all(r['firstObject']==panels.name for r in after[:21]),after[:21]
assert all(r['firstObject']==owned_glass.name for r in after[21:35]),after[21:35]
assert after[35:]==before[35:],after[35:]
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'clement-tall-window-spandrel-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
ref=ROOT/'result/blender/stage73/clm-2018.jpg';ref2=ROOT/'result/blender/stage73/clm-2023.jpg';estate=ROOT/'data/建筑图片/CLM_Clement House/01_建筑实拍/exteriors_lse_estate_003.jpg'
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[o.name for o in owned],'archivedObjects':[o.name for o in sources],'archiveObjects':[o.name for o in sources],'changes':[{'source':source_glass.name,'owned':owned_glass.name,'action':'Split7 tall glass boxes into14 panels around true opaque band'},{'source':source_bars.name,'owned':owned_bars.name,'action':'Replace7 thick center bars with14 thin boundary rails; retain42 other rails exactly'},{'source':None,'owned':panels.name,'action':'Add7 opaque brown infill panels in the registered tall openings'}],'panelRegistration':{'low':panel_low,'high':panel_high,'height':panel_high-panel_low,'bandFractionOfTallOpening':.42/5.56,'existingMiddleHeight':15.58,'frontOffsetFromOriginalGlass':.045,'metreDimensionsEstimated':True},'references':[{'local':str(ref.relative_to(ROOT)),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'captureDate':'2018-04-24','source':'Wei-Te Wong, archived stage73 references','supports':'All seven tall bays use warm opaque horizontal infill between their upper and lower glazed sections; most middle fields tree-obscured, end and right bays clearest.'},{'local':str(ref2.relative_to(ROOT)),'sha256':hashlib.sha256(ref2.read_bytes()).hexdigest(),'captureDate':'2023-11-15','source':'N Chadwick, archived stage73 references','supports':'Convex stone facade, seven bays, tall window morphology and roof; trees, vehicles and scaffolding limit internal frame/detail validation.'},{'local':str(estate.relative_to(ROOT)),'sha256':hashlib.sha256(estate.read_bytes()).hexdigest(),'captureDate':'unknown','supports':'Timber side entrance, stone tablet, broken pediment/figures; no change to this registered entrance.'}],'wholeStreetReview':{'mass':'Seven-bay convex Portland-stone main frontage retained; absolute heights/setback/bow remain approximate GIS and photo estimates.','storeys':'Existing colonnade and lower window tier, small tier, uninterrupted tall openings, upper small tier, attic and5 dormers retained. Do not revert114 to two separate masonry window rows.','divisions':'Three-column tall windows and8-row total layout retained around new opaque band; finer opening casements are not established from trees-obscured views.','stoneAndBrick':'Visible CLM front predominantly pale stone; neighboring red/grey brick mass is not CLM proof. Added brown strip is opaque spandrel, not invented red brick.','entrance':'Registered closed timber portals and glazing around central colonnade remain; side entrance partly photographed, full threshold/passages not measured.','glass':'Current neutral dark glass is opaque PBR approximation, Transmission0. No arbitrary alpha or guessed interior backplates added. Current recess objects remain.','roof':'Prior73 five dormers/four stacks and cornice sweep retained; latest2026 plant/rear roof unverified.'},'beforeProbes':before,'afterProbes':after,'limitations':['Panel dimensions and warm finish are photo-guided estimates, not architectural material specification or a measured2026 survey.','Source imagery establishes seven coherent mid-window bands; exact historical paint and current refurbishment finish unknown.','Figure surrounds and true central ornament contours, exact casement mechanics, full glass optics, rear roof and unseen elevations remain unresolved.','No new rooms, rear elevations, global transparent glazing or material changes outside the new bands.','Entry first-hit probes check retained model passages/door surfaces, not real-site accessibility certification.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('CLM_SPANDREL_COMPONENT_SAVED',flush=True)
open_baseline();collection=bpy.data.collections['CLM_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=audit['ownedObjects']
owned=dst.objects
for o in owned:
 collection.objects.link(o)
 if o.name==audit['ownedObjects'][0]:src=bpy.data.objects[audit['archivedObjects'][0]]
 elif o.name==audit['ownedObjects'][1]:src=bpy.data.objects[audit['archivedObjects'][1]]
 else:continue
 for i,m in enumerate(src.data.materials):o.data.materials[i]=m
for name in audit['archivedObjects']:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for sc in bpy.data.scenes:
 for layer in sc.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items());assert cast(visible(),fill+lights+entry)==after
scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
for o in scene.objects:
 if o.type=='MESH' and o.name not in {obj.name for obj in collection.all_objects}:o.hide_render=True
focus=point(length/2,0,13.5);n=normal(length/2);camdata=bpy.data.cameras.new('CLM_NEXT_FACADE_preview');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+n*42+Vector((0,0,3));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=37;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1400;scene.render.resolution_y=1150;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'reloaded-clement-street-facade.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'savedComponentReopened':True,'originalGeometryPreserved':True,'originalObjectCount':len(originals),'reloadedProbes':after,'nativeRender':'reloaded-clement-street-facade.png','splitGlassCount':14,'opaqueBandCount':7,'entryProbesUnchanged':True,'retainedOtherBarVertices':len(untouched)}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('CLM_SPANDREL_COMPONENT_RELOADED_VERIFIED',flush=True)
