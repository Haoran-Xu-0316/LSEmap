"""Restore missing metric brick UVs on the KSW exterior.

Keep authored red-brick colours and all geometry. The street elevation photo
lse_estate_009 confirms red brick rather than the brown mortar-only web result.
"""
from pathlib import Path
import array,hashlib,json,shutil
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage29';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v28.blend'))
def geometry(obj):
    values=array.array('f',[0])*(3*len(obj.data.vertices));obj.data.vertices.foreach_get('co',values)
    indices=array.array('i',[0])*len(obj.data.loops);obj.data.loops.foreach_get('vertex_index',indices)
    return hashlib.sha256(values.tobytes()+indices.tobytes()).hexdigest()
before={o.name:geometry(o) for o in bpy.data.objects if o.type=='MESH'}
changes=[]
for obj in bpy.data.collections['KSW_EXTERIOR'].all_objects:
    if obj.type!='MESH':continue
    if not any(m and m.use_nodes and any(n.type=='TEX_BRICK' for n in m.node_tree.nodes) for m in obj.data.materials):continue
    assert not obj.data.uv_layers, 'Do not replace existing authored UVs'
    layer=obj.data.uv_layers.new(name='Metric_brick_UV')
    for face in obj.data.polygons:
        normal=face.normal.normalized()
        u=Vector((0,0,1)).cross(normal)
        if u.length<1e-6:u=Vector((1,0,0))
        u.normalize();v=normal.cross(u).normalized()
        for index in face.loop_indices:
            point=obj.data.vertices[obj.data.loops[index].vertex_index].co
            layer.data[index].uv=(point.dot(u),point.dot(v))
        # Every exported brick face must have positive texture area.
        points=[layer.data[i].uv.copy() for i in face.loop_indices]
        area=abs(sum(a.x*b.y-b.x*a.y for a,b in zip(points,points[1:]+points[:1])))/2
        assert area>1e-8,(obj.name,face.index,area)
    layer.active_render=True
    changes.append({'object':obj.name,'faces':len(obj.data.polygons),'uvLayer':layer.name})
assert len(changes)==7
assert before=={o.name:geometry(o) for o in bpy.data.objects if o.type=='MESH'}
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage28'/name,OUT/name)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v29.blend'))
(OUT/'kingsway-brick-audit.json').write_text(json.dumps({'unchangedMeshGeometry':len(before),'changes':changes,'evidence':'data/collections/exteriors/images/lse_estate_009.jpg','scope':'Missing exterior UVs only. Existing photo-estimated dimensions and authored materials retained.'},indent=2)+'\n')
print('KSW_UV_COMPLETE',len(changes),'objects;',len(before),'unchanged geometries')
