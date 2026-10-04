"""Close one existing MAR high wing with an explicitly estimated roof slab.

Run in Blender's Text Editor. The component follows visible native walltops,
not the built third-floor drawing. It preserves the north terrace and fissure.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/mar_roof154'
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / 'result/blender/LSE_campus_detailed_v153.blend'
BASE_SHA = '1c042804b6fda74a7148309f934f7213647a4201953f92e170c2aeabff6305a1'
COMPONENT = OUT / 'marshall-highwing-roof154-component.blend'
OWNED = 'MAR_NEXT_ROOF154_8546_bounded_roof'
ORIGIN = Vector((-8.696325894899289, 49.33154396120258, 0))
ANGLE = math.radians(22)
U = Vector((math.cos(ANGLE), math.sin(ANGLE), 0))
N = Vector((-U.y, U.x, 0))


def world(x, y, z):
    return ORIGIN + U * x + N * y + Vector((0, 0, z))


def local(p):
    return [(p - ORIGIN).dot(U), (p - ORIGIN).dot(N), p.z]


def fingerprint(obj):
    """Track original transforms, geometry, face slots, UVs and material values."""
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for data, field, kind, size in [
            (obj.data.vertices, 'co', 'f', 3),
            (obj.data.loops, 'vertex_index', 'i', 1),
            (obj.data.polygons, 'material_index', 'i', 1),
        ]:
            values = array.array(kind, [0]) * (len(data) * size)
            data.foreach_get(field, values)
            h.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            h.update(layer.name.encode() + values.tobytes())
        for mat in obj.data.materials:
            if mat is None:
                continue
            values = [mat.name, list(mat.diffuse_color)]
            if mat.use_nodes:
                shader = mat.node_tree.nodes.get('Principled BSDF')
                if shader:
                    for key in ['Base Color', 'Metallic', 'Roughness', 'Alpha', 'Transmission Weight']:
                        value = shader.inputs[key].default_value
                        values.append([key, list(value) if key == 'Base Color' else value])
            h.update(str(values).encode())
    return h.hexdigest()


def visibility(obj):
    return [obj.hide_render, obj.hide_viewport, obj.hide_get()]


def open_baseline():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.view_layer.update()
    return bpy.data.collections['MAR_EXTERIOR']


assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
col = open_baseline()
originals = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
original_visibility = {obj.name: visibility(obj) for obj in bpy.data.objects}
assert len(originals) == 5874
sources = [
    'MAR_NEXT_PANEL_registered_8546_0_blank_wall',
    'MAR_MAR_rear_way/1376078546_1_pierced_wall',
    'MAR_V115_retained_MAR_rear_way/1376078546_2_pierced_wall',
    'MAR_NEXT_PANEL_retained_01_5_retained_D5_wings75_concrete',
]
walltops = []
for name in sources:
    obj = bpy.data.objects[name]
    assert not obj.hide_render
    for face in obj.data.polygons:
        points = [local(obj.matrix_world @ obj.data.vertices[i].co) for i in face.vertices]
        if min(p[2] for p in points) > 42.79 and abs(face.normal.z) > .8:
            walltops.append({'source': name, 'face': face.index, 'polygon': points})
assert len(walltops) == 9
# Native inner-side corners and retained north cut boundary at y8.799.
# The long west edge includes its two native wall junctions, avoiding an OSM box.
ring = [
    (8.696724891662598, -26.372554779052734),
    (23.720683097839355, -26.322793006896973),
    (23.926798820495605, 8.798999309539795),
    (8.988729000091553, 8.798999309539795),
    (8.983274459838867, 8.118438720703125),
    (8.81253981590271, -11.983867168426514),
]
# Every corner is on an existing top cap, including the north clip endpoint.
corner_distances = []
for x, y in ring:
    d = min(math.hypot(x-p[0], y-p[1]) for row in walltops for p in row['polygon'])
    assert d < .00002, (x, y, d)
    corner_distances.append(d)
area = sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(ring, ring[1:]+ring[:1])) / 2
assert 520 < area < 535
low, high = 42.51, 42.65
vertices = [world(x, y, z) for z in [low, high] for x, y in ring]
size = len(ring)
faces = [tuple(reversed(range(size))), tuple(range(size, size*2))]
faces += [(i, (i+1) % size, (i+1) % size+size, i+size) for i in range(size)]
mesh = bpy.data.meshes.new(OWNED)
mesh.from_pydata(vertices, [], faces)
mesh.materials.append(bpy.data.objects['MAR_D5_north115_roof'].data.materials[0])
mesh.update()
obj = bpy.data.objects.new(OWNED, mesh)
col.objects.link(obj)
obj['scope'] = 'Estimated closed roof within retained8546walltops; not measured upper-floor registration'
obj['roofTopEstimatedM'] = high
obj['roofThicknessEstimatedM'] = high-low
obj['northEdgeEstimated'] = 'Retained115cut at localY8.799; unseen roof termination, no extension to north terrace'
obj['evidence'] = 'Nick Kane built2022photos03/05; visible walltop ring, north clipping inherited'
owned_fp = fingerprint(obj)
assert all(fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
assert all(visibility(bpy.data.objects[name]) == value for name, value in original_visibility.items())
bpy.data.libraries.write(str(COMPONENT), {obj}, fake_user=True, compress=True)
audit = dict(
    baselineSha256=BASE_SHA, originalObjectCount=len(originals), ownedObjects=[OWNED],
    archivedObjects=[], changes=[dict(action='add bounded closed roof slab', owned=OWNED)],
    roofRingLocalXY=ring, roofAreaM2=area, roofTopEstimatedM=high,
    roofThicknessEstimatedM=high-low, walltopDatumRetainedM=42.8,
    parapetRevealEstimatedM=.15, nativeWalltopSources=sources, nativeWalltopPolygons=walltops,
    maximumCornerToWalltopDistanceM=max(corner_distances),
    originalFingerprints=originals, originalVisibility=original_visibility,
    materialSource='MAR_D5_north115_roof', roofMaterialReused=True,
    references=[dict(path='data/collections/architecture_round5/images/MAR/MAR_mar_kane_05.jpg', supports='Built south highwing has a continuous thin roofline above blank side and five-column end', date='2022 upload; capture unknown'),
                dict(path='data/collections/architecture_round5/images/MAR/MAR_mar_kane_03.jpg', supports='Stepped height hierarchy and roof-level north terrace retained', date='2022 upload; capture unknown')],
    limits=['Footprint follows existing estimated walltop geometry, not a measured roof plan',
            'Roof thickness,0.15m setback below walltop and reused grey roof finish are estimates',
            'Northern closing edge uses inherited115cut boundary; unseen roof termination remains estimated',
            'Only8546highest wing closed;39.4m wing and35.6m uncertain left wing retained',
            'No third-floor footprint extrapolation, no fictitious rooms or mechanical equipment added',
            'All new roof XY is east of8.69m; existing fissure maximumX-2m and north terraceY8.8–18.8 remain clear'],
)
(OUT/'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
# Reload only the small component into the unchanged campus, then verify before preview setup.
col = open_baseline()
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = [OWNED]
for obj in dst.objects:
    col.objects.link(obj)
obj = bpy.data.objects[OWNED]
# Library append suffixes an already-loaded shared material; remap to baseline.
obj.data.materials[0] = bpy.data.objects['MAR_D5_north115_roof'].data.materials[0]
assert fingerprint(obj) == owned_fp
assert all(fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
assert all(visibility(bpy.data.objects[name]) == value for name, value in original_visibility.items())
assert len(bpy.data.objects) == len(originals)+1
# Overall MAR south oblique makes the roof visible without a cropped detail view.
scene = bpy.context.scene
keep = {o.name for o in col.all_objects}
preview_excluded = []
for o in scene.objects:
    if o.type in ['MESH', 'FONT', 'CURVE', 'SURFACE', 'META'] and o.name not in keep and not o.hide_render:
        o.hide_render = True
        preview_excluded.append(o.name)
camera_data = bpy.data.cameras.new('MAR_ROOF154_REVIEW')
camera = bpy.data.objects.new(camera_data.name, camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 77
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.background_type = 'WORLD'
scene.render.resolution_x = 1250
scene.render.resolution_y = 1120
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
views = [('south-overall', (-70, -95, 85), (-3, -1, 22)),
         ('north-overall', (-65, 105, 80), (-3, -1, 22))]
for name, position, target in views:
    camera.location = world(*position)
    target = world(*target)
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
    for label, enabled in [('before', False), ('reloaded', True)]:
        obj.hide_render = not enabled
        obj.hide_set(not enabled)
        scene.render.filepath = str(OUT/f'{label}-{name}.png')
        bpy.ops.render.render(write_still=True)
# Restore preview-only visibility so the proof is independent of rendering filters.
obj.hide_render = False
obj.hide_set(False)
for name in preview_excluded:
    bpy.data.objects[name].hide_render = original_visibility[name][0]
assert all(visibility(bpy.data.objects[name]) == value for name, value in original_visibility.items())
proof = dict(componentSha256=hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
             savedComponentReopened=True, componentFingerprintParity=True,
             originalGeometryMaterialColorUVPreserved=True, unrelatedVisibilityPreserved=True,
             originalObjectCount=len(originals), reloadedObjectCount=len(originals)+1,
             archivedObjects=[], addedObjects=[OWNED], roofAreaM2=area,
             roofRingCornerCount=size, maxCornerToWalltopDistanceM=max(corner_distances),
             roofTopEstimatedM=high, roofThicknessEstimatedM=high-low,
             courtAndNorthTerraceClearByXY=True, wholeCampusSaved=False,
             baselineUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA,
             previewViews=views, visualAcceptancePending=True)
(OUT/'verification.json').write_text(json.dumps(proof, indent=2)+'\n')
print('MAR_ROOF154_VERIFIED', json.dumps(proof), flush=True)
