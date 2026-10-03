"""Audit the unsupported separate LRB plaza entry canopy.
Run in Blender. Archive-only visibility candidate; no full campus save.
"""
from pathlib import Path
import bpy,json,hashlib,array
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/lrb_facade_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v135.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene;col=bpy.data.collections['LRB_EXTERIOR']
def fingerprint(o):
 h=hashlib.sha256(str([list(row)for row in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,count in ((o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)):
   values=array.array(kind,[0])*(len(data)*count);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in o.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
originals={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
canopies=[o for o in col.all_objects if o.type=='MESH'and not o.hide_render and 'entry_canopy' in o.name];assert len(canopies)==1,[o.name for o in canopies];source=canopies[0]
ring=next(b['rings'][0]for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings']if b.get('code')=='LRB');p,q=[Vector((*ring[i],0))for i in [0,13]];axis=(q-p).normalized();normal=Vector((axis.y,-axis.x,0))
vs=[source.matrix_world@v.co-p for v in source.data.vertices];bounds=[[min(v.dot(ax)for v in vs),max(v.dot(ax)for v in vs)]for ax in [axis,normal,Vector((0,0,1))]]
references=[]
for f in ['data/建筑图片/LRB_Lionel Robbins Building_Library/01_建筑实拍/campus_photos_round3_LRB_LAK_geograph_668683.jpg','data/previews/property_handbook_p30.png']:
 path=ROOT/f;references.append({'path':f,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
audit={'baseline':str(BASE),'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[],'archivedObjects':[],'archiveObjects':[],'proposedArchiveObjects':[source.name],'sourceGeometry':{'name':source.name,'vertexCount':len(source.data.vertices),'faceCount':len(source.data.polygons),'localBounds':bounds,'materials':[m.name for m in source.data.materials]},'references':references,'change':'No accepted change; canopy omitted in memory for hypothetical comparison only.','evidence':'Geograph2008 suggests no separate canopy at the historical entry;2025/26 night view does not reliably exclude it due to stone-band shadow and angle. Current absence unproven.','limitations':['Entry location and old door width remain inherited estimates; no new size or current gate interpretation.','Night photo low resolution; strongest canopy evidence is2008 view and may not prove present-day works.','Only one independent canopy source, no new geometry or whole-entry reconstruction.'],'componentCreated':False,'fullModelSaved':False,'implementationStatus':'Pending current photographic confirmation;do not merge archives.'}
source.hide_render=True;source.hide_set(True);assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
visible={o.name for o in col.all_objects}
for o in scene.objects:
 if o.type=='MESH'and o.name not in visible:o.hide_render=True
focus=p+axis*((bounds[0][0]+bounds[0][1])/2)+Vector((0,0,2.6));cd=bpy.data.cameras.new('LRB_ENTRY_CANOPY_REVIEW');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=focus+normal*15;cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=7.8;scene.camera=cam;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'pending-canopy-comparison.png');bpy.ops.render.render(write_still=True)
source.hide_render,source.hide_viewport=visibility[source.name][:2];source.hide_set(visibility[source.name][2])
audit['referenceCoverage']={'historical':'2008 daylight covers entry head but cannot establish current condition.','recentPublication':'2025/26 night view includes entry, but stone-band shadow/oblique angle prevents reliably excluding thin projecting canopy;capture date unknown.'};audit['nextAction']='One dated daylight oblique close view of current entry head before any archive.';audit['previewStatus']='Unaccepted hypothetical omission.'
audit['originalGeometryPreserved']=True;audit['originalObjectCount']=len(originals);audit['blenderExitedAfterAudit']=True;(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('LRB_CANOPY_AUDIT',source.name,bounds);bpy.ops.wm.quit_blender()
