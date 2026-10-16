"""SAL historical window tint study on accepted228; run in Blender Text Editor.

Copies the two accepted window batches and only their blue glass materials.
Brightness, optical coefficients, topology, UVs and all source state are retained.
No current survey or calibrated glazing specification is inferred from photographs.
"""
from pathlib import Path
import hashlib,json,math,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v228.blend'
SHA='0ddf5bb3791d146690d2af1f44b4cb6b113930cf687bc30d1cb916d84f4f066b'
OUT=ROOT/'result/blender/facade-material229'
SOURCE=ROOT/'data/collections/facade-material229'
COLLECTION='SAL_EXTERIOR'
PREFIX='SAL229_'
TARGETS=['GLASS181_SAL_D5_photo70_glass','SAL222_opened_SAL184_GLASS181_SAL_NEXT_GLAZING149_retained_frontage_glass']
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints
from refine_portsmouth_exterior207 import material_fingerprint
from refine_ksw_exterior219 import modifier_state

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def update():
 for s in bpy.data.scenes:
  for layer in s.view_layers:layer.update()
 bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def state():
 meta=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
 rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in meta['spaces']}
 assert len(rooms)==27 and len(set().union(*(set(v)for v in rooms.values())))==1068
 return dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},modifiers={o.name:modifier_state(o)for o in bpy.data.objects},owners={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},visibility={o.name:o.hide_render for o in bpy.data.objects},rooms=rooms,roomScenes={c:{s.name:sorted(n for n in ns if n in s.objects)for s in bpy.data.scenes}for c,ns in rooms.items()})
def verify(before,hidden):
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in before['objects'].items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in before['materials'].items())
 assert all(modifier_state(bpy.data.objects[n])==v for n,v in before['modifiers'].items())
 assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in before['owners'].items())
 assert all(bpy.data.objects[n].hide_render==(True if n in hidden else v)for n,v in before['visibility'].items())
 assert all(sorted(o.name for o in bpy.data.collections[c].all_objects)==ns for c,ns in before['rooms'].items())
 assert {c:{s.name:sorted(n for n in ns if n in s.objects)for s in bpy.data.scenes}for c,ns in before['rooms'].items()}==before['roomScenes']
def metrics(m):
 n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');c=list(n.inputs['Base Color'].default_value)
 return dict(baseColor=c,luminance=sum(a*b for a,b in zip(c,[.2126,.7152,.0722])),saturation=(max(c[:3])-min(c[:3]))/max(c[:3]),roughness=n.inputs['Roughness'].default_value,metallic=n.inputs['Metallic'].default_value,alpha=n.inputs['Alpha'].default_value,transmission=n.inputs['Transmission Weight'].default_value,ior=n.inputs['IOR'].default_value,webOpacity=m.get('webOpacity'),webClosedGlazing=m.get('webClosedGlazing'))
