"""Build a private CBG placement/grid candidate from independent registration.

Run in Blender's Text Editor. This writes a component, never a complete campus
or published asset. Stepped teaching-wing returns, office module widths and the
highest roof cutbacks still need reconstruction before this candidate can ship.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import object_fingerprint
from refine_ground_orientation199 import closed_islands, signed_volume
from refine_street_connections194 import corner_signature
from build_room_samples167 import RoomGeometry
BASE = ROOT / 'result/blender/LSE_campus_detailed_v203.blend'
BASE_SHA = '976e645ef4b58e19485feff1fe3ff2fb64d9b5d497739642a2429548d821df8a'
OUTPUT = ROOT / 'result/blender/cbg-envelope202'
PREFIX = 'CBG202_'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame_functions(mapping):
    site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
    cx, cy = next(b['center'] for b in site['buildings'] if b['code'] == 'CBG')
    c, s = math.cos(math.radians(58)), math.sin(math.radians(58))
    frame = mapping['legacy_frame_compatible_transform']
    ox, oy = frame['translation_world']
    nc, ns = math.cos(math.radians(frame['rotation_degrees'])), math.sin(math.radians(frame['rotation_degrees']))
    wing_end = 7 + mapping['houghton_teaching_block']['bounds_local']['x'][1]

    def old_local(point):
        return Vector((c * (point.x - cx) + s * (point.y - cy), -s * (point.x - cx) + c * (point.y - cy), point.z))

    def new_world(point):
        x, y, z = point
        return Vector((ox + nc * x - ns * y, oy + ns * x + nc * y, z))

    def new_local(point):
        x, y, z = point
        # One continuous longitudinal map fixes the reversed placement while
        # keeping the shared tower/teaching-wing interface at local x7.
        nx = 7 + (x - 7) * (42 / 49 if x <= 7 else (wing_end - 7) / 28)
        fraction = min(1, max(0, (nx - 7) / (wing_end - 7)))
        upper = 4.158147892726317 - fraction * 3.23598130654656
        street = -17.232 + fraction * 2.094
        if y < -2:
            ny = -2 + (y + 2) * ((street + 2) / -12)
        elif y <= 2:
            ny = -2 + (y + 2) * ((upper + 2) / 4)
        else:
            tower_fraction = min(1, max(0, (7 - nx) / 42))
            rear = 15.94 + tower_fraction * (18.26 - 15.94) - 2
            ny = upper + (y - 2) * ((rear - upper) / 12)
        return Vector((nx, ny, z))
    return old_local, new_local, new_world


def orient_closed_shells(mesh):
    """Repair inherited inward solids without moving UVs between face corners."""
    before = corner_signature(mesh)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.normal_update()
    flipped = 0
    for faces, closed in closed_islands(bm):
        if closed and signed_volume(faces) < -1e-9:
            flipped += len(faces)
            bmesh.ops.reverse_faces(bm, faces=list(faces))
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    assert corner_signature(mesh) == before
    return flipped


def review_image(collection, name):
    scene = bpy.data.scenes.new('CBG202_' + name)
    scene.collection.children.link(collection)
    points = [obj.matrix_world @ Vector(p) for obj in collection.objects for p in obj.bound_box]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    centre = (low + high) / 2
    camera = bpy.data.objects.new('CBG202_review_camera', bpy.data.cameras.new('CBG202_review_camera'))
    scene.collection.objects.link(camera)
    camera.location = centre + Vector((-105, 90, 68))
    camera.rotation_euler = (centre - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 105
    scene.camera = camera
    scene.world = bpy.data.worlds.new('CBG202_review_world')
    scene.world.color = (.8, .82, .84)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.background_type = 'WORLD'
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUTPUT / (name + '.png'))
    bpy.ops.render.render(write_still=True, scene=scene.name)
    scene.collection.children.unlink(collection)
    world = scene.world
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.scenes.remove(scene)
    bpy.data.worlds.remove(world)


def build_candidate():
    assert digest(BASE) == BASE_SHA
    mapping = json.loads((ROOT / 'result/blender/cbg-georegistration202/rebuild-mapping.json').read_text())
    assert mapping['registration_fixed_scale_rms_metres'] < .4
    old_local, new_local, new_world = frame_functions(mapping)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    original = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    sources = sorted({o for name in ['CBG_EXTERIOR', 'CBG_PUBLIC_INTERIOR_study']
                      for o in bpy.data.collections[name].all_objects
                      if not o.hide_render and o.type in {'MESH', 'FONT', 'CURVE'}}, key=lambda o: o.name)
    before = bpy.data.collections.new('CBG202_before')
    for obj in sources:
        before.objects.link(obj)
    review_image(before, 'before-placement')
    bpy.data.collections.remove(before)
    collection = bpy.data.collections.new('CBG202_private_candidate')
    candidate_scene = bpy.data.scenes.new('CBG202_PRIVATE_REVIEW')
    candidate_scene.collection.children.link(collection)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    added, records = [], []
    column_source = next(o for o in sources if 'external_I_columns' in o.name)
    for source in sources:
        if source.type == 'MESH':
            mesh = source.data.copy()
            transform = source.matrix_world.copy()
        else:
            mesh = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)
            transform = source.matrix_world.copy()
        # Remove only the seven inherited tall column axes. The lower wing's
        # separate columns remain as a provisional member of this candidate.
        removed_tower_parts = 0
        if source == column_source:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            delete = []
            for faces, closed in closed_islands(bm):
                verts = {v for f in faces for v in f.verts}
                pts = [old_local(transform @ v.co) for v in verts]
                centre = sum(pts, Vector()) / len(pts)
                if centre.x <= 7.4 and min(abs(centre.y + 2.31), abs(centre.y - 14.31)) < .45:
                    assert closed
                    delete.extend(verts)
                    removed_tower_parts += 1
            bmesh.ops.delete(bm, geom=list(set(delete)), context='VERTS')
            bm.to_mesh(mesh)
            bm.free()
            assert removed_tower_parts == 70, removed_tower_parts
        for vertex in mesh.vertices:
            vertex.co = new_world(new_local(old_local(transform @ vertex.co)))
        mesh.update()
        # Authored transforms changed, so old custom normal directions cannot
        # be retained in the old coordinate frame.
        if mesh.has_custom_normals:
            mesh.normals_split_custom_set([(0, 0, 0)] * len(mesh.loops))
        flipped = orient_closed_shells(mesh)
        target = bpy.data.objects.new(PREFIX + source.name, mesh)
        target.matrix_world = Matrix.Identity(4)
        target['originalObject'] = source.name
        target['candidateScope'] = 'Independent placement/grid reconstruction; unfinished wing returns, office module and roof profile'
        collection.objects.link(target)
        added.append(target.name)
        records.append({'source': source.name, 'target': target.name, 'facesReoriented': flipped,
                        'towerColumnPartsRemoved': removed_tower_parts,
                        'sourceOwners': [c.name for c in source.users_collection]})
    # Six-metre module and eight axes are supported by both built photographs
    # and the structural engineer, independently of the obsolete49m box.
    g = RoomGeometry(collection, PREFIX)
    g.materials['paint'] = column_source.data.materials[0]
    axes = mapping['legacy_frame_compatible_transform']['tower_axis_x_G0_to_G7']
    for x in axes:
        depth = 15.94 + (7 - x) / 42 * (18.26 - 15.94)
        for y in [-2.31, depth - 2 + .31]:
            g.box('tower_I_webs', 'paint', (x, y, 26.1), (.16, .42, 52.2))
            for dy in [-.22, .22]:
                g.box('tower_I_flanges', 'paint', (x, y + dy, 26.1), (.48, .055, 52.2))
            for z in [.22, 51.98]:
                g.box('tower_column_caps', 'paint', (x, y, z), (.52, .57, .075))
    columns = g.finish()
    for obj in columns:
        for vertex in obj.data.vertices:
            vertex.co = new_world(vertex.co)
        obj.data.update()
        obj['originalObject'] = column_source.name
        added.append(obj.name)
    assert len(axes) == 8 and all(abs(b - a - 6) < 1e-9 for a, b in zip(axes, axes[1:]))
    assert all(object_fingerprint(bpy.data.objects[name]) == fingerprint for name, fingerprint in original.items())
    review_image(collection, 'candidate-placement')
    path = OUTPUT / 'cbg-envelope202-component.blend'
    bpy.data.libraries.write(str(path), {bpy.data.objects[name] for name in added}, fake_user=True, compress=True)
    fingerprints = {name: object_fingerprint(bpy.data.objects[name]) for name in added}
    report = {'status': 'private-partial-reconstruction-not-for-release', 'baselineSha256': BASE_SHA, 'baselinePath':str(BASE.relative_to(ROOT)),
              'componentPath': str(path.relative_to(ROOT)), 'componentSha256': digest(path),
              'targetCollection': 'CBG_EXTERIOR', 'addedObjects': added,
              'archivedObjects': [o.name for o in sources], 'changedObjects': [],
              'records': records, 'towerAxisX': axes, 'towerAxisSpanMetres': 42,
              'towerHeightMetres': 52.2, 'registrationRmsMetres': mapping['registration_fixed_scale_rms_metres'],
              'originalObjectCount': len(original), 'sourceFileUnchanged': digest(BASE) == BASE_SHA,
              'remainingBeforeRelease': ['Complete stepped teaching-wing footprint/return and low podium.',
                                         'Replace compressed inherited office units with correctly sized modules.',
                                         'Register and cut back highest canopy, rear terrace, core and upper stair.',
                                         'Update exterior/interior/gallery camera coordinates together.',
                                         'Review route/interface and remove only proven duplicate context proxies.']}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = list(added)
    for obj in dst.objects:
        bpy.context.scene.collection.objects.link(obj)
    for layer in bpy.context.scene.view_layers:
        layer.update()
    assert set(o.name for o in dst.objects) == set(added)
    assert all(object_fingerprint(obj) == fingerprints[obj.name] for obj in dst.objects)
    report['verification'] = {'componentReopened': True, 'allAddedFingerprintsMatch': True,
                              'baselineUnchanged': digest(BASE) == BASE_SHA,
                              'everyOriginalObjectPreservedInAuthoringSession': True}
    (OUTPUT / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print('CBG202_CANDIDATE_REOPENED', len(added), flush=True)


if __name__ == '__main__':
    build_candidate()
