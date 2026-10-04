"""Correct St Clement's main corner panel proportions from LSE archival dimensions.

Run inside Blender without arguments. The panel remains an art placeholder;
its mosaic and raised aluminium motifs are not invented from the distant photo.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stc_envelope_next'
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / 'result/blender/LSE_campus_detailed_v141.blend'
if not BASE.exists():
    BASE = max((ROOT / 'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'), key=lambda p: int(p.stem.rsplit('v', 1)[1]))
COMPONENT = OUT / 'st-clements-envelope-component.blend'
COLLECTION = 'STC_EXTERIOR'
PAIRS = [
    ('STC_D5_mural_panel_placeholder_panel', 'STC_NEXT_ENVELOPE_corner_panel_proportions', 2.286, 11.5824),
    ('STC_D5_mural_stone_frame_stone', 'STC_NEXT_ENVELOPE_corner_panel_frame', 2.446, 11.7524),
]


def open_baseline():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    previous = OUT / 'audit.json'
    prior = json.loads(previous.read_text()) if previous.exists() else {}
    for name in [p[1] for p in PAIRS]:
        obj = bpy.data.objects.get(name)
        if obj:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            mesh.use_fake_user = False
            if not mesh.users:
                bpy.data.meshes.remove(mesh)
    for name in prior.get('archivedObjects', []):
        obj = bpy.data.objects[name]
        state = prior['originalVisibility'][name]
        obj.hide_render, obj.hide_viewport = state[:2]
        obj.hide_set(state[2])
    bpy.context.view_layer.update()
    return bpy.context.scene


def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for data, field, kind, count in [(obj.data.vertices, 'co', 'f', 3), (obj.data.loops, 'vertex_index', 'i', 1), (obj.data.polygons, 'material_index', 'i', 1)]:
            values = array.array(kind, [0]) * (len(data) * count)
            data.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            digest.update(values.tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()


scene = open_baseline()
originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects}
archived = [p[0] for p in PAIRS]
owned_names = [p[1] for p in PAIRS]
owned = []
registration = []
for source_name, name, width, height in PAIRS:
    source = bpy.data.objects[source_name]
    assert len(source.data.vertices) == 8 and not source.hide_render
    vertices = [source.matrix_world @ v.co for v in source.data.vertices]
    u = (vertices[4] - vertices[0]).normalized()
    n = (vertices[2] - vertices[0]).normalized()
    assert abs(u.z) < 1e-6 and abs(n.z) < 1e-6
    centre = sum(vertices, Vector()) / 8
    old_width = max(v.dot(u) for v in vertices) - min(v.dot(u) for v in vertices)
    old_height = max(v.z for v in vertices) - min(v.z for v in vertices)
    copy = source.copy()
    copy.data = source.data.copy()
    copy.name = name
    copy.data.name = name
    bpy.data.collections[COLLECTION].objects.link(copy)
    inverse = copy.matrix_world.inverted()
    for vertex, point in zip(copy.data.vertices, vertices):
        offset = point - centre
        point += u * offset.dot(u) * (width / old_width - 1)
        point.z += offset.z * (height / old_height - 1)
        vertex.co = inverse @ point
    copy.data.update()
    source.hide_render = True
    source.hide_set(True)
    owned.append(copy)
    registration.append({'source': source_name, 'owned': name, 'centre': list(centre), 'horizontalAxis': list(u), 'depthAxis': list(n), 'beforeWidth': old_width, 'beforeHeight': old_height, 'afterWidth': width, 'afterHeight': height, 'depthAndCentrePreserved': True})
bpy.context.view_layer.update()


def validate():
    assert all(fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
    assert all([bpy.data.objects[name].hide_render, bpy.data.objects[name].hide_viewport, bpy.data.objects[name].hide_get()] == state for name, state in visibility.items() if name not in archived)
    trees = []
    for obj in scene.objects:
        if obj.type == 'MESH' and obj.name.startswith('STC') and not obj.hide_render and not obj.hide_get():
            trees.append((obj.name, BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices], [tuple(f.vertices) for f in obj.data.polygons])))
    record = registration[0]
    centre = Vector(record['centre'])
    u, n = Vector(record['horizontalAxis']), Vector(record['depthAxis'])
    ring = next(b['rings'][0] for b in json.loads((ROOT / 'result/blender/site_geometry.json').read_text())['buildings'] if b['code'] == 'STC')
    building_centre = sum((Vector((*v, 0)) for v in ring), Vector()) / len(ring)
    if n.dot(centre - building_centre) < 0:
        n = -n
    result = []
    for x in [-.42, 0, .42]:
        for z in [-.4, 0, .4]:
            origin = centre + u * x * record['afterWidth'] + Vector((0, 0, z * record['afterHeight'])) + n * .7
            hits = []
            for name, tree in trees:
                point, normal, face, distance = tree.ray_cast(origin, -n, 2)
                if point is not None:
                    hits.append({'object': name, 'distance': distance})
            hit = min(hits, key=lambda h: h['distance'])
            assert hit['object'] == owned_names[0], hit
            result.append({'widthFraction': x, 'heightFraction': z, 'firstHit': hit})
    for record in registration:
        source = bpy.data.objects[record['source']]
        copy = bpy.data.objects[record['owned']]
        assert len(copy.data.vertices) == len(source.data.vertices)
        assert [tuple(p.vertices) for p in copy.data.polygons] == [tuple(p.vertices) for p in source.data.polygons]
        assert [p.material_index for p in copy.data.polygons] == [p.material_index for p in source.data.polygons]
        for old_layer, new_layer in zip(source.data.uv_layers, copy.data.uv_layers):
            assert [tuple(v.uv) for v in old_layer.data] == [tuple(v.uv) for v in new_layer.data]
    return result, n


initial, outward = validate()
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
audit = {
    'baselineSha256': hashlib.sha256(BASE.read_bytes()).hexdigest(),
    'originalFingerprints': originals, 'originalVisibility': visibility,
    'ownedObjects': owned_names, 'archivedObjects': archived,
    'changes': [{'source': source, 'owned': name, 'action': 'replace', 'collection': COLLECTION} for source, name, _, _ in PAIRS],
    'sourceObjects': archived, 'destinationCollection': COLLECTION,
    'scope': 'Correct the principal street-corner panel and surrounding frame as a coherent facade feature; retain existing windows, wall divisions, entrance, attic and roof.',
    'registration': registration,
    'publishedArtworkDimensions': {'feetHeight': 38, 'feetWidth': 7.5, 'metresHeight': 11.5824, 'metresWidth': 2.286, 'basis': 'LSE archivist2015account of the completed vitreous mosaic panel; historical published dimensions, not2026survey'},
    'sources': [
        {'url': 'https://blogs.lse.ac.uk/lsehistory/2015/07/09/printing-presses-and-science-labs-the-story-of-st-clements/', 'date': '2015-07-09', 'supports': 'Completed corner panel dimensions and location'},
        {'url': 'https://blogs.lse.ac.uk/lsehistory/2017/01/09/harry-warren-wilson-and-the-st-clements-building-panel/', 'date': '2017-01-09', 'supports': 'Completed mosaic with projecting aluminium motifs; corroborating historical dimensions has repeated high typo in width phrase'},
        {'local': 'data/建筑图片/STC_St Clement_s/01_建筑实拍/campus_photos_round2_STC_geograph_7222785_01.jpg', 'sha256': '64694d6e29bca62c784e4751367db7625df7d1ef58c84aeab15de3855cafe536', 'date': '2022-06-01 archive record', 'supports': 'Whole corner/main street facade and continuous tall artwork panel'},
    ],
    'wholeBuildingAssessment': {'fourUpperWindowRows': 'Present; no photograph-supported row-count replacement', 'whiteMainFacadeAndRedRecessedLandings': 'Present; lighting-dependent colours not recalibrated blindly', 'setbackAttic': 'Prior35aperture correction retained', 'groundEntrance': 'Official close-up existing red jamb/grey fascia/recess arrangement retained', 'eastWallSteppedSilhouette': 'Oblique artwork photograph shows a stepped edge; precise building/roof registration insufficient for a roof-mass replacement'},
    'limitations': ['Mosaic colours, Thames drawing and raised aluminium figures remain an explicit placeholder; no invented replica or reused artwork texture.', 'The existing frame border0.08m per side and0.085m per top/bottom remains an estimate, not part of the published artwork specification.', 'Centre and wall depth retained from existing registered model; absolute panel elevation and source footprint are not surveyed.', 'No claim that hidden elevations, complete interiors or current2026appearance are finished.'],
}
(OUT / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
scene = open_baseline()
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = list(owned_names)
for obj in dst.objects:
    bpy.data.collections[COLLECTION].objects.link(obj)
for source_name, name, _, _ in PAIRS:
    source = bpy.data.objects[source_name]
    copy = bpy.data.objects[name]
    for index, material in enumerate(source.data.materials):
        copy.data.materials[index] = material
    source.hide_render = True
    source.hide_set(True)
bpy.context.view_layer.update()
reloaded, outward = validate()
assert initial == reloaded
proof = {'componentSha256': hashlib.sha256(COMPONENT.read_bytes()).hexdigest(), 'baselineSha256': audit['baselineSha256'], 'savedComponentReopened': True, 'originalObjectCount': len(originals), 'allOriginalFingerprintsPreserved': True, 'originalGeometryPreserved': True, 'unrelatedVisibilityPreserved': True, 'ownedTopologyUVMaterialSlotsRetained': True, 'panelFirstHitProbes': reloaded, 'renderCount': 1, 'fullModelSaved': False}
# Isolate the entire STC while keeping archived sources hidden.
for obj in scene.objects:
    if obj.type != 'CAMERA':
        obj.hide_render = (not obj.name.startswith('STC')) or obj.name in archived or visibility.get(obj.name, [False])[0]
points = [o.matrix_world @ v.co for o in bpy.data.collections[COLLECTION].all_objects if o.type == 'MESH' and not o.hide_render for v in o.data.vertices]
focus = sum(points, Vector()) / len(points)
focus.z = 10.5
camera_data = bpy.data.cameras.new('STC_ENVELOPE_preview')
camera = bpy.data.objects.new(camera_data.name, camera_data)
scene.collection.objects.link(camera)
u = Vector(registration[0]['horizontalAxis'])
camera.location = focus + outward * 70 - u * 13 + Vector((0, 0, 18))
camera.rotation_euler = (focus - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 51
scene.camera = camera
scene.render.engine = 'CYCLES'
scene.cycles.samples = 12
scene.cycles.use_denoising = True
world = bpy.data.worlds.new('STC_ENVELOPE_world')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.52, .55, .60, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = .7
scene.world = world
light_data = bpy.data.lights.new('STC_ENVELOPE_key', 'AREA')
light_data.energy = 18000
light_data.size = 35
light = bpy.data.objects.new(light_data.name, light_data)
scene.collection.objects.link(light)
light.location = focus + outward * 25 + Vector((0, 0, 30))
light.rotation_euler = (focus - light.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.resolution_x, scene.render.resolution_y = 1150, 1050
scene.render.resolution_percentage = 100
scene.render.filepath = str(OUT / 'reloaded-st-clements-envelope.png')
bpy.ops.render.render(write_still=True)
proof['nativeRender'] = str(OUT / 'reloaded-st-clements-envelope.png')
(OUT / 'verification.json').write_text(json.dumps(proof, indent=2) + '\n')
print('STC_ENVELOPE_VERIFIED', proof['componentSha256'])
bpy.ops.wm.quit_blender()
