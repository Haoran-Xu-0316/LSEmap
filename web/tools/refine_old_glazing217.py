"""Neutral photographic OLD glazing while retaining blue painted joinery.

Fixed Blender Text Editor authoring. The accepted complete native and original
nodes/meshes/UVs remain intact; only independent glass copies may be published.
"""
from pathlib import Path
import array
import hashlib
import json
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v216.blend'
SHA='12376d6365bbc57fa9eec97617453dbbfcf9235a8200bb90726f80c2147c1a60'
OUT=ROOT/'result/blender/old-glazing217'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints
from refine_portsmouth_exterior207 import material_fingerprint

def update():
 for scene in bpy.data.scenes:
  for layer in scene.view_layers:layer.update()

def inspect():
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
 expected=accepted_fingerprints(ROOT/'result/blender/stage216',SHA)
 actual={o.name:object_fingerprint(o)for o in bpy.data.objects}
 mismatches=[n for n in set(actual)|set(expected)if actual.get(n)!=expected.get(n)]
 assert not mismatches,mismatches[:20]
 collection=bpy.data.collections['OLD_EXTERIOR'];rows=[]
 for obj in collection.all_objects:
  if obj.type!='MESH'or obj.hide_render:continue
  if not any('glass'in m.name.lower()or'glazing'in m.name.lower()for m in obj.data.materials if m):continue
  mats=[]
  for m in obj.data.materials:
   shader=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
   mats.append(dict(name=m.name,color=list(shader.inputs['Base Color'].default_value)if shader else None,linked=shader.inputs['Base Color'].is_linked if shader else None,roughness=shader.inputs['Roughness'].default_value if shader else None,metallic=shader.inputs['Metallic'].default_value if shader else None,alpha=shader.inputs['Alpha'].default_value if shader else None,transmission=shader.inputs['Transmission Weight'].default_value if shader else None,properties=dict(m.items())))
  rows.append(dict(name=obj.name,materials=mats,faceSlots={str(i):sum(f.material_index==i for f in obj.data.polygons)for i in range(len(mats))},vertices=len(obj.data.vertices),faces=len(obj.data.polygons)))
 (OUT/'inspection.json').write_text(json.dumps(dict(acceptedFingerprintsVerified=len(actual),sourceModelSha256=SHA,glassObjects=rows),indent=2)+'\n')
 print('OLDGLASS217_ACCEPTED_INSPECTION',len(actual),len(rows),flush=True)

SOURCES=[
 'GLASS181_OLD_V112_entry_D5_portal78_pane_glass',
 'GLASS181_OLD_V112_entry_D5_portal79_Window_glazing',
 'GLASS181_OLD_V112_entry_Window_glazing',
]

def material_metrics(material):
 shader=next(node for node in material.node_tree.nodes if node.type=='BSDF_PRINCIPLED')
 color=list(shader.inputs['Base Color'].default_value)
 luminance=sum(c*w for c,w in zip(color,[.2126,.7152,.0722]))
 saturation=(max(color[:3])-min(color[:3]))/max(color[:3])
 return dict(color=color,linearLuminance=luminance,linearSaturation=saturation,
             alpha=float(shader.inputs['Alpha'].default_value),transmission=float(shader.inputs['Transmission Weight'].default_value),roughness=float(shader.inputs['Roughness'].default_value),metallic=float(shader.inputs['Metallic'].default_value),webOpacity=material.get('webOpacity'),webClosedGlazing=material.get('webClosedGlazing'))


