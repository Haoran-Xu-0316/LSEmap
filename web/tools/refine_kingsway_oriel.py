"""Curve KSW's photographed central oriel, preserving other building geometry.
Run in Blender's Text Editor. The arc is photo guided, not a measured survey.
"""
from pathlib import Path
import bpy,bmesh,json,math,hashlib,array
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage54';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v53.blend'))
def digest(obj):
    h=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    return h.hexdigest()
before={o.name:digest(o)for o in bpy.data.objects}
ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings']if b['code']=='KSW')['rings'][0]
a,b=Vector((*ring[11],0)),Vector((*ring[0],0));origin=(a+b)/2;right=(b-a).normalized();normal=Vector((right.y,-right.x,0))
center=Vector((*next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings']if b['code']=='KSW')['center'],0))
if (origin-center).dot(normal)<0:normal=-normal
stone=bpy.data.materials['KSW_D3_Portland_stone']
changes=[];total_parts=0
for obj in list(bpy.data.collections['KSW_EXTERIOR'].all_objects):
    if obj.type!='MESH' or obj.hide_render or not obj.name.startswith('KSW_D3_'):continue
    name=obj.name
    if not any(key in name for key in ['window','recess_shadow','oriel','brick_lower_spandrels','upper_brick_spandrels']):continue
    bm=bmesh.new();bm.from_mesh(obj.data);seen=set();selected=[];stone_faces=[];offsets={};parts=0
    for seed in list(bm.verts):
        if seed in seen:continue
        stack=[seed];component=[];seen.add(seed)
        while stack:
            v=stack.pop();component.append(v)
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other not in seen:seen.add(other);stack.append(other)
        points=[obj.matrix_world@v.co-origin for v in component]
        xs=[p.dot(right)for p in points];zs=[p.z for p in points]
        if min(zs)<5.25 or max(zs)>19.82 or max(abs(x)for x in xs)>1.32:continue
        mid=(min(xs)+max(xs))/2
        # Ordinary neighbouring bays never enter this central envelope.
        if abs(mid)>1.01:continue
        faces=set(f for v in component for f in v.link_faces)
        selected.extend(component);parts+=1
        upper=min(zs)>9.0
        offset=0
        if upper and any(k in name for k in ['stone_window_architraves','projecting_window_sills','window_head_mouldings']):offset=.31
        if not upper and 'brick_lower_spandrels' in name:offset=.48
        for v in component:offsets[v]=offset
        if upper and 'upper_brick_spandrels' in name:stone_faces.extend(faces)
    if not selected:bm.free();continue
    # Subdivision creates genuine curved surfaces instead of a bent four-corner box.
    edges=list({e for v in selected for e in v.link_edges})
    result=bmesh.ops.subdivide_edges(bm,edges=edges,cuts=7,use_grid_fill=True)
    new_verts={v for v in selected}
    for item in result['geom_inner']+result['geom_split']:
        if isinstance(item,bmesh.types.BMVert):new_verts.add(item)
        elif isinstance(item,bmesh.types.BMFace):new_verts.update(item.verts)
    inverse=obj.matrix_world.inverted()
    for v in new_verts:
        if not v.is_valid:continue
        p=obj.matrix_world@v.co-origin;x=p.dot(right)
        # Circular sagitta: 1.65m estimated radius, 0.32m central bow.
        bow=math.sqrt(max(0,1.65**2-x*x))-1.65+.32
        upper=p.z>9.0
        offset=.31 if upper and any(k in name for k in ['stone_window_architraves','projecting_window_sills','window_head_mouldings']) else .48 if not upper and 'brick_lower_spandrels' in name else 0
        v.co=inverse@(origin+p+normal*(bow+offset))
    if stone_faces:
        if stone.name not in [m.name for m in obj.data.materials]:obj.data.materials.append(stone)
        idx=list(obj.data.materials).index(stone)
        for face in bm.faces:
            coords=[obj.matrix_world@v.co-origin for v in face.verts]
            if min(p.z for p in coords)>9 and max(abs(p.dot(right))for p in coords)<1.32:face.material_index=idx
    bm.normal_update();bm.to_mesh(obj.data);bm.free();obj.data.update();changes.append({'name':name,'parts':parts,'vertices':len(obj.data.vertices)});total_parts+=parts
changed=[name for name,prior in before.items()if digest(bpy.data.objects[name])!=prior]
assert changed and all(name.startswith('KSW_D3_')for name in changed),changed
for name in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/name).write_bytes((ROOT/'result/blender/stage53'/name).read_bytes())
audit={'version':54,'baseline':53,'changedExistingObjects':changed,'changedOtherObjects':[n for n in changed if not n.startswith('KSW_')],'components':changes,'curvedParts':total_parts,'radius':1.65,'centerBow':.32,'reference':'data/建筑图片/KSW_20 Kingsway/01_建筑实拍/exteriors_lse_estate_009.jpg','limitations':['Undated estate street photograph; curvature dimensions estimated, not surveyed','Roof and unseen elevations remain unverified','No interior changes in this exterior pass']}
(OUT/'kingsway-oriel-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v54.blend'))
print('KSW_ORIEL_SAVED',len(changed),total_parts)
