"""Adjust OLD's open plastic lattice from the supplied entrance photograph.
Run in Blender Text Editor. Keep the original mesh and its topology intact.
Thread thickness is a visual estimate; this does not reproduce a sculpture scan.
"""
from pathlib import Path
import array
import hashlib
import json
import shutil
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage111-old'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v110.blend'))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects}
records = []
for family, offset in [('figures', .0018), ('products', .002)]:
    source_name = 'OLD_D5_finalsale106_figures' if family == 'figures' else 'OLD_D5_finalsale84_products'
    source = bpy.data.objects[source_name]
    assert not source.hide_render and not source.modifiers
    source.data.update()
    copy = source.copy()
    copy.data = source.data.copy()
    copy.name = 'OLD_V111_lattice_' + family
    bpy.data.collections['OLD_EXTERIOR'].objects.link(copy)
    # Offset the already evaluated lattice surface. This thickens the existing
    # strands without adding grid subdivisions, closing holes or replacing it
    # with an opaque draped body. World metric offsets survive object transforms.
    inverse = copy.matrix_world.inverted().to_3x3()
    normal_matrix = copy.matrix_world.to_3x3().inverted().transposed()
    if family == 'figures':
        # Each retained strand is one quad with two endpoints and two sides.
        # Widen in the ribbon plane; normal displacement would only translate
        # these zero-thickness faces and leave their projected density unchanged.
        for polygon in source.data.polygons:
            assert len(polygon.vertices) == 4
            indices = list(polygon.vertices)
            for left, right_index in [(indices[0], indices[3]), (indices[1], indices[2])]:
                a = source.matrix_world @ source.data.vertices[left].co
                b = source.matrix_world @ source.data.vertices[right_index].co
                lateral = (b-a).normalized() * offset
                copy.data.vertices[left].co -= inverse @ lateral
                copy.data.vertices[right_index].co += inverse @ lateral
    else:
        for original, vertex in zip(source.data.vertices, copy.data.vertices):
            direction = (normal_matrix @ original.normal).normalized()
            vertex.co += inverse @ (direction * offset)
    copy.data.update()
    copy['scope'] = 'Photo-estimated plastic lattice strand thickness; retained six-figure poses and open mesh'
    copy['strandSurfaceOffset'] = offset
    source.hide_render = True
    source.hide_set(True)
    copy.hide_render = False
    copy.hide_set(False)
    records.append({'source': source.name, 'copy': copy.name, 'offset': offset,
                    'vertices': len(source.data.vertices), 'faces': len(source.data.polygons)})
assert all(fingerprint(bpy.data.objects[name]) == digest for name, digest in before.items())
for name in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    shutil.copyfile(ROOT / 'result/blender/stage110' / name, OUT / name)
audit = {'version': 111, 'baseline': 110, 'originalFingerprints': before, 'copies': records,
         'reference': 'User supplied Houghton entrance photograph received 2026-10-02; capture date unknown',
         'limits': ['Thread density is a photographic estimate, not a measured artwork mesh',
                    'Anatomy, full OLD roof, unseen elevations and complete interiors remain unresolved']}
(OUT / 'old-artwork-density-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v111.blend'))
print('OLD_ARTWORK_DENSITY_SAVED', records, flush=True)
