"""Restore OLD Clare Market's photographed recessed blue entrance portal.

Run in Blender's Text Editor. The accepted campus file is read only. One portal
study is written as an independent component, with inherited opening registration
and photo-estimated lining proportions; no survey accuracy is claimed.
"""
from pathlib import Path
import array
import hashlib
import json
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v200.blend'
OUT = ROOT / 'result/blender/old-exterior201'
BASE_SHA = 'f893370b3bb5c7e87720ff38a8e1f3c65a1bf0aebc71265cba0c4137408fc552'
PREFIX = 'OLD201_CLARE_'
SOURCES = {
    'joinery': 'OLD_GLAZING_NEXT_retained_blue',
    'glazing': 'GLASS181_OLD_NEXT_GLAZING152_Clare_photographed_glass',
    'pulls': 'OLD_V53_Clare_metal',
    'transom': 'OLD_GLAZING_NEXT_portal_upper_transom',
    'student_services': 'OLD_V53_Portal_Student Services Centre',
    'building_name': 'OLD_V53_Portal_Old Building',
}
sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrate_exterior_round194 import object_fingerprint


def uv_state(obj):
    layers = {}
    if obj.type == 'MESH':
        for layer in obj.data.uv_layers:
            values = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            layers[layer.name] = hashlib.sha256(values.tobytes()).hexdigest()
    return layers


def registration():
    record = json.loads((ROOT / 'result/blender/stage49/old-clare-audit.json').read_text())
    origin, right, normal = [Vector(record[key]) for key in ['origin', 'right', 'outward']]
    width = record['edgeLength'] / 5 - .92
    centre = -record['edgeLength'] * .4
    return origin, right, normal, centre, width


def portal_coordinates(obj, vertex, origin, right, normal):
    p = obj.matrix_world @ vertex.co - origin
    return Vector((p.dot(right), p.dot(normal), p.z))


def world(x, depth, z, origin, right, normal):
    return origin + right * x + normal * depth + Vector((0, 0, z))


def render_review(phase, origin, right, normal, centre):
    scene = bpy.data.scenes.new('OLD201_review_' + phase)
    coll = bpy.data.collections.new(scene.name)
    scene.collection.children.link(coll)
    for obj in bpy.data.collections['OLD_EXTERIOR'].all_objects:
        if not obj.hide_render:
            coll.objects.link(obj)
    sky = bpy.data.worlds.new(scene.name)
    sky.use_nodes = True
    sky.node_tree.nodes['Background'].inputs['Color'].default_value = (.82, .85, .88, 1)
    sky.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
    scene.world = sky
    light = bpy.data.lights.new(scene.name + '_sun', 'SUN')
    light.energy, light.angle = 1.6, .12
    sun = bpy.data.objects.new(light.name, light)
    coll.objects.link(sun)
    sun.rotation_euler = Vector((-.6, .5, -1)).to_track_quat('-Z', 'Y').to_euler()
    camera = bpy.data.cameras.new(scene.name + '_camera')
    cam = bpy.data.objects.new(camera.name, camera)
    coll.objects.link(cam)
    scene.camera = cam
    focus = world(centre + 1.05, .15, 3.0, origin, right, normal)
    cam.location = focus + normal * 20 + right * 3.4 + Vector((0, 0, 1.0))
    cam.rotation_euler = (focus - cam.location).to_track_quat('-Z', 'Y').to_euler()
    camera.type, camera.ortho_scale = 'ORTHO', 8.6
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.render.filepath = str(OUT / (phase + '-clare-portal.png'))
    bpy.ops.render.render(write_still=True, scene=scene.name)
    bpy.data.scenes.remove(scene)
    for obj in list(coll.objects):
        if obj.type in {'LIGHT', 'CAMERA'}:
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(coll)
    bpy.data.worlds.remove(sky)


