"""Correct Cowdray upper sashes and the projecting corner window casing.
Run in Blender Text Editor. Dimensions are photographic estimates.
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
OUT = ROOT / 'result/blender/stage76'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Facade, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v75.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
collection = bpy.data.collections['COW_EXTERIOR']

def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects}
owned = {o.name for o in collection.all_objects}
materials.clear()
# Copies isolate Cowdray from King's Chambers, which shares the original palette.
for key in ['frame', 'trim', 'stone', 'slate']:
    material = bpy.data.materials['HERITAGE09_' + key].copy()
    material.name = 'COW_V76_' + key
    materials[key] = material
slate = materials['slate']
slate.diffuse_color = (.060, .067, .068, 1)
slate.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = slate.diffuse_color
slate.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .87
recolored = []
for obj in list(collection.all_objects):
    if obj.type != 'MESH' or obj.hide_render:
        continue
    for index, material in enumerate(obj.data.materials):
        if material and material.name == 'HERITAGE09_slate':
            obj.data.materials[index] = slate
            recolored.append(obj.name)

# Keep vertical muntins, ground windows and attic windows; replace upper quarter rails.
obj = bpy.data.objects['COW_D5_sash_glazing_bar_frame']
mesh = bmesh.new()
mesh.from_mesh(obj.data)
seen, deleted, removed_horizontal = set(), [], 0
for vertex in list(mesh.verts):
    if vertex in seen:
        continue
    stack, component = [vertex], []
    seen.add(vertex)
    while stack:
        current = stack.pop()
        component.append(current)
        for edge in current.link_edges:
            other = edge.other_vert(current)
            if other not in seen:
                seen.add(other)
                stack.append(other)
    points = [obj.matrix_world @ v.co for v in component]
    low, high = min(v.z for v in points), max(v.z for v in points)
    if low > 5 and high < 18 and high - low < .04:
        deleted.extend(component)
        removed_horizontal += 1
bmesh.ops.delete(mesh, geom=deleted, context='VERTS')
mesh.to_mesh(obj.data)
mesh.free()
obj.data.update()
profile = next(p for p in json.loads((ROOT / 'result/blender/stage05/infill-geometry.json').read_text()) if p['code'] == 'COW')
groups, windows = {}, []
for wall in profile['walls']:
    if wall['party'] or wall['length'] < 1.8:
        continue
    facade = Facade(profile, wall, groups)
    count = max(1, round(facade.length / 2.85))
    pitch = facade.length / count
    for bottom, top in [(4.9, 9.6), (9.6, 14), (14, 18)]:
        low, high = bottom + .82, top - .63
        for index in range(count):
            x, width = (index + .5) * pitch, min(1.62, pitch * .61)
            windows.append({'wall': wall['index'], 'x': x, 'low': low, 'high': high, 'width': width})
            for fraction in [1/6, 1/3, 2/3, 5/6]:
                facade.box('joinery76_six_row_rail', 'frame', x, low + (high-low)*fraction, width, .025, .06, .045)
assert removed_horizontal == len(windows) * 2, (removed_horizontal, len(windows))

# The photographed first upper corner window has a deep sill, paired consoles
# and a layered projecting cornice. Keep its aperture and recessed sash intact.
front = Facade(profile, next(w for w in profile['walls'] if w['front']), groups)
x, low, high, width = front.length / 2, 5.72, 8.97, 1.62
hidden = ['COW_D5_corner_window_architrave_trim', 'COW_D5_corner_window_pediment_trim', 'COW_D5_corner_sill_bracket_stone']
for name in hidden:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for sign in [-1, 1]:
    for lateral, w, depth in [(width/2+.13, .20, .34), (width/2+.30, .14, .50)]:
        front.box('joinery76_corner_casing', 'trim', x+sign*lateral, (low+high)/2, w, high-low+.20, depth, .15)
    # Stepped consoles widen into the sill; no unverified carved floral texture.
    for z, w, depth in [(low-.63,.19,.33),(low-.49,.24,.43),(low-.34,.33,.55)]:
        front.box('joinery76_corner_console', 'stone', x+sign*.66, z, w, .15, depth, .20)
for z, w, h, depth, offset in [
    (low-.14,width+.72,.22,.70,.23),
    (low-.01,width+.59,.07,.62,.23),
    (high+.12,width+.60,.20,.51,.18),
    (high+.27,width+.79,.10,.63,.21),
    (high+.39,width+.98,.14,.78,.24),
    (high+.50,width+1.06,.08,.83,.25),
]:
    front.box('joinery76_corner_courses', 'trim', x, z, w, h, depth, offset)
added = []
for geometry in groups.values():
    obj = geometry.finish()
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    added.append(obj.name)
changed = [name for name, value in before.items() if fingerprint(bpy.data.objects[name]) != value]
assert all(name in owned for name in changed)
for filename in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    (OUT / filename).write_bytes((ROOT / 'result/blender/stage75' / filename).read_bytes())
audit = {
    'version': 76, 'baseline': 75, 'windowCount': len(windows),
    'removedHorizontalRails': removed_horizontal, 'addedHorizontalRails': len(windows)*4,
    'windows': windows, 'addedObjects': added, 'hiddenPreviousObjects': hidden,
    'recoloredObjects': recolored, 'changedExistingObjects': changed,
    'referenceUrl': 'https://www.russellcawberry.com/projects/cowdray-house',
    'reference': 'LSE Cowdray House contractor project photograph, 2019 project; exact capture date unknown',
    'limitations': ['Upper sash subdivisions and corner stone profiles photo-estimated; original window centres and floor heights retained', 'Roof geometry, dormer count, unseen elevations and exact dimensions remain unverified', 'All interiors retained; complete interior accuracy not established'],
}
(OUT / 'cowdray-joinery-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v76.blend'))
print('COWDRAY_JOINERY_SAVED', len(windows), removed_horizontal)
