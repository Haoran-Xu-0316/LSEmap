"""Reopen the saved full campus; independently check every retained window face."""
from pathlib import Path
import hashlib, json, sys
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_architectural_glass import shape_signature
from refine_old_lettering185 import font_signature
from refine_rooms import geometry_signatures
from refine_lrb_window_surfaces import apply_lrb_window_surfaces, PANES
BASE = ROOT / 'result/blender/LSE_campus_detailed_v190.blend'
TARGET = ROOT / 'result/blender/LSE_campus_detailed_v191.blend'
REPORT = ROOT / 'result/blender/stage191'
proof = json.loads((REPORT / 'building-refinement.json').read_text())
snapshot = REPORT / 'baseline-collections.json'
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == proof['baselineSha256']
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    collections = {c.name: sorted(o.name for o in c.objects) for c in bpy.data.collections}
    snapshot.write_text(json.dumps(dict(baselineSha256=proof['baselineSha256'], collections=collections), indent=2)+'\n')
else:
    baseline = json.loads(snapshot.read_text())
    assert baseline['baselineSha256'] == proof['baselineSha256']
    collections = baseline['collections']
assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(TARGET))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
assert geometry_signatures() == proof['geometrySignatures']
assert all(shape_signature(bpy.data.objects[n]) == v for n, v in proof['originalShapesAndUVs'].items())
assert all(font_signature(bpy.data.objects[n]) == v for n, v in proof['originalFonts'].items())
assert all(bpy.data.objects[n].hide_render == v for n, v in proof['visibility'].items())
added = set(proof['changes'][0]['addedObjects'])
for name, objects in collections.items():
    assert sorted(o.name for o in bpy.data.collections[name].objects if o.name not in added) == objects
ring = next(b['rings'][0] for b in json.loads((ROOT / 'result/blender/site_geometry.json').read_text())['buildings'] if b['code'] == 'LRB')
a = Vector((*ring[1], 0)); b = Vector((*ring[2], 0))
edge = b - a
outward = Vector((-edge.y, edge.x, 0)).normalized()
checked = []
for old_name, new_name, count in PANES:
    old, new = bpy.data.objects[old_name], bpy.data.objects[new_name]
    assert old.hide_render and not new.hide_render
    assert new in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.values()
    assert old.matrix_world == new.matrix_world
    assert len(new.data.vertices) == count * 4 and len(new.data.polygons) == count
    assert [l.name for l in old.data.uv_layers] == [l.name for l in new.data.uv_layers]
    # Independent check: every new quad equals the source's maximum street-depth
    # plane of exactly one original 8-vertex box, with its per-vertex UV preserved.
    matched = set()
    for face in new.data.polygons:
        points = [new.matrix_world @ new.data.vertices[i].co for i in face.vertices]
        assert (points[1]-points[0]).cross(points[2]-points[0]).normalized().dot(outward) > .999
        candidates = []
        for pane in range(count):
            ids = set(range(pane*8, pane*8+8))
            source_points = {i:old.matrix_world @ old.data.vertices[i].co for i in ids}
            depth = max(p.dot(outward) for p in source_points.values())
            front = {i:p for i,p in source_points.items() if abs(p.dot(outward)-depth) < 2e-5}
            if len(front) == 4 and all(any((point-v).length < 1e-6 for v in front.values()) for point in points):
                candidates.append((pane, front))
        assert len(candidates) == 1
        pane, front = candidates[0]
        assert pane not in matched; matched.add(pane)
        source_face = next(f for f in old.data.polygons if set(f.vertices) == set(front))
        assert face.material_index == source_face.material_index
        for layer_old, layer_new in zip(old.data.uv_layers, new.data.uv_layers):
            for loop in face.loop_indices:
                point = new.data.vertices[new.data.loops[loop].vertex_index].co
                original_loop = next(li for li in source_face.loop_indices if (old.data.vertices[old.data.loops[li].vertex_index].co-point).length < 1e-6)
                assert (layer_old.data[original_loop].uv-layer_new.data[loop].uv).length < 1e-6
        left = old.data.materials[source_face.material_index]
        right = new.data.materials[face.material_index]
        assert list(left.diffuse_color) == list(right.diffuse_color)
        left_inputs = left.node_tree.nodes['Principled BSDF'].inputs
        right_inputs = right.node_tree.nodes['Principled BSDF'].inputs
        assert len(left_inputs) == len(right_inputs)
        for socket, partner in zip(left_inputs, right_inputs):
            assert socket.identifier == partner.identifier and socket.is_linked == partner.is_linked
            if hasattr(socket, 'default_value'):
                x, y = socket.default_value, partner.default_value
                if hasattr(x, '__iter__'): assert list(x) == list(y)
                else: assert x == y
        assert right.get('webClosedGlazing') is False
        assert left.get('webOpacity') == right.get('webOpacity')
    assert len(matched) == count
    checked.append(dict(source=old_name, target=new_name, panes=count))
assert apply_lrb_window_surfaces()['alreadyApplied']
assert not bpy.data.libraries
assert not any(i.source == 'FILE' and not i.packed_file for i in bpy.data.images)
result = dict(version=191, savedSceneReopened=True, sourceModelSha256=proof['sourceModelSha256'],
              originalGeometryUVFontsBindingsPreserved=True, collectionsPreserved=True,
              idempotent=True, paneFrontsAndCornerUVsPreserved=True, opticalInputsPreserved=True,
              checked=checked, addedObjects=sorted(added), objects=len(bpy.data.objects), externalDependencies=False)
(REPORT / 'reopened-verification.json').write_text(json.dumps(result, indent=2)+'\n')
print('LRB191_FULL_MODEL_VERIFIED', sum(r['panes'] for r in checked), flush=True)
