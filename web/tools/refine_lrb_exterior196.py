"""Refine the retained library exterior finishes from archived built photographs.

Run in Blender's Text Editor. Existing geometry, UVs, room structure, pane
opacity and metric brick dimensions are preserved. No measured colour claim.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v195.blend'
BASE_SHA = '93aab89a4f76c5343ee085c6271046294d6f51a801a42b118c8a4445703a4ac2'
OUT = ROOT / 'result/blender/lrb-exterior196'
PREFIX = 'LRB196_FINISH_'
REFERENCES = [
 ('data/collections/library_round5/photos/LRB_5ea4100c9303.jpg',
  'https://tyrensakt.com/projects/lse-library/',
  'Engineer project aerial; unknown capture date; dark roof pavilion, brown brick, pale stone bands'),
 ('data/collections/campus_photos_round3/images/LRB/LRB_LAK_geograph_668683.jpg',
  'https://www.geograph.org.uk/photo/668683',
  '23 January 2008; John Watkins Plaza daylight facade, dark joinery and reflective windows'),
 ('data/建筑图片/LRB_Lionel Robbins Building_Library/01_建筑实拍/exteriors_lse_estate_016.jpg',
  'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate',
  'Undated official corner photograph; original pale stone and brown brick retained; night lighting is not a colour calibration'),
]


def state(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    for data, field, kind, count in ((obj.data.vertices, 'co', 'f', 3),
                                    (obj.data.loops, 'vertex_index', 'i', 1),
                                    (obj.data.polygons, 'material_index', 'i', 1)):
        values = array.array(kind, [0]) * (len(data) * count)
        data.foreach_get(field, values)
        digest.update(values.tobytes())
    uv = {}
    for layer in obj.data.uv_layers:
        values = array.array('f', [0]) * (len(layer.data) * 2)
        layer.data.foreach_get('uv', values)
        uv[layer.name] = hashlib.sha256(values.tobytes()).hexdigest()
    return dict(geometry=digest.hexdigest(), uv=uv)


def family(material):
    name = material.name.lower()
    if any(n.type == 'TEX_BRICK' for n in material.node_tree.nodes):
        return 'brick'
    if material.name == 'LRB_V109_cladding':
        return 'roof-pavilion'
    if 'frame' in name and 'roof' not in name:
        return 'painted-joinery'
    if 'glass' in name and not material.get('webOpacity'):
        return 'reflective-window'
    return None


def finish(source):
    material = source.copy()
    material.name = PREFIX + source.name
    shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    kind = family(source)
    if kind == 'brick':
        # Retain the source metric bond and UV mapping. Only pigment/roughness
        # change; browser's derivative-filtered brick shader remains active.
        texture = next(n for n in material.node_tree.nodes if n.type == 'TEX_BRICK')
        for key, rgb in [('Color1', (.245, .147, .111)),
                         ('Color2', (.286, .177, .133)),
                         ('Mortar', (.29, .267, .23))]:
            texture.inputs[key].default_value = (*rgb, 1)
        shader.inputs['Base Color'].default_value = (.265, .162, .122, 1)
        shader.inputs['Roughness'].default_value = .86
        shader.inputs['Metallic'].default_value = 0
    elif kind == 'roof-pavilion':
        shader.inputs['Base Color'].default_value = (.155, .179, .185, 1)
        shader.inputs['Roughness'].default_value = .64
        shader.inputs['Metallic'].default_value = .08
    elif kind == 'painted-joinery':
        shader.inputs['Base Color'].default_value = (.065, .078, .078, 1)
        shader.inputs['Roughness'].default_value = .36
        shader.inputs['Metallic'].default_value = .04
    elif kind == 'reflective-window':
        # Keep proxies opaque wherever room registration is not verified.
        # Clear roof aperture and pavilion panes are explicitly excluded.
        shader.inputs['Base Color'].default_value = (.128, .166, .179, 1)
        shader.inputs['Roughness'].default_value = .13
        shader.inputs['Metallic'].default_value = 0
        shader.inputs['IOR'].default_value = 1.5
    material.diffuse_color = shader.inputs['Base Color'].default_value
    material['finishScope'] = 'LRB exterior photograph-guided ' + kind
    return material


def preview(phase):
    scene = bpy.data.scenes.new('LRB196_preview_' + phase)
    collection = bpy.data.collections.new(scene.name + '_objects')
    scene.collection.children.link(collection)
    points = []
    for obj in bpy.data.collections['LRB_EXTERIOR'].all_objects:
        if obj.type in {'MESH', 'FONT', 'CURVE'} and not obj.hide_render:
            collection.objects.link(obj)
            if obj.type == 'MESH':
                points.extend(obj.matrix_world @ Vector(v) for v in obj.bound_box)
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (low + high) / 2
    world = bpy.data.worlds.new(scene.name + '_world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[1].default_value = .65
    env = world.node_tree.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(str(ROOT / 'web/public/environment/kloppenheim-daylight-1k.hdr'), check_existing=True)
    world.node_tree.links.new(env.outputs['Color'], world.node_tree.nodes['Background'].inputs[0])
    scene.world = world
    light_data = bpy.data.lights.new(scene.name + '_sun', 'SUN')
    light_data.energy, light_data.angle = 1.8, .12
    sun = bpy.data.objects.new(light_data.name, light_data)
    collection.objects.link(sun)
    sun.rotation_euler = Vector((-.6, .5, -1)).to_track_quat('-Z', 'Y').to_euler()
    camera_data = bpy.data.cameras.new(scene.name + '_camera')
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 850
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    views = {'whole': (Vector((-65, -90, 45)), 105),
             'roof-opposite': (Vector((65, 90, 55)), 105)}
    for label, (offset, scale) in views.items():
        camera.location = center + offset
        camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera_data.ortho_scale = scale
        scene.render.filepath = str(OUT / (phase + '-' + label + '.png'))
        bpy.ops.render.render(write_still=True, scene=scene.name)
    bpy.data.scenes.remove(scene)
    bpy.data.collections.remove(collection)


def build_component():
    OUT.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    original = {o.name: state(o) for o in bpy.data.objects if o.type == 'MESH'}
    original_bindings = {o.name: [m.name if m else None for m in o.data.materials]
                         for o in bpy.data.objects if o.type == 'MESH'}
    preview('before')
    materials, replacements, bindings = {}, [], []
    target = bpy.data.collections['LRB_EXTERIOR']
    for source in list(target.all_objects):
        if source.type != 'MESH' or source.hide_render:
            continue
        slots = [(i, m) for i, m in enumerate(source.data.materials) if m and family(m)]
        if not slots:
            continue
        obj = source.copy()
        obj.data = source.data.copy()
        obj.name = PREFIX + source.name
        obj['originalObject'] = source.name
        obj['webGeometrySource'] = source.get('webGeometrySource', source.name)
        obj['finishScope'] = 'LRB retained exterior finishes only; source UV, geometry, opacity and rooms preserved'
        target.objects.link(obj)
        for index, material in slots:
            if material.name not in materials:
                materials[material.name] = finish(material)
            obj.data.materials[index] = materials[material.name]
            bindings.append(dict(object=obj.name, slot=index, originalMaterial=material.name,
                                 material=materials[material.name].name, family=family(material)))
        source.hide_render = True
        source.hide_set(True)
        obj.hide_render = False
        obj.hide_set(False)
        replacements.append(dict(originalObject=source.name, original=source.name,
                                 replacement=obj.name, targetCollection='LRB_EXTERIOR'))
        assert state(obj) == original[source.name]
    assert len(replacements) > 20
    assert all(state(bpy.data.objects[n]) == value for n, value in original.items())
    assert all([m.name if m else None for m in bpy.data.objects[n].data.materials] == value
               for n, value in original_bindings.items())
    preview('after')
    path = OUT / 'lrb-exterior196-component.blend'
    owned = {bpy.data.objects[r['replacement']] for r in replacements}
    bpy.data.libraries.write(str(path), owned | set(materials.values()), fake_user=True)
    report = dict(version=196, baseline=str(BASE.relative_to(ROOT)), baselineSha256=BASE_SHA,
                  componentPath=str(path.relative_to(ROOT)), componentSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  targetCollection='LRB_EXTERIOR', addedObjects=[r['replacement'] for r in replacements],
                  archivedObjects=[r['originalObject'] for r in replacements], changedObjects=[], replacements=replacements,
                  bindings=bindings, geometryAndOriginalUVPreserved=True,
                  originalStates={r['originalObject']: original[r['originalObject']] for r in replacements},
                  references=[dict(path=p, sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest(), url=u, scope=s) for p,u,s in REFERENCES],
                  improvements=['Roof pavilion cladding changed from pale grey to photo-supported dark grey; original roof mass and dormers retained.',
                                'Existing two brick colour families harmonised to lower-contrast brown pigment with subdued warm-grey mortar, retaining metric bonds and browser antialiasing.',
                                'Painted exterior joinery receives lower metallic charcoal finish; actual geometry and window divisions retained.',
                                'Reflective opaque window proxies use less milky colour and lower roughness; transparent dome aperture and café panes retained exactly.'],
                  rootCauseCorrection='Existing GLB surfaceDetail already transfers brick nodes; no missing-brick-export claim and no replacement image texture.',
                  previews=['before-whole.png','after-whole.png','before-roof-opposite.png','after-roof-opposite.png'],
                  previewLighting='Identical HDR, AgX,1.8sun,.65background,16Cycles samples; exterior-only comparison',
                  limitations=['Colour is photograph guided, not a calibrated material survey; aerial and plaza references are historical/undated.',
                               'No2026 roof completion claim; existing roof mass, unknown backs and entrance canopy retained.',
                               'Opaque windows remain opaque pending registered rooms; public interior structure and all original meshes/UVs/material bindings untouched.',
                               'Metric brick dimensions and per-corner UVs inherited, not a newly measured masonry survey.'])
    (OUT / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    bpy.ops.wm.open_mainfile(filepath=str(path))
    checks = []
    for r in replacements:
        obj = bpy.data.objects[r['replacement']]
        assert state(obj) == original[r['originalObject']]
        assert obj['originalObject'] == r['originalObject']
        checks.append(dict(object=obj.name, geometryPreserved=True, originalUVPreserved=True))
    verification = dict(savedComponentReopened=True, baselineUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
                        componentSha256=hashlib.sha256(path.read_bytes()).hexdigest(), replacementCount=len(checks), objects=checks,
                        addedTriangles=0, addedImages=0)
    (OUT / 'verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    print('LRB196_COMPONENT_READY', len(replacements), len(materials), flush=True)


if __name__ == '__main__':
    build_component()
