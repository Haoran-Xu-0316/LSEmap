"""Repair collapsed slate UVs in OLD/SAL without changing building geometry.

Tile dimensions are presentation estimates, not a measured roof survey.
"""
from pathlib import Path
import array, hashlib, json, shutil
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage28';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v27.blend'))
def geometry(obj):
    values=array.array('f',[0])*(3*len(obj.data.vertices));obj.data.vertices.foreach_get('co',values)
    indices=array.array('i',[0])*len(obj.data.loops);obj.data.loops.foreach_get('vertex_index',indices)
    return hashlib.sha256(values.tobytes()+indices.tobytes()).hexdigest()
before={o.name:geometry(o) for o in bpy.data.objects if o.type=='MESH'}
changes=[];copies={}
for code in ['OLD','SAL']:
    for obj in bpy.data.collections[code+'_EXTERIOR'].all_objects:
        if obj.type!='MESH':continue
        slots=[i for i,m in enumerate(obj.data.materials) if m and 'Weathered_slate' in m.name]
        if not slots:continue
        uv=obj.data.uv_layers.active or obj.data.uv_layers.new(name='Metric_roof_UV')
        faces=0
        for face in obj.data.polygons:
            if face.material_index not in slots:continue
            normal=face.normal.normalized()
            # Project onto an orthonormal basis in each roof plane. Horizontal
            # decks retain two dimensions; pitched roofs retain metric distances.
            u=Vector((0,0,1)).cross(normal)
            if u.length<1e-6:u=Vector((1,0,0))
            u.normalize();v=normal.cross(u).normalized()
            for index in face.loop_indices:
                point=obj.data.vertices[obj.data.loops[index].vertex_index].co
                uv.data[index].uv=(point.dot(u),point.dot(v))
            faces+=1
        for index in slots:
            old=obj.data.materials[index]
            if old.name not in copies:
                material=old.copy();material.name=old.name+'_roof28'
                for node in material.node_tree.nodes:
                    if node.type=='TEX_BRICK':
                        node.inputs['Mortar'].default_value=(.035,.043,.05,1)
                        node.inputs['Brick Width'].default_value=.30
                        node.inputs['Row Height'].default_value=.20
                        node.inputs['Mortar Size'].default_value=.003
                copies[old.name]=material
            obj.data.materials[index]=copies[old.name]
        changes.append({'code':code,'object':obj.name,'faces':faces})
assert before=={o.name:geometry(o) for o in bpy.data.objects if o.type=='MESH'}
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage27'/name,OUT/name)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v28.blend'))
(OUT/'roof-audit.json').write_text(json.dumps({'unchangedMeshGeometry':len(before),'changes':changes,'scope':'Slate UVs and joint colour only. Roof massing remains unverified; tile size is a presentation estimate.'},indent=2)+'\n')
print('ROOF_COMPLETE',len(changes),'objects;',len(before),'unchanged geometries')