def make_lining(material, origin, right, normal, centre, width):
    """Three closed solid panels reveal an open blue portal; no hidden wall cut."""
    vertices, faces = [], []
    inner_half = width * .68 / 2
    outer_half = width / 2
    def panel(x0, x1, d0, d1, z0, z1):
        start = len(vertices)
        vertices.extend([world(x, d, z, origin, right, normal)
                         for z in [z0, z1] for d in [d0, d1] for x in [x0, x1]])
        faces.extend([tuple(start + i for i in face) for face in
                      [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4),
                       (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]])
    # The opening and landing are inherited. The 0.40m cheeks, 0.28m head,
    # and 0.41m recess are proportion estimates from the user photo.
    panel(centre - outer_half, centre - inner_half, -.385, .025, .75, 5.1975)
    panel(centre + inner_half, centre + outer_half, -.385, .025, .75, 5.1975)
    panel(centre - inner_half, centre + inner_half, -.385, .025, 4.9175, 5.1975)
    mesh = bpy.data.meshes.new(PREFIX + 'blue_portal_lining')
    # right/outward/up is a left-handed registration; reverse cap and wall winding.
    mesh.from_pydata(vertices, [], [tuple(reversed(face)) for face in faces])
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.data.collections['OLD_EXTERIOR'].objects.link(obj)
    obj['evidence'] = 'User Clare Market frontal photo: broad blue recessed jambs and soffit'
    obj['dimensionBasis'] = 'Inherited opening; photo-estimated 68 percent glazed width and 0.41m recess'
    return obj


