"""Restore the photographed Clare Market planter's inset joints and thick coping.

Apply to an already loaded campus. Native soil/planting and the planter outline
register placement; joint spacing and the 120mm coping are photographic estimates.
No source geometry, materials or visibility outside the two replacements changes.
"""
from pathlib import Path
import json, math, hashlib
import bpy, bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ['OLD_NEXT_CLARE_sealed_window_head_stone', 'OLD_V53_Clare_edge']
NAMES = ['OLD_CLARE165_retained_facade_stone', 'OLD_CLARE165_retained_edge_stone', 'OLD_CLARE165_jointed_planter_stone']


def apply_old_planter_coping():
    if all(bpy.data.objects.get(n) for n in NAMES):
        return dict(addedObjects=[], archivedObjects=[], alreadyApplied=True)
    assert not any(bpy.data.objects.get(n) for n in NAMES)
    reg = json.loads((ROOT/'result/blender/old_facade_next/audit.json').read_text())['registration']
    origin, right, outward = [Vector(reg[k]) for k in ['origin', 'right', 'outward']]
    def local(p):
        return Vector(((p-origin).dot(right), (p-origin).dot(outward), p.z))
    def world(x, d, z):
        return origin + right*x + outward*d + Vector((0, 0, z))
    soil = bpy.data.objects['OLD_V53_Clare_soil']
    soil_points = [local(soil.matrix_world@v.co) for v in soil.data.vertices]
    left = min(p.x for p in soil_points)-.09
    end = max(p.x for p in soil_points)+.09
    # Derive the actual planter volume from the source's connected eight-vertex box.
    source = bpy.data.objects[SOURCES[0]]
    bm = bmesh.new(); bm.from_mesh(source.data)
    unseen = set(bm.verts); candidates = []
    while unseen:
        seed = unseen.pop(); group = {seed}; queue = [seed]
        while queue:
            for edge in queue.pop().link_edges:
                for v in edge.verts:
                    if v in unseen:
                        unseen.remove(v); group.add(v); queue.append(v)
        points = [local(source.matrix_world@v.co) for v in group]
        lo = [min(p[i] for p in points) for i in range(3)]
        hi = [max(p[i] for p in points) for i in range(3)]
        if len(group)==8 and abs(lo[0]-left)<.001 and abs(hi[0]-end)<.001 and hi[2]<1.1 and lo[1]>.2:
            candidates.append((lo, hi))
    bm.free(); assert len(candidates)==1, candidates
    lo, hi = candidates[0]
    left, end = lo[0], hi[0]; back, front = lo[1], hi[1]; bottom, top = lo[2], hi[2]
    assert .9 < top-bottom < 1.1
    collection = bpy.data.collections['OLD_EXTERIOR']; removed = {}
    for index, name in enumerate(SOURCES):
        src = bpy.data.objects[name]; clone = src.copy(); clone.data = src.data.copy()
        clone.name = NAMES[index]; clone.data.name = clone.name; collection.objects.link(clone)
        mesh = bmesh.new(); mesh.from_mesh(clone.data)
        selected = []
        for v in mesh.verts:
            p = local(clone.matrix_world@v.co)
            if index == 0:
                keep = left-.0002<=p.x<=end+.0002 and back-.0002<=p.y<=front+.0002 and bottom-.0002<=p.z<=top+.0002
            else:
                keep = left-.03<=p.x<=end+.03 and front-.015<=p.y<=front+.035 and bottom-.02<=p.z<=top+.02
            if keep: selected.append(v)
        assert len(selected) == (8 if index==0 else 80), (name,len(selected))
        removed[name] = len(selected)
        bmesh.ops.delete(mesh, geom=selected, context='VERTS'); mesh.to_mesh(clone.data); mesh.free()
        src.hide_render = True; src.hide_set(True)
    from facade_geometry import Geometry, materials
    materials['clare_planter165'] = source.data.materials[0]
    g = Geometry('OLD', 'clare_planter', 'clare_planter165'); g.name = NAMES[2]
    angle = math.atan2(right.y,right.x)
    def box(x0,x1,d0,d1,z0,z1):
        g.box(world((x0+x1)/2,(d0+d1)/2,(z0+z1)/2),(x1-x0,d1-d0,z1-z0),angle)
    # Backing retains the exact volume/soil support. Front face is separated into
    # real closed panels; gaps expose the recessed backing rather than black strips.
    inset = .012; coping = .12; seam = .012; gap = .008; panels = 11
    box(left,end,back,front-inset,bottom,top)
    for i in range(panels):
        x0=left+(end-left)*i/panels+(gap/2 if i else 0)
        x1=left+(end-left)*(i+1)/panels-(gap/2 if i<panels-1 else 0)
        box(x0,x1,front-inset,front,bottom,top-coping-seam)
        box(x0,x1,front-.18,front,top-coping,top)
    obj=g.finish()
    for mod in list(obj.modifiers):obj.modifiers.remove(mod)
    obj['reference']='data/collections/public-realm-2026/user-references/reference-04.png'
    obj['geometryScope']='Visible planter coping and recessed joints; thickness/spacing estimated, original bounds preserved.'
    for layer in bpy.context.scene.view_layers:layer.update()
    return dict(addedObjects=NAMES,archivedObjects=SOURCES,removedVertices=removed,
                registration=reg,planterBounds=[lo,hi],panels=panels,
                copingThickness=coping,horizontalJoint=seam,verticalJoint=gap,recess=inset,
                sourcePhoto=obj['reference'],sourcePhotoSha256=hashlib.sha256((ROOT/obj['reference']).read_bytes()).hexdigest(),photoDate='unknown',
                limitation='Existing native outline retained; segment count and joint/coping sizes are photo-guided estimates, not surveyed.')