def backing_probes():
 """Ray behind real glass centres, excluding all glass from opaque evidence."""
 objects=[];vertices=[];faces=[];owners=[]
 for obj in bpy.data.collections['OLD_EXTERIOR'].all_objects:
  if obj.type!='MESH'or obj.hide_render:continue
  if any('glass'in m.name.lower()or'glazing'in m.name.lower()for m in obj.data.materials if m):continue
  start=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
  faces.extend(tuple(start+i for i in face.vertices)for face in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 tree=BVHTree.FromPolygons(vertices,faces)
 outward=Vector((.890279,-.455415,0));rows=[]
 for name in SOURCES:
  source=bpy.data.objects[name]
  for face in source.data.polygons:
   normal=(source.matrix_world.to_3x3().inverted().transposed()@face.normal).normalized()
   if normal.dot(outward)<.95:continue
   centre=sum((source.matrix_world@source.data.vertices[i].co for i in face.vertices),Vector())/len(face.vertices)
   hit=tree.ray_cast(centre-normal*.01,-normal,40)
   owner=owners[hit[2]]if hit[2]is not None else None
   distance=hit[3]+.01 if hit[2]is not None else None
   rows.append(dict(glassObject=name,faceIndex=face.index,centre=list(centre),inward=list(-normal),firstOpaqueSurface=owner,distanceMetres=distance,nearBacking=distance is not None and distance<=1.5))
 assert rows
 return dict(method='Actual front-facing pane centroids; all glazing batches excluded from the opaque ray tree',samples=len(rows),nearBackingSamples=sum(row['nearBacking']for row in rows),rows=rows,interpretation='Opaque glazing proxies are retained. Missing or distant inner surfaces do not justify making the facade transparent; no invented interior/backing is added.')


def render_review(label):
 import math
 scene=bpy.data.scenes.new('OLDGLASS217_REVIEW_'+label)
 collection=bpy.data.collections['OLD_EXTERIOR'];scene.collection.children.link(collection)
 world=bpy.data.worlds.new(scene.name);world.use_nodes=True
 world.node_tree.nodes['Background'].inputs['Color'].default_value=(.82,.85,.88,1)
 world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65;scene.world=world
 light=bpy.data.lights.new(scene.name+'_sun','SUN');light.energy=1.6;light.angle=.12
 sun=bpy.data.objects.new(light.name,light);scene.collection.objects.link(sun)
 sun.rotation_euler=Vector((-.6,.5,-1)).to_track_quat('-Z','Y').to_euler()
 data=bpy.data.cameras.new(scene.name+'_camera');camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera);scene.camera=camera
 camera.location=Vector((14.206281663142814,-98.12818885723478,6.491428417478289))
 target=Vector((-5.152934221736798,-89.86124290037375,6.007142780167715))
 camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
 data.sensor_fit='VERTICAL';data.lens=data.sensor_height/(2*math.tan(math.radians(42)/2));data.clip_end=500
 scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=32
 scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
 scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/(label+'-houghton.png'))
 bpy.ops.render.render(write_still=True,scene=scene.name)
 for obj in [camera,sun]:bpy.data.objects.remove(obj,do_unlink=True)
 bpy.data.scenes.remove(scene);bpy.data.worlds.remove(world)
 bpy.data.cameras.remove(data);bpy.data.lights.remove(light)
 bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()


