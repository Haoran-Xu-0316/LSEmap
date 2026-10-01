"""Round 51L's photographed corner while preserving original native objects.
Run in Blender Text Editor. Endpoints follow the retained GIS frontage; curvature
and dimensions are photo estimates. Planar entrance leaves retain their joinery.
"""
from pathlib import Path
import array, hashlib, json, math, shutil
import bpy, bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage96';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v93.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text()) if p['code']=='51L')
wall=profile['walls'][2];length=wall['length']
start=Vector((*wall['p'],0));end=Vector((*wall['q'],0))
right=(end-start).normalized();normal=Vector((*wall['outward'],0))
previous=profile['walls'][1];following=profile['walls'][3]
tangent_start=Vector((previous['q'][0]-previous['p'][0],previous['q'][1]-previous['p'][1],0)).normalized()
tangent_end=Vector((following['q'][0]-following['p'][0],following['q'][1]-following['p'][1],0)).normalized()
handle=length*.39052429175
controls=[start,start+tangent_start*handle,end-tangent_end*handle,end]
collection=bpy.data.collections['51L_EXTERIOR']
def fingerprint(obj):
    digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
def local(position):
    delta=position-start
    return Vector((delta.dot(right),delta.dot(normal),position.z))
def curve(x):
    if x<0:return start+tangent_start*x,tangent_start
    if x>length:return end+tangent_end*(x-length),tangent_end
    t=x/length;s=1-t
    position=controls[0]*s**3+controls[1]*3*s*s*t+controls[2]*3*s*t*t+controls[3]*t**3
    tangent=(controls[1]-controls[0])*3*s*s+(controls[2]-controls[1])*6*s*t+(controls[3]-controls[2])*3*t*t
    return position,tangent.normalized()
def curved_point(coords):
    position,tangent=curve(coords.x)
    outward=Vector((-tangent.y,tangent.x,0))
    return position+outward*coords.y+Vector((0,0,coords.z))
arc_samples=[curve(length*i/256)[0] for i in range(257)]
arc_lengths=[0]
for a,b in zip(arc_samples,arc_samples[1:]):arc_lengths.append(arc_lengths[-1]+(b-a).length)
def arc_distance(x):
    t=max(0,min(256,x/length*256));i=min(255,int(t))
    return arc_lengths[i]+(arc_lengths[i+1]-arc_lengths[i])*(t-i)
bow=(curve(length/2)[0]-(start+end)/2).dot(normal)
before={o.name:fingerprint(o) for o in bpy.data.objects}
records=[]
flat_tags=['oak_door_leaf','door_glazed_panel','door_lower_panel','door_panel_reed',
           'door_handle','door_recess','pediment_scroll','corner57_dark']
