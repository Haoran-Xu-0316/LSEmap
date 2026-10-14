"""Build a bounded private teaching-wing facade contribution from203.

Call build_candidate() in Blender's Text Editor. Fixed local files only.
203 floorplates, tower and interiors remain read-only. The component contains
only four replacements and added wing facade families, with exact merge names.
Photographs establish expression and locations, not exact window/bay counts.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from build_room_samples167 import RoomGeometry
from integrate_exterior_round194 import object_fingerprint
from refine_ground_orientation199 import closed_islands, signed_volume

SOURCE = ROOT / 'result/blender/cbg-wing203/cbg-wing203-component.blend'
SOURCE_SHA = '59d71a8ab65ccf1d7d7f937d774d00d1b71aeb85c3f57a6350cd3370253ad621'
NATIVE = ROOT / 'result/blender/LSE_campus_detailed_v203.blend'
NATIVE_SHA = '976e645ef4b58e19485feff1fe3ff2fb64d9b5d497739642a2429548d821df8a'
ENVELOPE = ROOT / 'result/blender/cbg-envelope202/cbg-envelope202-component.blend'
ENVELOPE_SHA = 'aee42651de3fc344b88306172f94bbd6db1d33b6c5152e7c7ddb646263000228'
OUT = ROOT / 'result/blender/cbg-teaching204'
PREFIX = 'CBG204_TEACHING_'
TARGET_PREFIX = 'CBG203_WING_registered_'
REPLACED = [TARGET_PREFIX + family for family in [
    'teaching_glazing', 'teaching_mullions', 'teaching_transoms', 'houghton_stone_panels']]
HEIGHT = 25.0
STEP = HEIGHT / 6


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def material(name, color, roughness=.55):
    result = bpy.data.materials.new(PREFIX + name)
    result.use_nodes = True
    result.diffuse_color = (*color, 1)
    shader = result.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = result.diffuse_color
    shader.inputs['Roughness'].default_value = roughness
    return result


def rectangular_member(geometry, family, material_key, start, end, width=.32, depth=.30):
    """Exterior rectangular HSS proxy; no unsupported internal wall thickness."""
    a, b = Vector(start), Vector(end)
    axis = (b-a).normalized()
    first = axis.cross(Vector((0, 0, 1)))
    if first.length < .001:
        first = Vector((1, 0, 0))
    first.normalize()
    second = axis.cross(first).normalized()
    vertices = [tuple(p + first*width*u/2 + second*depth*v/2)
                for p in [a, b] for u, v in [(-1, -1), (1, -1), (1, 1), (-1, 1)]]
    geometry.add(family, material_key, vertices,
                 [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
                  (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])


def build_candidate():
    OUT.mkdir(parents=True, exist_ok=True)
    protected_hashes = {str(path): digest(path) for path in [SOURCE, NATIVE, ENVELOPE]}
    assert protected_hashes[str(SOURCE)] == SOURCE_SHA
    assert protected_hashes[str(NATIVE)] == NATIVE_SHA
    assert protected_hashes[str(ENVELOPE)] == ENVELOPE_SHA
    source_audit = json.loads((SOURCE.parent/'audit.json').read_text())
    mapping = json.loads((ROOT/'result/blender/cbg-georegistration202/rebuild-mapping.json').read_text())
    f = mapping['frame']
    origin = Vector((*f['origin_G7_SW_world'], 0))
    ex, ey = Vector((*f['x_unit_SW'], 0)), Vector((*f['y_unit_SE_rear'], 0))
    def world(point):
        return origin + ex*point[0] + ey*point[1] + Vector((0, 0, point[2]))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(SOURCE), link=False) as (available, loaded):
        loaded.objects = list(source_audit['addedObjects'])
    originals = {obj.name: obj for obj in loaded.objects}
    protected = {name: object_fingerprint(obj) for name, obj in originals.items()}
    collection = bpy.data.collections.new('CBG204_TEACHING_FACADE_PRIVATE')
    bpy.context.scene.collection.children.link(collection)
    geometry = RoomGeometry(collection, PREFIX)
    def source_material(suffix):
        return next(obj.data.materials[0] for name, obj in originals.items() if name.endswith(suffix))
    geometry.materials.update(
        glass=source_material('registered_teaching_glazing'),
        frame=source_material('registered_teaching_mullions'),
        stone=source_material('registered_houghton_stone_panels'),
        paint=source_material('registered_teaching_columns'),
        neutral=material('neutral_shade_exterior', (.76, .77, .73)),
        red=material('red_shade_inner_face', (.69, .035, .025)),
        orange=material('orange_shade_accent', (.90, .23, .028)),
        joint=material('stone_horizontal_recess', (.32, .33, .30)))
    outline = [tuple(point) for point in source_audit['registeredWingPolygon']]
    area = sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(outline, outline[1:]+outline[:1]))
    records = []
    edge_frames = {}
    for inherited in source_audit['perimeter']:
        edge = inherited['edge']
        a, b = outline[edge], outline[(edge+1) % len(outline)]
        delta = Vector((b[0]-a[0], b[1]-a[1]))
        length, axis = delta.length, delta.normalized()
        outward = Vector((axis.y, -axis.x))*(1 if area > 0 else -1)
        angle = math.atan2(axis.y, axis.x)
        def at(distance, z, offset=0, a=a, axis=axis, outward=outward):
            return (a[0]+axis.x*distance+outward.x*offset,
                    a[1]+axis.y*distance+outward.y*offset, z)
        edge_frames[edge] = (length, angle, at)
        divisions = inherited['estimatedGlazingDivisions']
        bays = inherited['nominalStructuralBays']
        glazing_width = length/divisions
        # Keep inherited203 partitions. Replace the generic regular curtain
        # with double-height teaching zones and upper-level opening-vent bands.
        zones = [(0, STEP), (STEP, 3*STEP), (3*STEP, 4*STEP),
                 (4*STEP, 5*STEP), (5*STEP, HEIGHT)]
        for bottom, top in zones:
            for division in range(divisions):
                center = (division+.5)*glazing_width
                geometry.box('teaching_glazing', 'glass', at(center, (bottom+top)/2),
                             (glazing_width-.075, .035, top-bottom-.18), angle)
                geometry.box('teaching_mullions', 'frame', at(division*glazing_width, (bottom+top)/2, .05),
                             (.065, .15, top-bottom), angle)
                # End glass remains cross-braced; other upper glazing gains the
                # high-level opening-vent line visible in026. Teaching pair has
                # the actual intermediate glass transom without a shade split.
                levels = [top-.72]
                if top-bottom > STEP*1.5:
                    levels.append(2*STEP)
                for z in levels:
                    geometry.box('teaching_transoms', 'frame', at(center, z, .07),
                                 (glazing_width, .10, .055), angle)
            geometry.box('teaching_mullions', 'frame', at(length, (bottom+top)/2, .05),
                         (.065, .15, top-bottom), angle)
        if edge == 6:
            # RSHP026: limestone piers spanL1/L2 with horizontal rustication.
            # Widths reuse203bay locations, not a new asserted measured count.
            for bay in range(bays):
                stone_width = length/bays*.61
                center = (bay+.5)*length/bays
                geometry.box('houghton_stone_panels', 'stone', at(center, 2*STEP, .24),
                             (stone_width, .15, 2*STEP-.34), angle)
                for z in [STEP + course*(2*STEP)/9 for course in range(1, 9)]:
                    geometry.box('stone_horizontal_banding', 'joint', at(center, z, .319),
                                 (stone_width, .012, .022), angle)
        if edge in [2, 6]:
            # Preserve203 module placement. Composite blades give a neutral
            # outer face and coloured inward face, as the architect describes.
            depth = .65 if edge == 6 else .45
            for bottom, top in [(STEP, 3*STEP), (3*STEP, 4*STEP),
                                (4*STEP, 5*STEP), (5*STEP, HEIGHT)]:
                blade_height = top-bottom-.34
                for division in range(divisions+1):
                    distance = division*glazing_width
                    geometry.box('solar_blade_neutral_outer', 'neutral', at(distance, (bottom+top)/2, .35+depth/2),
                                 (.09, depth, blade_height), angle)
                    # Red primary, sparse orange accents are explicit user
                    # art direction; they are not claimed as surveyed colours.
                    color_key = 'orange' if division % 6 == 5 else 'red'
                    color_distance = distance + (.052 if edge == 6 else -.052)
                    geometry.box('solar_blade_'+color_key+'_inner', color_key,
                                 at(color_distance, (bottom+top)/2, .35+depth/2),
                                 (.014, depth-.02, blade_height), angle)
                for z in [bottom+.11, top-.10]:
                    geometry.box('solar_shade_head_sill', 'neutral', at(length/2, z, .35+depth/2),
                                 (length, depth+.05, .11), angle)
            records.append({'edge': edge, 'shadeDivisionsFrom203': divisions,
                            'doubleHeightTeachingSpan': [STEP, 3*STEP], 'estimatedShadeDepth': depth})
    length, angle, at = edge_frames[7]
    brace_spans = []
    for pair in range(3):
        bottom, top = pair*2*STEP+.18, (pair+1)*2*STEP-.18
        left, right = .30, length-.30
        rectangular_member(geometry, 'end_two_storey_HSS_X_braces', 'paint',
                           at(left, bottom, .68), at(right, top, .68))
        rectangular_member(geometry, 'end_two_storey_HSS_X_braces', 'paint',
                           at(left, top, .68), at(right, bottom, .68))
        geometry.box('end_brace_cruciform_plates', 'paint', at(length/2, (bottom+top)/2, .875),
                     (.78, .10, .29), angle)
        geometry.box('end_brace_cruciform_plates', 'paint', at(length/2, (bottom+top)/2, .875),
                     (.29, .10, .78), angle)
        for distance, z in [(left, bottom), (right, top), (left, top), (right, bottom)]:
            geometry.box('end_brace_connection_plates', 'paint', at(distance, z, .82),
                         (.45, .11, .55), angle)
        brace_spans.append({'edge': 7, 'lower': bottom, 'upper': top, 'twoStoreys': True})
    # Roof terrace glass is clearly present in020; no furniture or planter count
    # is fabricated. Only exposed front/end perimeters are added.
    for edge in [6, 7]:
        length, angle, at = edge_frames[edge]
        geometry.box('roof_terrace_glass_guard', 'glass', at(length/2, HEIGHT+.63, -.16),
                     (length-.15, .035, 1.08), angle)
        geometry.box('roof_terrace_guard_toprail', 'frame', at(length/2, HEIGHT+1.19, -.16),
                     (length, .075, .075), angle)
    objects = geometry.finish()
    for obj in objects:
        for vertex in obj.data.vertices:
            vertex.co = world(vertex.co)
        obj.data.update()
        obj['candidateScope'] = 'Bounded204 teaching facade; private reconstruction, inherited203 division estimates'
        family = obj.name[len(PREFIX):]
        if family in ['teaching_glazing', 'teaching_mullions', 'teaching_transoms', 'houghton_stone_panels']:
            obj['replaceObject'] = TARGET_PREFIX+family
    assert {obj['replaceObject'] for obj in objects if 'replaceObject' in obj} == set(REPLACED)
    assert all(object_fingerprint(obj) == protected[name] for name, obj in originals.items())
    component = OUT/'cbg-teaching204-component.blend'
    bpy.data.libraries.write(str(component), set(objects), fake_user=True, compress=True)
    fingerprints = {obj.name: object_fingerprint(obj) for obj in objects}
    replacements = [{'source': obj['replaceObject'], 'target': obj.name}
                    for obj in objects if 'replaceObject' in obj]
    # A real library round-trip verifies exact meshes, names and material nodes.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component), link=False) as (available, reopened):
        reopened.objects = list(fingerprints)
    reopened_shells = 0
    for obj in reopened.objects:
        bpy.context.scene.collection.objects.link(obj)
        assert object_fingerprint(obj) == fingerprints[obj.name], obj.name
        mesh = bmesh.new()
        mesh.from_mesh(obj.data)
        mesh.normal_update()
        for faces, closed in closed_islands(mesh):
            assert closed and signed_volume(faces) > 0, obj.name
            reopened_shells += 1
        mesh.free()
    # Append203 context solely for render, keeping it out of the delivered file.
    with bpy.data.libraries.load(str(SOURCE), link=False) as (available, context):
        context.objects = [name for name in source_audit['addedObjects'] if name not in REPLACED]
    for obj in context.objects:
        bpy.context.scene.collection.objects.link(obj)
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new(PREFIX+'review_world')
    scene.world.color = (.80, .82, .84)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
    scene.render.resolution_percentage = 100
    camera = bpy.data.objects.new(PREFIX+'review_camera', bpy.data.cameras.new(PREFIX+'review_camera'))
    scene.collection.objects.link(camera)
    camera.data.type = 'ORTHO'
    scene.camera = camera
    for name, position, target, scale in [
        ('houghton-long-face', (43, -70, 32), (15, -8, 13), 69),
        ('square-braced-end', (-56, -57, 35), (-3, -7, 20), 65),
        ('teaching-end-detail', (-47, -45, 24), (-9, -10, 13), 37)]:
        camera.data.ortho_scale = scale
        camera.location = world(position)
        camera.rotation_euler = (world(target)-camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(OUT/(name+'.png'))
        bpy.ops.render.render(write_still=True)
    assert all(digest(Path(path)) == value for path, value in protected_hashes.items())
    report = {
        'status': 'private-bounded-facade-candidate-not-for-release',
        'componentPath': str(component.relative_to(ROOT)), 'componentSha256': digest(component),
        'inputWing203Sha256': SOURCE_SHA, 'nativeBaselineSha256': NATIVE_SHA,
        'inputEnvelope202Sha256': ENVELOPE_SHA,
        'addedObjects': list(fingerprints), 'replacements': replacements,
        'removeObjects': REPLACED, 'contextObjectsExcludedFromComponent': len(context.objects),
        'sha256ByProtectedInput': protected_hashes, 'shadeZones': records,
        'endBracing': brace_spans, 'registeredWingPolygon': outline,
        'sourceEvidence': [{'path': str(path.relative_to(ROOT)), 'sha256': digest(path),
                            'role': 'built photograph; capture date unknown'}
                           for path in [ROOT/'data/collections/exteriors/images/cbg_rshp_020.jpg',
                                        ROOT/'data/collections/exteriors/images/cbg_rshp_026.jpg']],
        'primaryPage': {'url': 'https://rshp.com/projects/education/lse-centre-building/',
                        'verifiedDate': '2026-10-14',
                        'facts': ['L1/L2 double-storey rainscreen and solar-louvre expression',
                                  'Neutral/solid appearance from south; bright/perforate from north',
                                  'Houghton lower limestone has horizontal bands',
                                  'External standard HSS cross braces span two storeys with cruciform plate intersections']},
        'paletteRole': 'Explicit user preference: red primary, orange accent; not a built colour survey',
        'floorSolidProof': geometry.solid_proof,
        'verification': {'reopenedFingerprintCount': len(fingerprints),
                         'positiveClosedShellCount': reopened_shells, 'newShellsOutward': True,
                         'inputMeshesUnmodified': True, 'allProtectedInputHashesPreserved': True},
        'limitations': ['Height25m/sixvisiblelevels retained from203; GIS7level tag remains unreconciled.',
                        'Structural bays and glazing divisions reused203 estimates; no exact wing-window count claim.',
                        'Shade projection, stone-course spacing and HSS dimensions are visual estimates.',
                        'Four source objects replaced; retained tower-edge oldfin is intentionally root-owned.',
                        'No public asset, model metadata, interior partition or full building copied to component.']}
    (OUT/'audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print('CBG204_TEACHING_REOPENED', len(fingerprints), reopened_shells, flush=True)
    return report


if __name__ == '__main__':
    build_candidate()