def run():
 inspect()
 originals={o.name:object_fingerprint(o)for o in bpy.data.objects}
 material_states={m.name:material_fingerprint(m)for m in bpy.data.materials}
 visibility={o.name:o.hide_render for o in bpy.data.objects}
 backings=backing_probes()
 (OUT/'backing-rays.json').write_text(json.dumps(backings,indent=2)+'\n')
 render_review('before')
 owned=[];bindings={};material_records=[];new_materials={}
 for source_name in SOURCES:
  source=bpy.data.objects[source_name];assert not source.hide_render
  clone=source.copy();clone.data=source.data.copy();clone.name='OLDGLASS217_'+source_name;clone.data.name=clone.name
  clone['originalObject']=source_name;clone['destinationCollection']='OLD_EXTERIOR'
  clone['scope']='Only photographed Houghton glazed panes; blue painted frames, door/artwork glass and unseen elevations retained'
  for index,source_material in enumerate(source.data.materials):
   if not any(face.material_index==index for face in source.data.polygons):continue
   if source_material.name not in new_materials:
    before=material_metrics(source_material)
    material=source_material.copy();material.name='OLDGLASS217_glass_neutral_'+source_material.name
    shader=next(node for node in material.node_tree.nodes if node.type=='BSDF_PRINCIPLED');assert not shader.inputs['Base Color'].is_linked
    # Preserve linear brightness and a restrained cool residual hue. This is
    # a photographic finish estimate, not a colour-calibrated glass product.
    tint=(.96,1.005,1.04);weight=sum(v*w for v,w in zip(tint,[.2126,.7152,.0722]))
    color=tuple(before['linearLuminance']*v/weight for v in tint)+(before['color'][3],)
    shader.inputs['Base Color'].default_value=color;material.diffuse_color=color
    material['finishScope']='Neutral smoke-grey reflective glazing; finite original opacity and all original PBR optics retained'
    material['colourBasis']='Undated private Houghton photographs; hue is an uncalibrated visual estimate, linear luminance preserved'
    after=material_metrics(material)
    assert abs(after['linearLuminance']-before['linearLuminance'])<1e-7
    assert after['linearSaturation']<before['linearSaturation']*.3
    for key in ['alpha','transmission','roughness','metallic','webOpacity','webClosedGlazing']:assert before[key]==after[key],key
    new_materials[source_material.name]=material
    material_records.append(dict(source=source_material.name,replacement=material.name,before=before,after=after))
   clone.data.materials[index]=new_materials[source_material.name]
  bpy.data.collections['OLD_EXTERIOR'].objects.link(clone);clone.hide_render=False;clone.hide_set(False)
  bindings[clone.name]=[m.name for m in clone.data.materials]
  source.hide_render=True;source.hide_set(True);owned.append(clone)
 update()
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in material_states.items())
 fingerprints={o.name:object_fingerprint(o)for o in owned}
 render_review('after')
 component=OUT/'old-glazing217-component.blend'
 bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
 expected=accepted_fingerprints(ROOT/'result/blender/stage216',SHA)
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in expected.items())
 with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(fingerprints)
 for obj in loaded.objects:
  for index,name in enumerate(bindings[obj.name]):obj.data.materials[index]=bpy.data.materials[name]
  bpy.data.collections['OLD_EXTERIOR'].objects.link(obj);obj.hide_render=False;obj.hide_set(False)
 for name in SOURCES:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
 update()
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in expected.items())
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in material_states.items())
 assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items()if n not in SOURCES)
 for obj in loaded.objects:
  source=bpy.data.objects[obj['originalObject']]
  for field,key,kind,count in [(source.data.vertices,'co','f',3),(source.data.loops,'vertex_index','i',1)]:
   a=array.array(kind,[0])*(len(field)*count);field.foreach_get(key,a)
   target=getattr(obj.data,'vertices'if key=='co'else'loops');b=array.array(kind,[0])*len(a);target.foreach_get(key,b);assert a==b
  assert len(obj.data.uv_layers)==len(source.data.uv_layers)
  for left,right in zip(source.data.uv_layers,obj.data.uv_layers):
   a=array.array('f',[0])*(len(left.data)*2);b=array.array('f',[0])*len(a);left.data.foreach_get('uv',a);right.data.foreach_get('uv',b);assert a==b
 references=[]
 for path in ['data/collections/old-exterior-2026/user-references/houghton-entrance-latest.png','data/collections/old-user-reference/houghton-entrance-user-20261002.png']:
  references.append(dict(path=path,sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),captureDate='unknown',distribution='Private visual evidence only; no public photo texture'))
 verification=dict(savedComponentReopened=True,precedingAcceptedFingerprintsVerified=len(expected),originalObjectsVerified=len(originals),originalMaterialsVerified=len(material_states),originalGeometryUVBindingsAndMaterialNodesPreserved=True,allBlueFramesUnchanged=True,allDoorAndArtworkGlassUnchanged=True,glassTopologyTransformAndUVExact=True,originalOpticalParametersAndOpacityUnchanged=True,unrelatedVisibilityPreserved=True,sourceModelUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA)
 audit=dict(version=217,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),targetCollection='OLD_EXTERIOR',destinationCollection='OLD_EXTERIOR',addedObjects=list(fingerprints),archivedObjects=SOURCES,changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,materials=material_records,backingEvidence=dict(path=str((OUT/'backing-rays.json').relative_to(ROOT)),samples=backings['samples'],nearBackingSamples=backings['nearBackingSamples']),references=references,verification=verification,previews=['before-houghton.png','after-houghton.png'],lighting='Identical1000x800 EEVEE32sample neutral sky.65 and sun1.6, AgX, same42degree gallery camera; source materials, no reference photo pixels',scope='Three photographed Houghton entrance-window batches only. Neutral reflective grey distinguishes panes from untouched blue painted joinery.',limitations=['Colour values are visual estimates from undated, uncalibrated photographs, not measured product specifications.','Opaque legacy glazing proxies retain alpha1/transmission0 because a complete interior/backing is not established.','No additional panes, UVs, geometry, transparent layers, glazing distortion or invented rooms are added.','Browser PMREM/lighting influences reflected sky colour; this change corrects authored glass hue rather than claiming a photographic colour match.'])
 (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
 print('OLDGLASS217_COMPONENT_REOPENED',len(fingerprints),len(expected),backings['nearBackingSamples'],'/',backings['samples'],flush=True)
if __name__=='__main__':run()
