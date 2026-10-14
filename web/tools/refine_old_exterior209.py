"""Restore continuous grey-brown brick bonding on OLD's photographed mansard.

Fixed Blender Text Editor configuration. Original mesh, materials and UV layer
remain intact. A copied mesh adds one continuous physical-scale UV layer; source
photographs establish finish and bonding, not surveyed dimensions or paint codes.
"""
from pathlib import Path
import array
import hashlib
import json
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v208.blend'
SOURCE_SHA = 'da07d198617bd18bceaece14682b9d0995a288655b6c5aa0ac8d2765e883b92c'
OUT = ROOT / 'result/blender/old-exterior209'
COMPONENT = OUT / 'old-exterior209-component.blend'
SOURCE = 'OLD_D5_houghton112_mansard_brick'
OWNED = 'OLD209_Houghton_continuous_mansard_brick'
COLLECTION = 'OLD_EXTERIOR'
UV_NAME = 'MansardBond209'
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import object_fingerprint
from refine_portsmouth_exterior207 import material_fingerprint


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh_state(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    for data, key, kind, count in [(obj.data.vertices, 'co', 'f', 3),
                                   (obj.data.loops, 'vertex_index', 'i', 1),
                                   (obj.data.polygons, 'material_index', 'i', 1)]:
        values = array.array(kind, [0]) * (len(data) * count)
        data.foreach_get(key, values)
        digest.update(values.tobytes())
    uv = {}
    for layer in obj.data.uv_layers:
        values = array.array('f', [0]) * (len(layer.data) * 2)
        layer.data.foreach_get('uv', values)
        uv[layer.name] = hashlib.sha256(values.tobytes()).hexdigest()
    return dict(geometry=digest.hexdigest(), uv=uv)


def bond_boundary_audit(obj, layer):
    """Coincident corners on different wall strips must share texture phase."""
    corners = {}
    edges = []
    for face in obj.data.polygons:
        loops = list(face.loop_indices)
        for station, index in enumerate(loops):
            following = loops[(station+1) % len(loops)]
            point = obj.matrix_world @ obj.data.vertices[obj.data.loops[index].vertex_index].co
            endpoint = obj.matrix_world @ obj.data.vertices[obj.data.loops[following].vertex_index].co
            key = tuple(round(float(v), 4) for v in point)
            corners[key] = point
            edges.append((face.index, point, endpoint, Vector(layer.data[index].uv), Vector(layer.data[following].uv)))
    shared = []
    for point in corners.values():
        on_faces = {}
        for face, start, end, uv_start, uv_end in edges:
            delta = end-start
            if delta.length_squared < 1e-12:
                continue
            fraction = (point-start).dot(delta)/delta.length_squared
            if -.00001 <= fraction <= 1.00001 and (point-(start+delta*fraction)).length < .0001:
                on_faces[face] = uv_start + (uv_end-uv_start)*fraction
        if len(on_faces) > 1:
            values = list(on_faces.values())
            shared.append(max((a-b).length for a in values for b in values))
    return dict(sharedBoundaryStations=len(shared), maxCoordinateDifference=max(shared, default=0),
                continuous=sum(delta < 1e-4 for delta in shared))


def render_views(label):
    scene = bpy.data.scenes.new('OLD209_REVIEW_' + label)
    scene.collection.children.link(bpy.data.collections[COLLECTION])
    bpy.context.window.scene = scene
    world = bpy.data.worlds.new(scene.name)
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.75, .79, .83, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .7
    scene.world = world
    sun = bpy.data.objects.new(scene.name + '_sun', bpy.data.lights.new(scene.name + '_sun', 'SUN'))
    scene.collection.objects.link(sun)
    sun.data.energy = 1.7
    sun.data.angle = .18
    sun.rotation_euler = Vector((-.6, .5, -1)).to_track_quat('-Z', 'Y').to_euler()
    camera = bpy.data.objects.new(scene.name + '_camera', bpy.data.cameras.new(scene.name + '_camera'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.clip_end = 500
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.render.image_settings.file_format = 'PNG'
    origin = Vector((-7.28653, -89.75267, 0))
    right = Vector((.455415, .890279, 0))
    outward = Vector((.890279, -.455415, 0))
    cameras = []
    for name, x, z, scale, sideways, up in [('whole', 17, 14, 77, 7, 22),
                                           ('mansard', 0, 23.6, 19, .5, 1)]:
        target = origin + right*x + Vector((0, 0, z))
        camera.location = target + outward*90 + right*sideways + Vector((0, 0, up))
        camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        scene.render.filepath = str(OUT / (label+'-'+name+'.png'))
        bpy.ops.render.render(write_still=True)
        cameras.append(dict(view=name, target=list(target), position=list(camera.location), orthoScale=scale))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for obj in (sun, camera):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    return cameras


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    assert sha(BASE) == SOURCE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    originals = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    materials = {m.name: material_fingerprint(m) for m in bpy.data.materials}
    visibility = {o.name: o.hide_render for o in bpy.data.objects}
    source = bpy.data.objects[SOURCE]
    original_mesh = mesh_state(source)
    before_bond = bond_boundary_audit(source, source.data.uv_layers.active)
    cameras = render_views('before')
    clone = source.copy()
    clone.data = source.data.copy()
    clone.name = OWNED
    clone.data.name = OWNED
    clone['originalObject'] = SOURCE
    clone['webGeometrySource'] = SOURCE
    clone['destinationCollection'] = COLLECTION
    bpy.data.collections[COLLECTION].objects.link(clone)
    # The photographed face is a sloping planar mansard. Use its actual tangent
    # plane, not per-panel resets or a stretched vertical projection.
    points = [source.matrix_world @ source.data.vertices[i].co for i in source.data.polygons[0].vertices]
    origin = points[0]
    horizontal = (points[1]-origin).normalized()
    normal = (points[1]-origin).cross(points[-1]-origin).normalized()
    vertical = normal.cross(horizontal).normalized()
    assert vertical.z > 0 and abs(horizontal.z) < 1e-5
    uv = clone.data.uv_layers.new(name=UV_NAME)
    for face in clone.data.polygons:
        for index in face.loop_indices:
            point = clone.matrix_world @ clone.data.vertices[clone.data.loops[index].vertex_index].co
            uv.data[index].uv = ((point-origin).dot(horizontal), (point-origin).dot(vertical))
    clone.data.uv_layers.active = uv
    uv.active_render = True
    material = source.data.materials[0].copy()
    material.name = 'OLD209_photographed_gray_brown_brick'
    brick = next(n for n in material.node_tree.nodes if n.type == 'TEX_BRICK')
    old_colors = {key: list(brick.inputs[key].default_value) for key in ('Color1','Color2','Mortar')}
    # Grey-brown and restrained pale pointing visible in engineer's built photo.
    # These linear values are visual estimates, not sampled/calibrated standards.
    brick.inputs['Color1'].default_value = (.12, .117, .098, 1)
    brick.inputs['Color2'].default_value = (.078, .078, .066, 1)
    brick.inputs['Mortar'].default_value = (.19, .185, .16, 1)
    brick.inputs['Mortar Size'].default_value = .003
    brick.inputs['Scale'].default_value = 1
    texcoord = next(n for n in material.node_tree.nodes if n.type == 'TEX_COORD')
    uv_node = material.node_tree.nodes.new('ShaderNodeUVMap')
    uv_node.uv_map = UV_NAME
    material.node_tree.links.new(uv_node.outputs['UV'], brick.inputs['Vector'])
    material.node_tree.nodes.remove(texcoord)
    material.diffuse_color = (.105, .103, .086, 1)
    material['finishScope'] = 'Photographed Houghton mansard only; continuous estimated metric brick bond, gray-brown palette and pale pointing'
    clone.data.materials[0] = material
    after_bond = bond_boundary_audit(clone, uv)
    # Shared wall-strip corners intentionally join at one texture coordinate.
    assert after_bond['sharedBoundaryStations'] > 8
    assert after_bond['maxCoordinateDifference'] < 1e-4
    assert before_bond['maxCoordinateDifference'] > 1
    current = mesh_state(clone)
    assert current['geometry'] == original_mesh['geometry']
    assert all(current['uv'][key] == digest for key, digest in original_mesh['uv'].items())
    source.hide_render = True
    source.hide_set(True)
    assert all(object_fingerprint(bpy.data.objects[k]) == v for k, v in originals.items())
    assert all(material_fingerprint(bpy.data.materials[k]) == v for k, v in materials.items())
    owned_state = object_fingerprint(clone)
    bpy.data.libraries.write(str(COMPONENT), {clone}, fake_user=True, compress=True)
    audit = dict(version=209, baseline=str(BASE.relative_to(ROOT)), baselineSha256=SOURCE_SHA,
                 component=str(COMPONENT.relative_to(ROOT)), componentSha256=sha(COMPONENT),
                 addedObjects=[OWNED], archivedObjects=[SOURCE], changedObjects=[],
                 destinationCollection=COLLECTION, targetCollection=COLLECTION, retainNewMaterials=True,
                 geometryAndOriginalUVsPreserved=True, originalObjectCount=len(originals),
                 addedFingerprints={OWNED:owned_state},
                 sourceReference=dict(local='data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_06.jpg',
                     sha256=sha(ROOT/'data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_06.jpg'),
                     url='https://webbyates.com/projects/the-old-building/', rechecked='2026-10-15',
                     projectCompletion=2024, photographCaptureDate='unknown', photographer='Damian Griffiths'),
                 improvement='Continuous 17-panel horizontal bonding and grey-brown brick/pale pointing on photographed two-row Houghton mansard; former per-panel UV resets removed in owned copy.',
                 beforeBondBoundary=before_bond, afterBondBoundary=after_bond,
                 brickWidth=float(brick.inputs['Brick Width'].default_value), rowHeight=float(brick.inputs['Row Height'].default_value),
                 mortarSize=float(brick.inputs['Mortar Size'].default_value),
                 oldColors=old_colors, newColors={key:list(brick.inputs[key].default_value)for key in old_colors},
                 uvProjection=dict(origin=list(origin), horizontal=list(horizontal), vertical=list(vertical), units='metres along actual sloping face'),
                 cameras=cameras, previewLighting='Same AgX, sun1.7, neutral sky.7,12samples for both phases',
                 limitations=['Only photographed Houghton mansard finish is corrected; rear upper brick and roof plant remain planning-based estimates.',
                              'Bond dimensions and color values are visual estimates; reference is not color calibrated and capture date is unspecified.',
                              'Existing building geometry, roof tiers, windows, dormer caps, glass optics/backing and all interiors are retained.',
                              'No additional texture files, mesh faces, speculative equipment or photo pixels are exported.'])
    (OUT/'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    # Independently reopen the saved component against an untouched baseline.
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    with bpy.data.libraries.load(str(COMPONENT), link=False) as (available, loaded):
        assert set(available.objects) == {OWNED}
        loaded.objects = [OWNED]
    restored = loaded.objects[0]
    bpy.data.collections[COLLECTION].objects.link(restored)
    assert object_fingerprint(restored) == owned_state
    assert mesh_state(restored) == current
    restored.hide_render = False
    restored.hide_set(False)
    bpy.data.objects[SOURCE].hide_render = True
    bpy.data.objects[SOURCE].hide_set(True)
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    assert all(object_fingerprint(bpy.data.objects[k]) == v for k, v in originals.items())
    assert all(material_fingerprint(bpy.data.materials[k]) == v for k, v in materials.items())
    assert all(bpy.data.objects[k].hide_render == v for k,v in visibility.items() if k != SOURCE)
    render_views('after')
    verification = dict(savedComponentReopened=True, componentSha256=sha(COMPONENT),
        baselineSha256=sha(BASE), baselineUnchanged=sha(BASE)==SOURCE_SHA,
        originalObjectsVerified=len(originals), originalMaterialsVerified=len(materials),
        originalGeometryMaterialsUVsAndBindingsPreserved=True, allUnrelatedVisibilityPreserved=True,
        ownedGeometryUnchanged=True, sourceUvLayersPreserved=True, continuousMetricBond=after_bond,
        replacementFingerprint=owned_state, addedFaces=0, textureBytesAdded=0,
        allGlassGeometryBackingAndOpticsUnchanged=True, renderedIdenticalLightingWholeAndMansard=True)
    (OUT/'verification.json').write_text(json.dumps(verification, indent=2)+'\n')
    assert sha(COMPONENT) == audit['componentSha256']
    print('OLD209_COMPONENT_VERIFIED', audit['componentSha256'], flush=True)


if __name__ == '__main__':
    run()
    bpy.ops.wm.quit_blender()