for source in list(collection.all_objects):
    if source.type!='MESH' or source.hide_render:continue
    bm=bmesh.new();bm.from_mesh(source.data);bm.verts.ensure_lookup_table()
    seen=set();curved=[];flat=[];parts=0
    for seed in list(bm.verts):
        if seed in seen:continue
        group=[];pending=[seed];seen.add(seed)
        while pending:
            vertex=pending.pop();group.append(vertex)
            for edge in vertex.link_edges:
                other=edge.other_vert(vertex)
                if other not in seen:seen.add(other);pending.append(other)
        points=[local(source.matrix_world@v.co) for v in group]
        center=sum(points,Vector())/len(points)
        if not(-.06<center.x<length+.06 and abs(center.y)<.38):continue
        if not all(-.16<p.x<length+.16 and -.43<p.y<.53 for p in points):continue
        if max(p.z for p in points)>21.05:continue
        planar=any(tag in source.name for tag in flat_tags)
        if 'corner57_stone' in source.name and max(p.z for p in points)<3.76:planar=True
        (flat if planar else curved).extend(group);parts+=1
    if not(curved or flat):bm.free();continue
    old_indices={v.index for v in curved+flat}
    retained=[tuple(v.co) for v in bm.verts if v.index not in old_indices]
    curved_faces=set(f for v in curved for f in v.link_faces)
    geometry=set(curved)|curved_faces|{e for v in curved for e in v.link_edges}
    inverse=source.matrix_world.inverted()
    plane_normal=(source.matrix_world.to_3x3().transposed()@right).normalized()
    # Slice across the frontage only: curvature needs no extra storey-height grid.
    for i in range(1,24):
        if not geometry:break
        result=bmesh.ops.bisect_plane(bm,geom=list(geometry),dist=1e-6,
            plane_co=inverse@(start+right*(length*i/24)),plane_no=plane_normal,
            clear_inner=False,clear_outer=False)
        geometry=set(result['geom'])
    curved_vertices={item for item in geometry if isinstance(item,bmesh.types.BMVert)}
    curved_faces={item for item in geometry if isinstance(item,bmesh.types.BMFace)}
    curved_vertices.update(v for f in curved_faces for v in f.verts)
    uv=bm.loops.layers.uv.active
    is_brick=any(m and any(n.type=='TEX_BRICK' for n in m.node_tree.nodes) for m in source.data.materials if m.use_nodes)
    coordinates={v:local(source.matrix_world@v.co) for v in curved_vertices}
    if is_brick and uv:
        for face in curved_faces:
            world_normal=source.matrix_world.to_3x3()@face.normal
            for loop in face.loops:
                p=coordinates[loop.vert]
                s=arc_distance(p.x)*(1+p.y/(length/math.sqrt(2)))
                loop[uv].uv=(s,p.y) if abs(world_normal.z)>.5 else ((p.y,p.z) if abs(world_normal.dot(right))>.5 else (s,p.z))
    for vertex,coords in coordinates.items():vertex.co=inverse@curved_point(coords)
    for vertex in flat:vertex.co=inverse@(source.matrix_world@vertex.co+normal*bow)
    copy=source.copy();copy.data=source.data.copy()
    copy.name='51L_D5_round96_'+source.name.removeprefix('51L_')
    collection.objects.link(copy)
    bm.normal_update();bm.to_mesh(copy.data);bm.free();copy.data.update()
    source.hide_render=True;source.hide_set(True)
    records.append({'source':source.name,'copy':copy.name,'parts':parts,
                    'curvedVertices':len(curved_vertices),'planarVertices':len(flat),
                    'retainedVertices':retained})
# Keep the original door lettering upright on the planar inset entrance.
label=bpy.data.objects.get('51L_V57_Entry_name')
if label and not label.hide_render:
    copy=label.copy();copy.data=label.data.copy();copy.name='51L_V96_Entry_name'
    collection.objects.link(copy);copy.location+=normal*bow
    label.hide_render=True;label.hide_set(True)
    records.append({'source':label.name,'copy':copy.name,'planarLabel':True})
# Fill only the small roof-edge crescent introduced by rounding the footprint.
outline=[curve(length*i/48)[0]+Vector((-curve(length*i/48)[1].y,curve(length*i/48)[1].x,0))*.03 for i in range(49)]
outline+=[end,start]
vertices=[tuple(p+Vector((0,0,z))) for z in [20.79,20.94] for p in outline]
count=len(outline)
faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
faces.extend((i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count))
mesh=bpy.data.meshes.new('51L_V96_roof_corner_crescent');mesh.from_pydata(vertices,[],faces);mesh.update()
mesh.materials.append(bpy.data.materials['51L_V93_slate'])
cap=bpy.data.objects.new(mesh.name,mesh);collection.objects.link(cap)
closed=bmesh.new();closed.from_mesh(mesh);bmesh.ops.recalc_face_normals(closed,faces=list(closed.faces));closed.to_mesh(mesh);closed.free()
assert records and all(fingerprint(bpy.data.objects[name])==value for name,value in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage93'/name,OUT/name)
if not(OUT/'catalogue-before.json').exists():shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
audit={'version':96,'baseline':93,'baselineFingerprint':before,'copies':records,'roofCap':cap.name,
       'frame':{'start':list(start),'end':list(end),'right':list(right),'normal':list(normal),'length':length},
       'controls':[list(v) for v in controls],'arcLength':arc_lengths[-1],'midpointBow':bow,
       'sourceUrl':'https://www.lse.ac.uk/global-school-of-sustainability/news/2025/first-recipients-Global-Sustainability-Research-Fund',
       'published':'2025-07-31','captureDate':None,
       'limitations':['Cubic corner curvature and dimensions are photo estimates, not a survey',
                      'Retained portal joinery remains planar; its exact installed geometry unverified',
                      'Other street-side windows, rear roof layout and complete interiors remain under review']}
(OUT/'lincolns-rounded-corner-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v96.blend'))
print('LINCOLNS_ROUNDED_CORNER_SAVED',len(records),bow,arc_lengths[-1],flush=True)