def preview(label):
 scene=bpy.data.scenes.new(PREFIX+'PREVIEW');scene.collection.children.link(bpy.data.collections[COLLECTION]);bpy.context.window.scene=scene
 world=bpy.data.worlds.new(PREFIX+'WORLD');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.8,.8,.8,1);world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
 sun=bpy.data.objects.new(PREFIX+'SUN',bpy.data.lights.new(PREFIX+'SUN','SUN'));scene.collection.objects.link(sun);sun.data.energy=1.7;sun.data.angle=.1;sun.rotation_euler=(math.radians(25),math.radians(-20),math.radians(-30))
 camera=bpy.data.objects.new(PREFIX+'CAMERA',bpy.data.cameras.new(PREFIX+'CAMERA'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.clip_end=500
 scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True;scene.render.resolution_x=900;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
 a=math.radians(24.35);u=Vector((-math.cos(a),-math.sin(a),0));n=Vector((-math.sin(a),math.cos(a),0))
 def worldpoint(x,y,z):return u*x+n*y+Vector((0,0,z))
 cameras=[]
 for tag,target,offset,scale in [('front',(-160,70,12),(0,65,3),59),('side',(-135.2,42.25,12),(70,-18,4),44)]:
  focus=worldpoint(*target);camera.location=focus+u*offset[0]+n*offset[1]+Vector((0,0,offset[2]));camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale;scene.render.filepath=str(OUT/(label+'-'+tag+'.png'));bpy.ops.render.render(write_still=True);cameras.append(dict(name=tag,position=list(camera.location),target=list(focus),orthoScale=scale))
 bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for o in [camera,sun]:
  data=o.data;bpy.data.objects.remove(o,do_unlink=True)
  if isinstance(data,bpy.types.Camera):bpy.data.cameras.remove(data)
  else:bpy.data.lights.remove(data)
 bpy.data.scenes.remove(scene);bpy.data.worlds.remove(world);update();return cameras

def run():
 assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();before=state();assert len(before['objects'])==8074 and before['objects']==accepted_fingerprints(ROOT/'result/blender/stage228',SHA)
 protected=set().union(*(set(v)for v in before['rooms'].values()));assert not protected.intersection(TARGETS)
 cameras=preview('before');added=[];material_cache={};records=[]
 for name in TARGETS:
  original=bpy.data.objects[name];assert not original.hide_render
  clone=original.copy();clone.data=original.data.copy();clone.name=PREFIX+name;clone.data.name=clone.name;clone['originalObject']=name;clone['webGeometrySource']=original.get('webGeometrySource',name);clone['destinationCollection']=COLLECTION
  changed=0
  for i,m in enumerate(original.data.materials):
   if not m or not any(x in m.name.lower()for x in ['glaz','glass']):continue
   if m.name not in material_cache:
    new=m.copy();new.name=PREFIX+m.name;old=metrics(m);shader=next(n for n in new.node_tree.nodes if n.type=='BSDF_PRINCIPLED');assert not shader.inputs['Base Color'].is_linked
    tint=(.97,1.0,1.025);weight=sum(a*b for a,b in zip(tint,[.2126,.7152,.0722]));colour=tuple(old['luminance']*a/weight for a in tint)+(old['baseColor'][3],)
    shader.inputs['Base Color'].default_value=colour;new.diffuse_color=colour;new['colourBasis']='Neutral reflections in undated built photographs; uncalibrated hue estimate; accepted linear luminance and optics retained';newstate=metrics(new)
    assert abs(old['luminance']-newstate['luminance'])<1e-7 and newstate['saturation']<.06
    assert all(old[k]==newstate[k]for k in ['roughness','metallic','alpha','transmission','ior','webOpacity','webClosedGlazing'])
    records.append(dict(source=m.name,replacement=new.name,before=old,after=newstate));material_cache[m.name]=new
   clone.data.materials[i]=material_cache[m.name];changed+=1
  assert changed
  bpy.data.collections[COLLECTION].objects.link(clone);clone.hide_render=False;clone.hide_set(False);original.hide_render=True;original.hide_set(True);added.append(clone)
 update();verify(before,set(TARGETS));assert preview('after')==cameras
 fingerprints={o.name:object_fingerprint(o)for o in added};bindings={o.name:[m.name for m in o.data.materials]for o in added};component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True);component_sha=sha(component)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update();verify(before,set())
 with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(fingerprints)
 for o in dst.objects:
  bpy.data.collections[COLLECTION].objects.link(o)
  for i,m in enumerate(bindings[o.name]):o.data.materials[i]=bpy.data.materials[m]
  o.hide_render=False;o.hide_set(False)
 for name in TARGETS:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
 update();verify(before,set(TARGETS));assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert set(bpy.data.objects.keys())==set(before['objects'])|set(fingerprints)
 for o in dst.objects:
  original=bpy.data.objects[o['originalObject']];held=list(o.data.materials)
  for i,m in enumerate(original.data.materials):o.data.materials[i]=m
  assert object_fingerprint(o)==object_fingerprint(original)
  for i,m in enumerate(held):o.data.materials[i]=m
 assert sha(BASE)==SHA and sha(component)==component_sha
 reference=json.loads((ROOT/'data/collections/library_round5/sources.json').read_text())
 if isinstance(reference,dict):reference=reference.get('sources',reference.get('images',[]))
 refs=[]
 for row in reference:
  if row.get('id') in ['library_round5_SAL_5b39324ea103','library_round5_SAL_d0d696021ed0']:
   p=ROOT/row['local_file'];refs.append(dict(path=row['local_file'],url=row['url'],sha256=sha(p),photographCaptureDate='unknown',projectYear=2012,uploadPathDate='2024/01; not capture date',scope='Built historical windows and their environment-dependent reflections; no dimensions or current2026survey'))
 write(SOURCE/'sources.json',refs)
 verification=dict(savedComponentReopenedAndAppended=True,originalObjectsVerified=len(before['objects']),originalMaterialNodesVerified=len(before['materials']),originalModifierStacksVerified=len(before['modifiers']),protectedSpacesVerified=27,protectedSpaceObjectsVerified=1068,originalGeometryUVTransformsBindingsAndModifiersPreserved=True,originalMaterialNodeTreesPreserved=True,allOriginalCollectionMembershipsPreserved=True,protectedSpaceSceneMembershipsPreserved=True,clonedGeometryUVNormalsTransformsExact=True,allOriginalOpticalParametersPreserved=True,linearBrightnessPreserved=True,nonGlassStoneSlotPreserved=True,onlyListedOriginalVisibilityChanged=True,sourceFileShaUnchanged=True,sourcePhotographsNotUsedAsTextures=True,noFullNativeWritten=True,addedTrianglesNet=0)
 audit=dict(version=229,building='SAL',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=component_sha,targetCollection=COLLECTION,destinationCollection=COLLECTION,addedObjects=list(fingerprints),archivedObjects=TARGETS,changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,materials=records,references=refs,verification=verification,cameras=cameras,previews=['before-front.png','after-front.png','before-side.png','after-side.png'],scope='Reduce authored cyan-blue tint of two existing historical-window batches to near-neutral reflective grey, preserving accepted luminance and every optical parameter. Entrance pavilion, lantern glazing, frames, brick, stone and all interiors retained.',limitations=['Photographs are uncalibrated; this is a constrained visual hue estimate rather than measured glazing specification.','Photographed reflections depend on sky and surroundings; neutral material remains capable of reflecting blue sky.','2012projectyear and2024uploadpath do not establish photograph capture dates or current2026condition.','No change to existing opacity, transmission, backing, room openings, size or construction.'])
 audit['replacementOwnership']={n:dict(originalCollections=before['owners'][n],originalScenes=sorted(s.name for s in bpy.data.scenes if n in s.objects),integrationRule='Inherit every originalObject collection through the generic integrator')for n in TARGETS}
 audit['triangles']=sum(sum(len(p.vertices)-2 for p in o.data.polygons)for o in dst.objects)
 write(OUT/'audit.json',audit);write(OUT/'verification.json',verification);print('FACADE229_READY',component_sha,len(added),len(before['materials']),flush=True)
if __name__=='__main__':run()
