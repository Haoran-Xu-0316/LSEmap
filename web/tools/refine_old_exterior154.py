"""Refine OLD Houghton portal proportions from two built entrance photographs.

Fixed authoring paths for Blender's Text Editor. Preserve the inherited stone
arch curve, doorway threshold and blue windows; extend the existing artwork's
straight lower field rather than inventing sculptures or rescaling the building.
Only an independent component is saved. Dimensions remain photographic estimates.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/old_exterior154'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v153.blend'
PREFIX = 'OLD_NEXT_EXTERIOR154_'
COMPONENT = OUT / 'old-houghton-portal-component.blend'
EXPECTED = '1c042804b6fda74a7148309f934f7213647a4201953f92e170c2aeabff6305a1'
OUT.mkdir(parents=True, exist_ok=True)
BASE_SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()
assert BASE_SHA == EXPECTED


def open_baseline():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()


def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for items, field, kind, width in ((obj.data.vertices, 'co', 'f', 3),
                                        (obj.data.loops, 'vertex_index', 'i', 1),
                                        (obj.data.polygons, 'material_index', 'i', 1)):
            values = array.array(kind, [0]) * (len(items) * width)
            items.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            digest.update(values.tobytes())
    if obj.type == 'FONT':
        digest.update(obj.data.body.encode())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()


def visibility():
    return {obj.name: [obj.hide_render, obj.hide_viewport, obj.hide_get()]
            for obj in bpy.data.objects}


def render_fully_framed_whole_views():
    """Preview-only pass: fit complete OLD bounding geometry, no component edits."""
    audit = json.loads((OUT / 'audit.json').read_text())
    proof = json.loads((OUT / 'verification.json').read_text())
    open_baseline()
    frame = json.loads((ROOT / 'result/blender/stage52/old-houghton-audit.json').read_text())
    origin, axis, normal = [Vector(frame[key]) for key in ['origin', 'right', 'outward']]
    collection = bpy.data.collections['OLD_EXTERIOR']
    for edition in ['before', 'after']:
        if edition == 'after':
            with bpy.data.libraries.load(str(COMPONENT), link=False) as (source, destination):
                destination.objects = list(audit['ownedObjects'])
            for obj in destination.objects:
                collection.objects.link(obj)
                original = bpy.data.objects[next(change['source'] for change in audit['changes'] if change['owned'] == obj.name)]
                for index, material in enumerate(original.data.materials):
                    obj.data.materials[index] = material
                obj.hide_render = False
            for name in audit['archivedObjects']:
                bpy.data.objects[name].hide_render = True
        scene = bpy.data.scenes.new(PREFIX + 'full_frame_' + edition)
        scene.collection.children.link(collection)
        bpy.context.window.scene = scene
        scene.world = bpy.data.worlds.new(PREFIX + 'full_world_' + edition)
        scene.world.use_nodes = True
        scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.55,.63,.70,1)
        scene.world.node_tree.nodes['Background'].inputs[1].default_value = .75
        sun = bpy.data.objects.new(PREFIX + 'full_sun_' + edition, bpy.data.lights.new(PREFIX + 'full_sun_' + edition, 'SUN'))
        scene.collection.objects.link(sun)
        sun.data.energy = 2
        sun.data.angle = .15
        sun.rotation_euler = (.5,-.45,-.5)
        cam = bpy.data.objects.new(PREFIX + 'full_camera_' + edition, bpy.data.cameras.new(PREFIX + 'full_camera_' + edition))
        scene.collection.objects.link(cam)
        scene.camera = cam
        cam.data.type = 'ORTHO'
        cam.data.clip_end = 3000
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 8
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 4
        scene.render.resolution_x = 1200
        scene.render.resolution_y = 900
        scene.render.resolution_percentage = 100
        scene.view_settings.view_transform = 'AgX'
        scene.render.image_settings.file_format = 'PNG'
        points = [obj.matrix_world @ Vector(corner) for obj in collection.all_objects
                  if obj.type in {'MESH','FONT'} and not obj.hide_render for corner in obj.bound_box]
        for label,x,z,distance,side,elevation in [('whole-houghton',-6.01,13.5,100,3,12),
                                                ('whole-three-quarter',-5,13.5,100,-55,58)]:
            focus = origin + axis*x + Vector((0,0,z))
            cam.location = focus + normal*distance + axis*side + Vector((0,0,elevation))
            cam.rotation_euler = (focus-cam.location).to_track_quat('-Z','Y').to_euler()
            bpy.context.view_layer.update()
            projected = [cam.matrix_world.inverted() @ point for point in points]
            lo = Vector(tuple(min(point[index] for point in projected) for index in range(3)))
            hi = Vector(tuple(max(point[index] for point in projected) for index in range(3)))
            shift = cam.matrix_world.to_3x3() @ Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,0))
            cam.location += shift
            focus += shift
            cam.data.ortho_scale = max(hi.x-lo.x,(hi.y-lo.y)*1200/900)*1.08
            scene.render.filepath = str(OUT / (edition + '-' + label + '.png'))
            bpy.ops.render.render(write_still=True)
            view = {'position':list(cam.location),'target':list(focus),'orthoScale':cam.data.ortho_scale,
                    'path':edition + '-' + label + '.png','completeVisibleBoundsFitted':True,'margin':.08}
            proof[edition + 'Views'][label] = view
            if edition == 'before':
                audit['beforeViews'][label] = view
            print('OLD154_FULL_FRAME',edition,label,flush=True)
        bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
        bpy.data.scenes.remove(scene)
        for obj in [sun,cam]:
            bpy.data.objects.remove(obj,do_unlink=True)
    assert hashlib.sha256(COMPONENT.read_bytes()).hexdigest() == proof['componentSha256']
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    proof['wholeViewsFullyFramed'] = True
    proof['previewViewed'] = False
    (OUT / 'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
    (OUT / 'verification.json').write_text(json.dumps(proof,indent=2))
    print('OLD154_FULL_FRAME_DONE',flush=True)
    bpy.ops.wm.quit_blender()


PREVIEW_ONLY = False
if PREVIEW_ONLY:
    render_fully_framed_whole_views()
    raise SystemExit(0)

open_baseline()
originals = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
states = visibility()
assert len(originals) == 5874
registration = json.loads((ROOT / 'result/blender/stage52/old-houghton-audit.json').read_text())
origin, axis, normal = [Vector(registration[key]) for key in ['origin', 'right', 'outward']]
collection = bpy.data.collections['OLD_EXTERIOR']


def world_vertices(obj):
    values = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', values)
    matrix = np.asarray(obj.matrix_world, dtype=np.float64)
    return values.reshape(-1, 3).astype(np.float64) @ matrix[:3, :3].T + matrix[:3, 3]


def geometry_bounds(obj):
    values = world_vertices(obj)
    return [values.min(axis=0).tolist(), values.max(axis=0).tolist()]


art_names = ['OLD_V112_entry_D5_finalsale84_display_frame',
             'OLD_V112_entry_D5_finalsale84_containers',
             'OLD_V112_entry_V111_lattice_figures',
             'OLD_V112_entry_V111_lattice_products']
backing_name = 'OLD_V112_entry_D5_finalsale84_glazing'
door_names = ['OLD_NEXT_ACCESS_door_glass', 'OLD_NEXT_ACCESS_door_frame',
              'OLD_NEXT_ACCESS_door_steel']
backing = bpy.data.objects[backing_name]
backing_points = world_vertices(backing)
old_art_base = float(backing_points[:, 2].min())
crown = float(backing_points[:, 2].max())
door_points = world_vertices(bpy.data.objects[door_names[0]])
old_door_top = float(door_points[:, 2].max())
threshold = float(door_points[:, 2].min())
# Two frontal/oblique built photographs show a tall artwork field above a
# normal entrance door. Choose a conservative central ratio within1.05-1.25.
photo_ratio = 1.15
old_frame_top = float(world_vertices(bpy.data.objects['OLD_NEXT_ACCESS_door_frame'])[:, 2].max())
new_header = (crown + photo_ratio * threshold) / (1 + photo_ratio)
assert 3.45 < new_header < 3.70
assert 4.0 < old_art_base < 4.15
print('OLD154_DIMENSIONS', old_art_base, crown, old_door_top, threshold, new_header, flush=True)
assert 3.9 < old_door_top < 4.65
owned = []
archived = []
changes = []


def copy_source(source_name, label):
    source = bpy.data.objects[source_name]
    assert source.type == 'MESH' and not source.hide_render, source_name
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = PREFIX + label
    obj.data.name = obj.name
    collection.objects.link(obj)
    obj.hide_render = False
    obj.hide_viewport = False
    obj.hide_set(False)
    owned.append(obj)
    archived.append(source_name)
    return source, obj


def remap_world_heights(source, obj, low, high, target_low, target_high):
    points = world_vertices(source)
    before = points[:, 2].copy()
    points[:, 2] = target_low + (before - low) * (target_high - target_low) / (high - low)
    inverse = np.asarray(obj.matrix_world.inverted(), dtype=np.float64)
    coords = points @ inverse[:3, :3].T + inverse[:3, 3]
    obj.data.vertices.foreach_set('co', np.asarray(coords, dtype=np.float32).reshape(-1))
    obj.data.update()
    assert np.max(np.abs(world_vertices(obj)[:, :2] - world_vertices(source)[:, :2])) < 0.0001
    changes.append({'source': source.name, 'owned': obj.name,
                    'action': 'Existing topology remapped vertically; worldX/Y preserved',
                    'inputZ': [low, high], 'outputZ': [target_low, target_high],
                    'changedVertexCount': int(np.count_nonzero(np.abs(before - points[:, 2]) > 0.00001)),
                    'boundsBefore': geometry_bounds(source), 'boundsAfter': geometry_bounds(obj)})


# Hide new copies until matching baseline renders have been produced.
new_frame_top = threshold + (old_frame_top - threshold) * (new_header - threshold) / (old_door_top - threshold)
artwork_target_low = new_frame_top + .020
artwork_low = min(float(world_vertices(bpy.data.objects[name])[:, 2].min()) for name in art_names)
for name in art_names:
    source, obj = copy_source(name, name.removeprefix('OLD_V112_entry_'))
    remap_world_heights(source, obj, artwork_low, crown, artwork_target_low, crown)

for name in door_names:
    source, obj = copy_source(name, name.removeprefix('OLD_NEXT_ACCESS_'))
    remap_world_heights(source, obj, threshold, old_door_top, threshold, new_header)

# Keep every sampled arch-edge vertex fixed. Only the two existing rectangular
# lower corners move, exposing the straight-sided artwork field seen in photos.
source, obj = copy_source(backing_name, 'artwork_straight_lower_field')
points = world_vertices(source)
mask = np.abs(points[:, 2] - old_art_base) < 0.0001
assert int(mask.sum()) == 2
points[mask, 2] = new_header
inverse = np.asarray(obj.matrix_world.inverted(), dtype=np.float64)
obj.data.vertices.foreach_set('co', np.asarray(points @ inverse[:3, :3].T + inverse[:3, 3], dtype=np.float32).reshape(-1))
obj.data.update()
assert np.max(np.abs(world_vertices(obj)[~mask] - world_vertices(source)[~mask])) < 0.0001
changes.append({'source': source.name, 'owned': obj.name,
                'action': 'Lower two straight-field corners; all65 curve samples fixed',
                'changedVertexCount': 2, 'boundsBefore': geometry_bounds(source),
                'boundsAfter': geometry_bounds(obj)})

# The existing stone shoulder contains the necessary jamb returns below the
# arch spring. No extra covering planes, doors, generic figures or roof added.
for obj in owned:
    obj.hide_render = True
    obj.hide_set(True)


def protected(check_visibility=True):
    assert all(fingerprint(bpy.data.objects[name]) == digest for name, digest in originals.items())
    if check_visibility:
        current = visibility()
        assert all(current[name] == state for name, state in states.items() if name not in archived)


def render_views(edition):
    scene = bpy.data.scenes.new(PREFIX + 'proof_' + edition)
    scene.collection.children.link(collection)
    scene.world = bpy.data.worlds.new(PREFIX + 'world_' + edition)
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes['Background']
    background.inputs[0].default_value = (.55, .63, .70, 1)
    background.inputs[1].default_value = .75
    sun = bpy.data.objects.new(PREFIX + 'sun_' + edition,
                              bpy.data.lights.new(PREFIX + 'sun_' + edition, 'SUN'))
    scene.collection.objects.link(sun)
    sun.data.energy = 2
    sun.data.angle = .15
    sun.rotation_euler = (.5, -.45, -.5)
    cam = bpy.data.objects.new(PREFIX + 'proof_camera_' + edition,
                              bpy.data.cameras.new(PREFIX + 'proof_camera_' + edition))
    scene.collection.objects.link(cam)
    cam.data.type = 'ORTHO'
    cam.data.clip_end = 3000
    scene.camera = cam
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 8
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.render.image_settings.file_format = 'PNG'
    bpy.context.window.scene = scene
    cameras = {}
    views = [('whole-houghton', -6.01, 13.5, 100, 3, 12, 67),
             ('whole-three-quarter', -5, 13.5, 100, -55, 58, 75),
             ('portal-context', -27.27, 7.4, 90, 6, 5, 22),
             ('portal-oblique', -27.27, 7.4, 90, -40, 5, 24)]
    for label, x, z, distance, side, elevation, scale in views:
        focus = origin + axis * x + Vector((0, 0, z))
        cam.location = focus + normal * distance + axis * side + Vector((0, 0, elevation))
        cam.rotation_euler = (focus - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.ortho_scale = scale
        scene.render.filepath = str(OUT / (edition + '-' + label + '.png'))
        bpy.ops.render.render(write_still=True)
        cameras[label] = {'position': list(cam.location), 'target': list(focus),
                          'orthoScale': scale, 'path': edition + '-' + label + '.png'}
        print('OLD154_RENDER', edition, label, flush=True)
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.data.scenes.remove(scene)
    # Render support objects are outside the independently saved component.
    for obj in [sun, cam]:
        bpy.data.objects.remove(obj, do_unlink=True)
    return cameras


protected()
previous = json.loads((OUT / 'audit.json').read_text()) if (OUT / 'audit.json').exists() else None
if previous and previous.get('baselineSha256') == BASE_SHA and all((OUT / value['path']).exists() for value in previous.get('beforeViews', {}).values()):
    before_views = previous['beforeViews']
    assert len(before_views) == 4
else:
    before_views = render_views('before')
for name in archived:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for obj in owned:
    obj.hide_render = False
    obj.hide_set(False)
protected()
owned_fingerprints = {obj.name: fingerprint(obj) for obj in owned}
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
references = []
for path, role in [
    ('data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_01.jpg',
     'Completed entrance frontal photograph: large arch rises above straight-sided artwork field; doorway header lies below stone arch spring'),
    ('data/collections/old-user-reference/houghton-user-entrance-additional-20261002.png',
     'User oblique photo corroborates straight lower relief edges, full-height figures and normal glazed door; lower door partly obscured by caption'),
    ('data/建筑图片/OLD_Old Building/01_建筑实拍/exteriors_lse_estate_018.jpg',
     'Independent complete entrance context confirms same arch/straight artwork/door hierarchy; low-resolution image only used for qualitative corroboration')]:
    photo = ROOT / path
    references.append({'path': path, 'sha256': hashlib.sha256(photo.read_bytes()).hexdigest(),
                       'captureDate': 'unknown', 'supports': role})
audit = {'baseline': str(BASE), 'baselineSha256': BASE_SHA,
         'originalObjectCount': len(originals), 'originalFingerprints': originals,
         'originalVisibility': states, 'ownedObjects': list(owned_fingerprints),
         'archivedObjects': archived, 'changes': changes,
         'destinationCollection': 'OLD_EXTERIOR', 'retainNewMaterials': False,
         'sourcePhotoSha': references, 'references': references,
         'proportions': {'oldDoorTop': old_door_top, 'originalArtBase': old_art_base,
                        'retainedArchCrown': crown, 'retainedDoorThreshold': threshold,
                        'estimatedNewDoorHeader': new_header,
                        'oldVisibleArtworkToDoorHeight': (crown - old_door_top)/(old_door_top-threshold),
                        'artworkLowestBeamClearanceAboveFrame': .020,
                        'newVisibleArtworkToDoorHeight': photo_ratio},
         'estimate': {'basis': 'Two built photographs, cross-checked with a complete contextual photograph',
                      'ratioRange': [1.05, 1.25], 'chosenRatio': photo_ratio,
                      'estimatedHeaderRange': [(crown + ratio*threshold)/(1+ratio) for ratio in [1.25,1.05]],
                      'scope': 'Door/artwork height partition only; inherited global dimensions and threshold remain unsurveyed'},
         'limitations': ['Photographic vertical ratio, not measured architectural dimensions',
                        'Existing interpreted figures/products are retained and stretched vertically; this is not an exact sculpture reconstruction',
                        'Stone arch curve, all blue windows, stairs, access rails, crest, complete massing and roof remain unchanged',
                        'No proposed Food Hall or future roof scheme introduced'],
         'beforeViews': before_views,
         'photoMeasurement': {'path': references[0]['path'], 'imageSize': [2000,1429],
                              'archCrownPixel': [990,334], 'structuralDoorHeaderPixel': [990,684],
                              'thresholdPixel': [990,990], 'coordinateTolerancePx': 12,
                              'observedArtworkToDoorHeight': (684-334)/(990-684),
                              'notes': 'Manual frontal-image estimates; frame/glass boundary and perspective allow finite tolerance. Oblique user photo corroborates hierarchy rather than serving as orthographic measurement.'}}
(OUT / 'audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2))

# Reopen the baseline and independently reload only the saved owned component.
open_baseline()
collection = bpy.data.collections['OLD_EXTERIOR']
with bpy.data.libraries.load(str(COMPONENT), link=False) as (source, destination):
    destination.objects = list(owned_fingerprints)
reopened = destination.objects
for obj in reopened:
    collection.objects.link(obj)
    original_name = next(change['source'] for change in changes if change['owned'] == obj.name)
    for index, material in enumerate(bpy.data.objects[original_name].data.materials):
        obj.data.materials[index] = material
    obj.hide_render = False
    obj.hide_viewport = False
    obj.hide_set(False)
for name in archived:
    obj = bpy.data.objects[name]
    obj.hide_render = True
    obj.hide_set(True)
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
protected()
assert all(fingerprint(bpy.data.objects[name]) == digest for name, digest in owned_fingerprints.items())
after_views = render_views('after')
protected()
proof = {'componentSha256': hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
         'baselineUnchanged': hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
         'savedComponentReopened': True, 'originalGeometryPreserved': True,
         'unrelatedVisibilityPreserved': True, 'originalObjectCount': len(originals),
         'ownedObjectCount': len(reopened), 'ownedGeometryVerifiedAfterReload': True,
         'archCurveSamplesFixed': 65, 'doorThresholdPreserved': threshold,
         'fullCampusSaved': False, 'beforeViews': before_views, 'afterViews': after_views,
         'previewViewed': False, 'ownBlenderQuitRequested': True,
         'artworkFrameClearanceMin': artwork_target_low - new_frame_top,
         'figureClearanceMin': min(geometry_bounds(obj)[0][2] for obj in reopened if 'lattice_figures' in obj.name) - max(geometry_bounds(obj)[1][2] for obj in reopened if obj.name.endswith('door_frame')),
         'topologyAndUVPreservedForEveryOwnedObject': True}
assert proof['baselineUnchanged']
(OUT / 'verification.json').write_text(json.dumps(proof, indent=2))
print('OLD154_DONE', proof['componentSha256'], flush=True)
bpy.ops.wm.quit_blender()
