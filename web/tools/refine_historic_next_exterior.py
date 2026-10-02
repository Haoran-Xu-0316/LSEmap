"""Private CLM tall-window candidate from dated built photographs.
Run in Blender Text Editor. No exports or shared release metadata are changed.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage114/historic'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v113.blend'))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [v.vertex_index for v in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()
original = {o.name: fingerprint(o) for o in bpy.data.objects}
collection = bpy.data.collections['CLM_EXTERIOR']
archive = bpy.data.collections.new('CLM_ARCHIVE_PRE_TALL_WINDOWS')
bpy.context.scene.collection.children.link(archive)
replacements = []
# Remove complete independent construction pieces in the two mistaken window
# rows. Party-wall envelopes span this range and are intentionally retained.
for source in list(collection.all_objects):
    if source.type != 'MESH' or source.hide_render:
        continue
    if any(key in source.name for key in ['unobserved', 'rear_attic', 'mansard', 'GIS', 'slate']):
        continue
    mesh = bmesh.new()
    mesh.from_mesh(source.data)
    visited, selected, count = set(), [], 0
    for vertex in mesh.verts:
        if vertex in visited:
            continue
        pending, part = [vertex], []
        visited.add(vertex)
        while pending:
            current = pending.pop()
            part.append(current)
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other not in visited:
                    visited.add(other)
                    pending.append(other)
        heights = [(source.matrix_world @ v.co).z for v in part]
        if min(heights) >= 12.10 and max(heights) <= 18.91:
            selected.extend(part)
            count += 1
    if not selected:
        mesh.free()
        continue
    copy = source.copy()
    copy.data = source.data.copy()
    copy.name = 'CLM_V114_retained_' + source.name.removeprefix('CLM_')
    collection.objects.link(copy)
    bmesh.ops.delete(mesh, geom=selected, context='VERTS')
    mesh.to_mesh(copy.data)
    mesh.free()
    copy.data.update()
    archive.objects.link(source)
    for owner in list(source.users_collection):
        if owner != archive:
            owner.objects.unlink(source)
    source.hide_render = True
    source.hide_set(True)
    replacements.append({'source': source.name, 'copy': copy.name, 'removedParts': count})
assert any(r['source'] == 'CLM_D3_window_glass' for r in replacements)
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
record = next(b for b in site['buildings'] if b['code'] == 'CLM')
ring = record['rings'][0]
points = [Vector(ring[i]) for i in (5, 4, 3, 2, 1)]
centre = Vector(record['center'])
segments, length = [], 0
for a, b in zip(points, points[1:]):
    u = (b-a).normalized()
    n = Vector((u.y, -u.x))
    if n.dot((a+b)/2-centre) < 0:
        n = -n
    size = (b-a).length
    segments.append((length, length+size, a, u, n))
    length += size
materials.clear()
materials['stone'] = bpy.data.materials['CLM_D3_Portland_stone']
materials['metal'] = bpy.data.materials['CLM_D3_bronze_or_dark_painted_metal']
materials['glass'] = bpy.data.objects['CLM_D3_window_glass'].data.materials[0]
batches = {}
def point(s, d, z):
    start, end, a, u, n = next((p for p in segments if s <= p[1]), segments[-1])
    xy = a + u*(s-start) + n*d
    return Vector((xy.x, xy.y, z))
def box(key, family, s, d, z, w, depth, h):
    identity = key+'_'+family
    if identity not in batches:
        batches[identity] = Geometry('CLM', 'tall114_'+identity, key)
    batch = batches[identity]
    vertices = [point(s+x*w/2, d+y*depth/2, z+k*h/2) for x,y,k in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    batch.add(vertices, [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])
# Keep existing metric floor bounds. These are inherited estimates; the evidence
# supports morphology, seven bays and uninterrupted tall openings, not heights.
bay = length/7
low, high, width = 12.80, 18.36, 2.10
windows = []
for i in range(7):
    s = (i+.5)*bay
    for sign in [-1,1]:
        edge = s+sign*(width+bay)/4
        box('stone', 'piers', edge, -.13, 15.50, (bay-width)/2, .27, 6.60)
    for a,b in [(12.20,low),(high,18.80)]:
        box('stone', 'spandrels', s, -.13, (a+b)/2, width, .27, b-a)
    box('glass', 'panes', s, -.18, (low+high)/2, width, .042, high-low)
    for sign in [-1,1]:
        box('metal', 'frames', s+sign*width/2, -.14, (low+high)/2, .075, .10, high-low+.12)
        box('metal', 'frames', s, -.14, (low+high)/2+sign*(high-low)/2, width+.08, .10, .075)
    for j in range(1,3):
        box('metal', 'mullions', s-width/2+j*width/3, -.125, (low+high)/2, .038, .075, high-low)
    for j in range(1,8):
        z = low+j*(high-low)/8
        box('metal', 'bars', s, -.11, z, width, .06, .028 if j != 4 else .12)
    box('stone', 'sills', s, .13, low-.08, width+.32, .48, .15)
    windows.append({'bay': i, 's': s, 'low': low, 'high': high, 'width': width, 'columns': 3, 'rows': 8})
# Continuous narrow balcony below the tall openings; curved along GIS frontage.
for j in range(64):
    s = (j+.5)*length/64
    box('stone', 'balcony_deck', s, .40, 12.20, length/64+.006, 1.08, .17)
    box('metal', 'balcony_rail', s, .91, 13.15, length/64+.006, .035, .045)
for j in range(85):
    s = j*length/84
    box('metal', 'balcony_posts', s, .91, 12.72, .024, .03, .83)
added = []
for geometry in batches.values():
    obj = geometry.finish()
    obj.modifiers.clear()
    added.append(obj.name)
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
assert all(fingerprint(bpy.data.objects[name]) == prior for name, prior in original.items())
audit = {'baseline':113,'candidate':'CLM tall-window morphology','originalsRetained':True,'otherBuildingsRetained':True,'replacements':replacements,'addedObjects':added,'windows':windows,'scope':'Replace two equal upper window rows with seven uninterrupted tall openings and shallow balcony; retain roof, lower portal and other buildings','sources':[{'path':'result/blender/stage73/clm-2018.jpg','captureDate':'2018-04-24'},{'path':'result/blender/stage73/clm-2023.jpg','captureDate':'2023-11-15'},{'url':'https://historicengland.org.uk/listing/the-list/list-entry/1066494','supports':'Seven bays, convex frontage, Portland stone and bronze windows'}],'limitations':['Not an as-built 2026 survey','Floor bounds retained from estimated study; window proportions and railing construction estimated','Figure relief and central ornamental surrounds still absent','No claim of correct rear roof, complete elevations or full interiors']}
(OUT/'historic-candidate-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'CLM_tall_windows_candidate.blend'))
print('CLM_TALL_WINDOW_CANDIDATE_SAVED',len(replacements),len(added),flush=True)
