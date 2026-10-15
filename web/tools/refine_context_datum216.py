"""Support existing mapped footways with the same flat presentation datum.

The old finite background ends before several verified surface footways. Extend
only its display rectangle from those existing meshes, retaining its elevation
and material. This is a map backdrop, never a new measured terrain survey.
"""
from pathlib import Path
import hashlib,json,math,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint
from refine_portsmouth_exterior207 import material_fingerprint
BASE=ROOT/'result/blender/LSE_campus_detailed_v215.blend';SHA='b6c726056d7e98dc229e1ac2dc1d01e7be35eb1835a28cd7a6bb88155a9c1a11'
OUT=ROOT/'result/blender/context-datum216';OUT.mkdir(parents=True,exist_ok=True)
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
originals={o.name:object_fingerprint(o) for o in bpy.data.objects};materials={m.name:material_fingerprint(m) for m in bpy.data.materials}
source_name='GROUND199_Local_ground_datum';source=bpy.data.objects[source_name];old=[source.matrix_world@v.co for v in source.data.vertices];assert not source.hide_render
points=[bpy.data.objects[n].matrix_world@v.co for n in ['SITE215_mapped_footway_body','SITE215_mapped_footway_edge'] for v in bpy.data.objects[n].data.vertices]
old_min=[min(p[i] for p in old) for i in range(2)];old_max=[max(p[i] for p in old) for i in range(2)]
new_min=[math.floor((min(p[i] for p in points)-5)/5)*5 if min(p[i] for p in points)<old_min[i] else old_min[i] for i in range(2)]
new_max=[math.ceil((max(p[i] for p in points)+5)/5)*5 if max(p[i] for p in points)>old_max[i] else old_max[i] for i in range(2)]
z=max(p.z for p in old);bottom=min(p.z for p in old);assert z<0 and bottom<z
assert old_min!=new_min or old_max!=new_max
name='SITE216_Expanded_flat_map_datum';mesh=bpy.data.meshes.new(name)
ring=[(new_min[0],new_min[1]),(new_max[0],new_min[1]),(new_max[0],new_max[1]),(new_min[0],new_max[1])]
mesh.from_pydata([(x,y,h) for h in [bottom,z] for x,y in ring],[],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);mesh.update()
bindings=[m.name for m in source.data.materials]
for m in source.data.materials:mesh.materials.append(m)
uv=mesh.uv_layers.new(name='MetricUV')
for loop in mesh.loops:uv.data[loop.index].uv=mesh.vertices[loop.vertex_index].co.xy
obj=bpy.data.objects.new(name,mesh);bpy.data.collections['00_SITE'].objects.link(obj);obj['originalObject']=source_name;obj['scope']='Flat display datum extended to support existing mapped footways; elevation unchanged, not surveyed terrain.'
assert all(object_fingerprint(bpy.data.objects[n])==f for n,f in originals.items());assert all(material_fingerprint(bpy.data.materials[n])==f for n,f in materials.items())
footway_outside_before=sum(not all(old_min[i]<=p[i]<=old_max[i] for i in range(2)) for p in points)
assert footway_outside_before>0
assert all(all(new_min[i]<=p[i]<=new_max[i] for i in range(2)) for p in points)
fingerprint=object_fingerprint(obj);component=OUT/'component.blend';bpy.data.libraries.write(str(component),{obj},fake_user=True,compress=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(component),link=False) as (_,target):target.objects=[name]
bpy.context.scene.collection.objects.link(target.objects[0]);assert object_fingerprint(target.objects[0])==fingerprint
record=dict(version=216,baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),targetCollection='00_SITE',addedObjects=[name],archivedObjects=[source_name],replacementMaterialBindings={name:bindings},oldBounds=dict(min=old_min,max=old_max),newBounds=dict(min=new_min,max=new_max),datumHeight=z,footwayVerticesChecked=len(points),footwayVerticesPreviouslyOutside=footway_outside_before,footwayVerticesNowOutside=0,originalObjectsVerified=len(originals),originalMaterialsVerified=len(materials),componentReopened=True,triangles=12,displayMarginMetres=5,scope='Extend only the flat background display boundary around the accepted mapped footway meshes. Do not change real road/path positions, terrain elevation, green areas or mapped structures.',limitations='The background rectangle and five-metre display margin are presentation choices, not mapped ground extent, slope or new terrain survey.')
(OUT/'audit.json').write_text(json.dumps(record,indent=2)+'\n');print('DATUM216_COMPONENT',record,flush=True)
