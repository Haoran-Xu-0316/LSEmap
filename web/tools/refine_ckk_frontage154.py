"""Correct the photographed semicircular CKK fanlight independently of the campus.

The official frontal photograph shows no rectangular glass skirt below the arch.
Retain existing radius and materials; align its spring with the existing portico.
All dimensional registration remains a photographic estimate.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/ckk_frontage154'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v153.blend'
SHA = '1c042804b6fda74a7148309f934f7213647a4201953f92e170c2aeabff6305a1'
PREFIX = 'CKK_NEXT_FRONTAGE154_'
SOURCES = ['CKK_V33_fanlight_glass', 'CKK_NEXT_FANLIGHT_retained_arch_frame',
           'CKK_V33_arch_stones', 'CKK_V33_arch_spandrels']
OWNED = [PREFIX + suffix for suffix in ['semicircular_glass', 'lowered_arch_frame',
                                     'lowered_arch_stones', 'closed_arch_spandrels']]
COMPONENT = OUT / 'cheng-kin-ku-frontage-component.blend'
SPRING_BEFORE, SPRING_AFTER = 6.55, 5.30
DROP = SPRING_BEFORE - SPRING_AFTER


def fingerprint(obj):
    digest = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for data, field, kind, width in [(obj.data.vertices, 'co', 'f', 3),
                                        (obj.data.loops, 'vertex_index', 'i', 1),
                                        (obj.data.polygons, 'material_index', 'i', 1)]:
            values = array.array(kind, [0]) * (len(data) * width)
            data.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            digest.update(values.tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()


def reopen():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()


assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
reopen()
assert len(bpy.data.objects) == 5874
originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects}
collection = bpy.data.collections['CKK_EXTERIOR']
owned = []
for source_name, owned_name in zip(SOURCES, OWNED):
    source = bpy.data.objects[source_name]
    assert not source.hide_render
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = owned_name
    obj.data.name = owned_name
    collection.objects.link(obj)
    if source_name == SOURCES[0]:
        # Exactly the one connected six-face rectangular skirt is unsupported.
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        skirts = [face for face in bm.faces if all(
            (obj.matrix_world @ v.co).z <= SPRING_BEFORE + 1e-5 for v in face.verts)]
        assert len(skirts) == 6, len(skirts)
        bmesh.ops.delete(bm, geom=skirts, context='FACES')
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context='VERTS')
        bm.to_mesh(obj.data)
        bm.free()
        assert len(obj.data.polygons) == 40
    for vertex in obj.data.vertices:
        world = obj.matrix_world @ vertex.co
        # Extend existing stone corner closures to the new arch, retaining top8m.
        if source_name != SOURCES[3] or world.z < 7.999:
            world.z -= DROP
            vertex.co = obj.matrix_world.inverted() @ world
    if source_name == SOURCES[3]:
        # The old forty disconnected coplanar strips develop shadow seams when
        # lengthened. One concave stone solid closes the actual arched aperture.
        # Frontage stone thickness0.50m follows the existing native wall estimate.
        assert not obj.data.uv_layers
        local_profile = [(-1.35, SPRING_AFTER), (-1.35, 8.0),
                         (1.35, 8.0), (1.35, SPRING_AFTER)]
        local_profile.extend((1.35 * math.cos(i * math.pi / 40),
                              SPRING_AFTER + 1.35 * math.sin(i * math.pi / 40))
                             for i in range(1, 40))
        center = Vector((-110.49102024587766, 77.56014819690478, 0))
        n = Vector((math.cos(math.radians(22)), math.sin(math.radians(22)), 0))
        u = Vector((-n.y, n.x, 0))
        inverse = obj.matrix_world.inverted()
        vertices = [inverse @ (center + n * x + u * y + Vector((0, 0, z)))
                    for x in [22.92, 22.42] for y, z in local_profile]
        count = len(local_profile)
        faces = [tuple(reversed(range(count))), tuple(range(count, 2 * count))]
        faces.extend((i, (i + 1) % count, (i + 1) % count + count, i + count)
                     for i in range(count))
        obj.data.clear_geometry()
        obj.data.from_pydata(vertices, [], faces)
        editable = bmesh.new()
        editable.from_mesh(obj.data)
        bmesh.ops.triangulate(editable, faces=[f for f in editable.faces if len(f.verts) > 4])
        bmesh.ops.recalc_face_normals(editable, faces=list(editable.faces))
        editable.to_mesh(obj.data)
        editable.free()
    obj.data.update()
    assert list(obj.data.materials) == list(source.data.materials)
    source.hide_render = True
    source.hide_set(True)
    owned.append(obj)


def protected():
    assert all(fingerprint(bpy.data.objects[n]) == f for n, f in originals.items())
    assert all([bpy.data.objects[n].hide_render, bpy.data.objects[n].hide_viewport,
                bpy.data.objects[n].hide_get()] == state
               for n, state in visibility.items() if n not in SOURCES)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA


protected()
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
origin = Vector((-110.49102024587766, 77.56014819690478, 0))
normal = Vector((math.cos(math.radians(22)), math.sin(math.radians(22)), 0))
axis = Vector((-normal.y, normal.x, 0))


def world(x, y, z):
    return origin + normal * x + axis * y + Vector((0, 0, z))


def probes():
    vs, fs, names = [], [], []
    for obj in collection.all_objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        index = len(vs)
        vs.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        obj.data.calc_loop_triangles()
        fs.extend(tuple(index + k for k in t.vertices) for t in obj.data.loop_triangles)
        names.extend([obj.name] * len(obj.data.loop_triangles))
    tree = BVHTree.FromPolygons(vs, fs, all_triangles=True)
    checks = []
    # Three independent glass points and two stone points above the new arc.
    for y, z, expected in [(-.7, 5.75, OWNED[0]), (0, 6.0, OWNED[0]),
                            (.7, 5.75, OWNED[0]), (-.5, 7.2, OWNED[3]),
                            (.5, 7.2, OWNED[3])]:
        start = world(24.2, y, z)
        hit = tree.ray_cast(start, -normal, 3)
        name = names[hit[2]] if hit[2] is not None else None
        assert name == expected, (y, z, name, expected)
        checks.append({'start': list(start), 'firstSurface': name, 'hit': list(hit[0])})
    return checks


checks = probes()
new_fingerprints = {o.name: fingerprint(o) for o in owned}
photo = ROOT / 'data/建筑图片/CKK_Cheng Kin Ku Building/01_建筑实拍/exteriors_ckk_grimshaw_010.jpg'
audit = {'baseline': str(BASE), 'baselineSha256': SHA, 'originalObjectCount': 5874,
         'ownedObjects': OWNED, 'archivedObjects': SOURCES,
         'destinationCollection': 'CKK_EXTERIOR', 'retainNewMaterials': False,
         'originalFingerprints': originals, 'originalVisibility': visibility,
         'changes': [{'source': s, 'owned': o, 'action': a} for s, o, a in zip(SOURCES, OWNED,
             ['Remove one six-face rectangular glass skirt and lower semicircle1.25m',
              'Lower retained unsplit arch rim and spring rail1.25m',
              'Lower existing13 stone voussoirs1.25m',
              'Replace40 disconnected stone closure strips with one continuous0.50m-thick arched fill'])],
         'registration': {'origin': list(origin), 'outward': list(normal),
                          'oldSpring': SPRING_BEFORE, 'newSpring': SPRING_AFTER,
                          'retainedRadius': 1.35, 'porticoTop': 5.27},
         'rejectedCandidate': 'rejected-opacity: transparency exposed distant courtyard wall bands; no clear overall improvement',
         'references': [{'path': str(photo), 'sha256': hashlib.sha256(photo.read_bytes()).hexdigest(),
                         'source': 'https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/',
                         'captureDate': 'unknown',
                         'supports': 'Semicircular fanlight directly over portico lintel; no rectangular glass skirt'}],
         'limitations': ['Spring5.30m and retained radius1.35m are photo registration estimates, not surveyed dimensions.',
                        'Materials, UV layers,61 frontage panes, door, portico, roof and unrelated visibility retained.',
                        'No new interior, signage, lighting or unobserved facade detail.']}
(OUT / 'audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2))
# Reopen the saved component in the authoritative baseline, validate geometry anew.
reopen()
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = list(OWNED)
for source_name, obj in zip(SOURCES, dst.objects):
    bpy.data.collections['CKK_EXTERIOR'].objects.link(obj)
    # Appending a library duplicates datablocks; bind the retained native finishes.
    for index, material in enumerate(bpy.data.objects[source_name].data.materials):
        obj.data.materials[index] = material
for name in SOURCES:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
protected()
assert all(fingerprint(bpy.data.objects[n]) == f for n, f in new_fingerprints.items())
collection = bpy.data.collections['CKK_EXTERIOR']
assert probes() == checks
proof = {'componentSha256': hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
         'savedComponentReopened': True, 'originalGeometryPreserved': True,
         'originalObjectCount': 5874, 'baselineUnchanged': True,
         'originalMaterialsRetained': True, 'unrelatedVisibilityPreserved': True,
         'removedRectangularSkirtFaces': 6, 'retainedSemicircularGlassFaces': 40,
         'continuousStoneFill': True, 'stoneThicknessEstimate': 0.50,
         'ownedFingerprints': new_fingerprints, 'firstSurfaceChecks': checks,
         'fullCampusSaved': False}
(OUT / 'verification.json').write_text(json.dumps(proof, indent=2))
print('CKK154_GEOMETRY_DONE', proof['componentSha256'], flush=True)
bpy.ops.wm.quit_blender()
