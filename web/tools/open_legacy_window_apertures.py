"""Cut native window openings where legacy glass backs coincide with solid walls.

Uses existing pane geometry, not inferred new windows. Runs in Blender's Text
Editor. Repair is limited to rectangular legacy wall sheets and preserves all
frames, glazing, authored palettes and public-interior geometry.
"""
from pathlib import Path
from collections import defaultdict
import array,hashlib,json,shutil
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage34';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v33.blend'))
def fingerprint(o):
    v=array.array('f',[0])*(3*len(o.data.vertices));o.data.vertices.foreach_get('co',v)
    i=array.array('i',[0])*len(o.data.loops);o.data.loops.foreach_get('vertex_index',i)
    return hashlib.sha256(v.tobytes()+i.tobytes()).hexdigest()
before={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}

def connected_bounds(obj):
    parent=list(range(len(obj.data.vertices)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for edge in obj.data.edges:
        a,b=edge.vertices;parent[root(a)]=root(b)
    groups=defaultdict(list)
    for v in obj.data.vertices:groups[root(v.index)].append(obj.matrix_world@v.co)
    return list(groups.values())

changes=[]
for collection in bpy.data.collections:
    if not collection.name.endswith('_EXTERIOR'):continue
    panes=[]
    for obj in collection.objects:
        if obj.type=='MESH' and 'Glazing_bays' in obj.name and any(m and 'glazing' in m.name.lower() for m in obj.data.materials):panes.extend(connected_bounds(obj))
    if not panes:continue
    for obj in list(collection.objects):
        if obj.type!='MESH' or '_wall_' not in obj.name or len(obj.data.vertices)!=4:continue
        points=[obj.matrix_world@v.co for v in obj.data.vertices]
        normal=(obj.matrix_world.to_3x3().inverted().transposed()@obj.data.polygons[0].normal).normalized()
        if abs(normal.z)>.001:continue
        origin=points[0];u=Vector((-normal.y,normal.x,0));up=Vector((0,0,1))
        project=lambda p:((p-origin).dot(u),(p-origin).dot(up),(p-origin).dot(normal))
        wall=[project(p) for p in points];xmin,xmax=min(p[0] for p in wall),max(p[0] for p in wall);zmin,zmax=min(p[1] for p in wall),max(p[1] for p in wall)
        if (xmax-xmin)<1 or max(abs(p[2]) for p in wall)>.002:continue
        holes=[]
        for pane in panes:
            p=[project(v) for v in pane];depth=[v[2] for v in p]
            if min(depth)>.012 or max(depth)<-.012 or max(depth)-min(depth)>.20:continue
            # Clearance stays beneath the authored jamb overlap, avoiding Draco edge noise.
            left=max(xmin,min(v[0] for v in p)-.008);right=min(xmax,max(v[0] for v in p)+.008)
            bottom=max(zmin,min(v[1] for v in p)-.008);top=min(zmax,max(v[1] for v in p)+.008)
            if right-left<.3 or top-bottom<.3:continue
            holes.append((left,right,bottom,top))
        if not holes:continue
        xs=sorted(set([xmin,xmax]+[v for h in holes for v in h[:2]]));zs=sorted(set([zmin,zmax]+[v for h in holes for v in h[2:]]))
        vertices=[];faces=[];uvs=[];removed_area=0
        inverse=obj.matrix_world.inverted()
        for left,right in zip(xs,xs[1:]):
            if right-left<1e-5:continue
            for bottom,top in zip(zs,zs[1:]):
                if top-bottom<1e-5:continue
                midx,midz=(left+right)/2,(bottom+top)/2
                if any(a<=midx<=b and c<=midz<=d for a,b,c,d in holes):removed_area+=(right-left)*(top-bottom);continue
                base=len(vertices)
                corners=[(left,bottom),(right,bottom),(right,top),(left,top)]
                vertices.extend(inverse@(origin+u*x+up*z) for x,z in corners)
                faces.append(tuple(range(base,base+4)))
                uvs.extend((x,origin.z+z) for x,z in corners)
        assert 0<removed_area<(xmax-xmin)*(zmax-zmin)*.85,obj.name
        mesh=bpy.data.meshes.new(obj.name+'_openings');mesh.from_pydata(vertices,[],faces)
        for material in obj.data.materials:mesh.materials.append(material)
        mesh.update();uv=mesh.uv_layers.new(name='SurfaceUV')
        for i,value in enumerate(uvs):uv.data[i].uv=value
        obj.data=mesh
        changes.append({'object':obj.name,'building':collection.name.split('_')[0],'openings':len(holes),'removedWallArea':removed_area,'wallFaces':len(faces)})
after={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
assert set(name for name in before if before[name]!=after[name])==set(c['object'] for c in changes)
assert set(c['building'] for c in changes)=={'CKK','LRB','CON'}
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage33'/name,OUT/name)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v34.blend'))
(OUT/'window-aperture-audit.json').write_text(json.dumps({'changes':changes,'unchangedMeshes':len(before)-len(changes),'clearance':.008,'scope':'Openings follow existing panes; no changes to their positions, colours, frames or public interiors.'},indent=2)+'\n')
print('WINDOW_APERTURES_COMPLETE',len(changes),sum(c['openings'] for c in changes))