def build_component():
    OUT.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    fingerprints = {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}
    visibility = {obj.name: obj.hide_render for obj in bpy.data.objects}
    origin, right, normal, centre, width = registration()
    if not (OUT / 'before-clare-portal.png').exists():
        render_review('before', origin, right, normal, centre)
    owned, changes, materials = [], [], {}
    portal_font = None
    for role, name in SOURCES.items():
        source = bpy.data.objects[name]
        assert not source.hide_render and not source.constraints and source.parent is None
        clone = source.copy()
        clone.data = source.data.copy()
        clone.name = PREFIX + role
        clone.data.name = clone.name
        # Give unchanged material/font copies component-owned identities so that
        # appending to the complete campus cannot rename their dependencies.
        for index, material in enumerate(clone.data.materials):
            if material.name not in materials:
                copy = material.copy()
                copy.name = PREFIX + 'material_' + str(len(materials))
                materials[material.name] = copy
            clone.data.materials[index] = materials[material.name]
        if clone.type == 'FONT':
            if portal_font is None:
                portal_font = source.data.font.copy()
                portal_font.name = PREFIX + 'inscription_font'
            clone.data.font = portal_font
        clone['originalObject'] = name
        clone['finishScope'] = 'Only Clare Student Services lower-bay portal; all shared non-portal members retained'
        bpy.data.collections['OLD_EXTERIOR'].objects.link(clone)
        changed, unchanged = 0, 0
        if clone.type == 'MESH':
            for vertex in clone.data.vertices:
                p = portal_coordinates(clone, vertex, origin, right, normal)
                # The shared joinery/glass retain four ordinary bays and all
                # upper bays. The metal mesh retains both existing stair rails.
                inside = (abs(p.x - centre) <= width / 2 + .001
                          and .69 <= p.z <= 5.21 and -.30 <= p.y <= .10)
                if inside:
                    if role != 'pulls':
                        p.x = centre + (p.x - centre) * .68
                    if p.z > 3.36:
                        p.z = 3.36 + (p.z - 3.36) * ((4.9175 - 3.36) / (5.1975 - 3.36))
                    p.y -= .35
                    vertex.co = clone.matrix_world.inverted() @ world(*p, origin, right, normal)
                    changed += 1
                else:
                    unchanged += 1
            clone.data.update()
            assert changed > 0
            assert uv_state(clone) == uv_state(source)
        else:
            clone.location -= normal * .35
            changed = 1
        source.hide_render = True
        source.hide_set(True)
        clone.hide_render = False
        clone.hide_set(False)
        owned.append(clone)
        changes.append(dict(source=name, replacement=clone.name, changedVertices=changed,
                            unchangedVertices=unchanged, originalCornerUVsRetained=clone.type == 'MESH'))
    lining = make_lining(owned[0].data.materials[0],
                         origin, right, normal, centre, width)
    owned.append(lining)
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    assert all(object_fingerprint(bpy.data.objects[name]) == expected for name, expected in fingerprints.items())
    assert all(bpy.data.objects[name].hide_render == expected for name, expected in visibility.items() if name not in SOURCES.values())
    component = OUT / 'old-exterior201-component.blend'
    bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)
    added = [obj.name for obj in owned]
    owned_fingerprints = {obj.name: object_fingerprint(obj) for obj in owned}
    # Reopen the unchanged full baseline and append only saved component objects.
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    with bpy.data.libraries.load(str(component), link=False) as (source, target):
        assert set(added) <= set(source.objects)
        target.objects = list(added)
    for obj in target.objects:
        bpy.data.collections['OLD_EXTERIOR'].objects.link(obj)
        obj.hide_render = False
        obj.hide_set(False)
    for name in SOURCES.values():
        bpy.data.objects[name].hide_render = True
        bpy.data.objects[name].hide_set(True)
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    mismatches = [name for name, expected in fingerprints.items() if object_fingerprint(bpy.data.objects[name]) != expected]
    assert not mismatches, mismatches[:20]
    mismatches = [name for name, expected in owned_fingerprints.items() if object_fingerprint(bpy.data.objects[name]) != expected]
    assert not mismatches, mismatches
    assert set(bpy.data.objects.keys()) - set(fingerprints) == set(added)
    render_review('after', origin, right, normal, centre)
    references = []
    for path, supports in [
        ('data/collections/old-clare-reference/front.png', 'Broad blue portal lining surrounds a narrower recessed glazed entrance'),
        ('data/collections/old-user-reference/houghton-entrance.png', 'Houghton arch, blue casements and stepped landing retained'),
        ('data/collections/old-user-reference/final-sale-side.jpg', 'Arch and forecourt configuration retained; historical nighttime photo'),
    ]:
        references.append(dict(path=path, sha256=hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                               supports=supports, captureDate='unknown'))
    report = dict(version=201, targetCollection='OLD_EXTERIOR', baseline=str(BASE.relative_to(ROOT)),
                  baselineSha256=BASE_SHA, componentPath=str(component.relative_to(ROOT)),
                  componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),
                  addedObjects=added, archivedObjects=list(SOURCES.values()), changedObjects=[], changes=changes,
                  originalGeometryAndBindingsPreserved=True, originalCornerUVsPreserved=True,
                  sourceModelUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
                  savedComponentReopened=True, addedFingerprints=owned_fingerprints,
                  registration=dict(origin=list(origin), right=list(right), outward=list(normal)),
                  portal=dict(outerOpeningWidth=width, glazingWidthFactor=.68,
                              jambLiningWidth=width * .16, liningDepth=.41, headHeight=.28,
                              joineryRecession=.35, sourceOpeningAndLandingRetained=True),
                  references=references,
                  previews=['before-clare-portal.png', 'after-clare-portal.png'],
                  scope='Clare Student Services recessed blue portal only; shared meshes retain all non-portal members',
                  limitations=['Portal proportions and recess depth are photo-estimated, not surveyed dimensions.',
                               'Blue paint and glazing material parameters are inherited; no calibrated colour match is claimed.',
                               'Frith carvings, Houghton relief, roof and unseen elevations remain model interpretations.',
                               'Current refurbishment condition is not established by undated private reference photographs.'])
    (OUT / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    verification = dict(baselineUnchanged=report['sourceModelUnchanged'], savedComponentReopened=True,
                        originalObjectsVerified=len(fingerprints), addedObjectsVerified=len(added),
                        unrelatedVisibilityPreserved=True, originalGeometryAndCornerUVsPreserved=True,
                        addedFingerprints=owned_fingerprints)
    (OUT / 'verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    assert report['sourceModelUnchanged']
    print('OLD201_COMPONENT_REOPENED', len(added), len(fingerprints), flush=True)


if __name__ == '__main__':
    build_component()
