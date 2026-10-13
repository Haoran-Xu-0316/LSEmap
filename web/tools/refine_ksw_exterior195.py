"""Photo-guided 20 Kingsway facade finish and paired upper sash correction.

Run this file in Blender. Originals, UVs, room studies, roof and unseen envelope
remain intact. Only the saved owned component is handed to the release assembly.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/ksw-exterior195'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v194.blend'
BASE_SHA = 'bcd7292cfda4c43ed4fd7622f564a5d3ce7ef8ac0360ba00d68b4081bd363c8e'
COLLECTION = 'KSW_EXTERIOR'
PREFIX = 'KSW_NEXT_EXTERIOR195_'
PHOTO = ROOT / 'data/建筑图片/KSW_20 Kingsway/01_建筑实拍/small_round5_KSW_handbook-000.png'
PHOTO_SECOND = ROOT / 'data/建筑图片/KSW_20 Kingsway/01_建筑实拍/exteriors_lse_estate_009.jpg'


def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for sequence, field, kind, width in [(obj.data.vertices, 'co', 'f', 3),
                                            (obj.data.loops, 'vertex_index', 'i', 1),
                                            (obj.data.polygons, 'material_index', 'i', 1)]:
            values = array.array(kind, [0]) * (len(sequence) * width)
            sequence.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            digest.update(values.tobytes())
        digest.update(str([m.name if m else None for m in obj.data.materials]).encode())
    return digest.hexdigest()


def registration():
    record = next(b for b in json.loads((ROOT / 'result/blender/site_geometry.json').read_text())['buildings'] if b['code'] == 'KSW')
    ring = record['rings'][0]
    a, b = Vector((*ring[11], 0)), Vector((*ring[0], 0))
    origin, axis = (a + b) / 2, (b - a).normalized()
    normal = Vector((axis.y, -axis.x, 0))
    if (origin - Vector((*record['center'], 0))).dot(normal) < 0:
        normal = -normal
    return origin, axis, normal


def material_role(name):
    lower = name.lower()
    if 'recessed_glass' in lower:
        return 'glazing_reflective', (.090, .120, .150), .16, 0
    if lower.endswith('painted_sash_frame'):
        return 'white_sash_paint', (.78, .79, .76), .45, 0
    if lower.endswith('dark_storefront_paint'):
        return 'dark_storefront_paint', (.020, .025, .029), .42, 0
    if lower.endswith('door_timber'):
        return 'dark_door_timber', (.075, .025, .018), .46, 0
    if lower.endswith('brick'):
        return 'orange_red_brick', (.48, .15, .080), .81, 0
    if lower.endswith('red_block_face'):
        return 'orange_red_rustication', (.49, .153, .082), .80, 0
    if lower.endswith('recessed_red_joint'):
        return 'rustication_joint', (.245, .071, .035), .88, 0
    if lower.endswith('portland_stone') or lower in ['ext20_pale', 'ext20_stone'] or lower in ['v16_ksw_finish', 'v17_ksw_finish']:
        return 'neutral_portland_stone', (.69, .675, .635), .73, 0
    return None


def cloned_finish(source, cache):
    if source.name in cache:
        return cache[source.name]
    role = material_role(source.name)
    if not role:
        return source
    kind, color, roughness, metallic = role
    material = source.copy()
    material.name = PREFIX + kind + '_' + source.name
    material.diffuse_color = (*color, 1)
    shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['IOR'].default_value = 1.5
    # These are closed reflective proxies, with no verified room enclosure.
    shader.inputs['Alpha'].default_value = 1
    shader.inputs['Transmission Weight'].default_value = 0
    material['webSurfaceRole'] = 'glazing' if kind == 'glazing_reflective' else 'opaque'
    material['sourceMaterial'] = source.name
    material['photoGuidedFinish'] = True
    for node in material.node_tree.nodes:
        if kind == 'orange_red_brick' and node.type == 'TEX_BRICK':
            node.inputs['Color1'].default_value = (.505, .173, .090, 1)
            node.inputs['Color2'].default_value = (.415, .122, .062, 1)
            node.inputs['Mortar'].default_value = (.30, .265, .22, 1)
        if kind == 'orange_red_rustication' and node.type == 'VALTORGB':
            node.color_ramp.elements[0].color = (.47, .147, .079, 1)
            node.color_ramp.elements[-1].color = (.51, .160, .086, 1)
    cache[source.name] = material
    return material


def connected_parts(mesh):
    neighbours = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbours[a].append(b)
        neighbours[b].append(a)
    seen = set()
    for seed in range(len(mesh.vertices)):
        if seed in seen:
            continue
        pending, part = [seed], []
        seen.add(seed)
        while pending:
            i = pending.pop()
            part.append(i)
            for j in neighbours[i]:
                if j not in seen:
                    pending.append(j)
                    seen.add(j)
        yield part


def add_upper_sash_bars(collection, glass, material):
    origin, axis, normal = registration()
    vertices, faces, windows = [], [], []
    seen = set()
    def local(p):
        return Vector(((p - origin).dot(axis), (p - origin).dot(normal), p.z))
    def world(x, depth, z):
        return origin + axis * x + normal * depth + Vector((0, 0, z))
    for part in connected_parts(glass.data):
        points = [local(glass.matrix_world @ glass.data.vertices[i].co) for i in part]
        lo = Vector(tuple(min(p[a] for p in points) for a in range(3)))
        hi = Vector(tuple(max(p[a] for p in points) for a in range(3)))
        cx = (lo.x + hi.x) / 2
        if not (lo.z > 9 and hi.z < 19.85 and abs(cx) > 1.3 and .9 < hi.x - lo.x < 2.1 and hi.z - lo.z > 2):
            continue
        key = tuple(round(v, 2) for v in [lo.x, hi.x, lo.z, hi.z])
        if key in seen:
            continue
        seen.add(key)
        # Photographs show a central vertical meeting bar on the flanking paired
        # upper sashes. Existing sill/head, horizontal rail and central oriel survive.
        start = len(vertices)
        vertices.extend(world(x, d, z) for z in [lo.z, hi.z] for d in [hi.y + .014, hi.y + .043] for x in [cx - .018, cx + .018])
        faces.extend(tuple(start + i for i in q) for q in [(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)])
        windows.append({'centreX': cx, 'sillZ': lo.z, 'headZ': hi.z, 'barWidth': .036, 'depth': .029})
    assert len(windows) == 12, windows
    mesh = bpy.data.meshes.new(PREFIX + 'paired_upper_sash_meeting_bars')
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    collection.objects.link(obj)
    obj['scope'] = '12 photo-guided paired upper sash centre bars; photographic proportions, not surveyed'
    return obj, windows


def setup_review(scene):
    collection = bpy.data.collections[COLLECTION]
    members = {o.name for o in collection.all_objects}
    for obj in scene.objects:
        if obj.type == 'MESH' and obj.name not in members:
            obj.hide_render = True
        if obj.type == 'LIGHT':
            obj.hide_render = True
    origin, axis, normal = registration()
    world = bpy.data.worlds.new(PREFIX + 'review_world')
    world.use_nodes = True
    background = world.node_tree.nodes['Background']
    background.inputs['Color'].default_value = (.45, .50, .56, 1)
    background.inputs['Strength'].default_value = .45
    scene.world = world
    light = bpy.data.lights.new(PREFIX + 'review_sun', 'SUN')
    light.energy, light.angle = 2.4, math.radians(7)
    sun = bpy.data.objects.new(light.name, light)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (-normal * .65 - axis * .5 + Vector((0,0,-.85))).to_track_quat('-Z','Y').to_euler()
    data = bpy.data.cameras.new(PREFIX + 'review_camera')
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    focus = origin + Vector((0,0,10.2))
    camera.location = focus + normal * 43 + axis * 1.8 + Vector((0,0,1))
    camera.rotation_euler = (focus-camera.location).to_track_quat('-Z','Y').to_euler()
    data.type, data.ortho_scale = 'ORTHO', 24
    scene.camera = camera
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x, scene.render.resolution_y = 840, 1260
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.window.scene = scene
    collection = bpy.data.collections[COLLECTION]
    originals = {o.name: fingerprint(o) for o in bpy.data.objects}
    material_colors = {m.name:list(m.diffuse_color) for m in bpy.data.materials}
    visibility = {o.name:[o.hide_render,o.hide_viewport,o.hide_get()] for o in bpy.data.objects}
    setup_review(scene)
    scene.render.filepath = str(OUT / 'before.png')
    bpy.ops.render.render(write_still=True)
    # Review isolation does not determine which objects should be replaced.
    eligible = [o for o in collection.all_objects if o.type == 'MESH' and not visibility[o.name][0]
                and 'unobserved_envelope' not in o.name and 'unverified_roof' not in o.name]
    cache, owned, replacements = {}, [], []
    for source in eligible:
        if not any(m and material_role(m.name) for m in source.data.materials):
            continue
        copy = source.copy()
        copy.data = source.data.copy()
        copy.name = PREFIX + source.name
        copy.data.name = copy.name
        collection.objects.link(copy)
        for i, material in enumerate(copy.data.materials):
            if material:
                copy.data.materials[i] = cloned_finish(material, cache)
        source.hide_render = True
        source.hide_set(True)
        owned.append(copy)
        replacements.append({'originalObject': source.name, 'replacementObject': copy.name,
                             'reason': 'Photo-guided whole facade finish; mesh, original UV and polygon material indices unchanged'})
    glass = next(o for o in eligible if 'window_glass' in o.name)
    frame = next(m for m in cache.values() if 'white_sash_paint' in m.name)
    bar, windows = add_upper_sash_bars(collection, glass, frame)
    owned.append(bar)
    assert all(fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
    assert all(list(bpy.data.materials[name].diffuse_color) == values for name, values in material_colors.items())
    component = OUT / 'ksw-exterior195-component.blend'
    bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)
    scene.render.filepath = str(OUT / 'after.png')
    bpy.ops.render.render(write_still=True)
    report = {
        'baselinePath':str(BASE.relative_to(ROOT)), 'baselineSha256':BASE_SHA,
        'componentPath':str(component.relative_to(ROOT)),
        'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),
        'targetCollection':COLLECTION, 'addedObjects':[o.name for o in owned],
        'archivedObjects':[r['originalObject'] for r in replacements], 'replacements':replacements,
        'wholeFacadeChanges':['Lighter orange-red upper brick and lower rustication with narrower chromatic variation.',
                              'Neutral pale Portland-stone portal, mouldings, oriel and repeated upper reveals.',
                              'White paired-sash joinery and dark dielectric shopfront paint; eliminate green cast and metallic paint.',
                              'Reflective blue-grey opaque glazing with roughness0.16; retain sealed window proxies.',
                              'Darker stained timber entry, matching the handbook photograph.',
                              '12 missing centre meeting bars across all photographed flanking upper-window rows.'],
        'materialChanges':[{'originalMaterial':original, 'replacementMaterial':m.name,
                            'beforeBaseColor':material_colors[original], 'afterBaseColor':list(m.diffuse_color),
                            'role':m['webSurfaceRole']} for original,m in cache.items()],
        'upperSashRegistration':windows,
        'sources':[{'file':str(p.relative_to(ROOT)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                    'captureDate':'unknown', 'coverage':'Front ground, first-floor rustication and partial upper sash rows; full crown/rear not visible'}
                   for p in [PHOTO,PHOTO_SECOND]],
        'sourceURL':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf',
        'verified':{'originalGeometryUVAndMaterialSlotsUnchanged':True,'originalMaterialsUnchanged':True,
                    'nativeBaselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA,
                    'sameCameraAndLighting':True,'upperSashBarCount':len(windows)},
        'limitations':['Material reflectance and sash-bar dimensions are photographic estimates, not measured.',
                       'Source image capture dates unverified; no current as-built survey claim.',
                       'Opaque reflective glass retained because no full verified room enclosure is available.',
                       'Existing roof, footprint, central curved-oriel geometry, unseen envelope and interiors unchanged.',
                       'Upper paired-window schedule extrapolated from visible flanking rows; complete upper elevation not photographed.'],
        'beforePreview':str((OUT/'before.png').relative_to(ROOT)), 'afterPreview':str((OUT/'after.png').relative_to(ROOT))}
    owned_fingerprints = {obj.name:fingerprint(obj) for obj in owned}
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    with bpy.data.libraries.load(str(component), link=False) as (src, dst):
        assert set(report['addedObjects']).issubset(src.objects)
        dst.objects = list(report['addedObjects'])
    target = bpy.data.collections[COLLECTION]
    for obj in dst.objects:
        target.objects.link(obj)
    assert all(fingerprint(bpy.data.objects[name]) == value for name,value in originals.items())
    assert all(fingerprint(bpy.data.objects[name]) == value for name,value in owned_fingerprints.items())
    assert all([bpy.data.objects[name].hide_render,bpy.data.objects[name].hide_viewport,bpy.data.objects[name].hide_get()] == state for name,state in visibility.items())
    report['verified']['componentReopenedAndAllOwnedGeometryUVMaterialSlotsMatch'] = True
    report['verified']['unrelatedBaselineVisibilityPreservedOnReopen'] = True
    report['ownedFingerprints'] = owned_fingerprints
    (OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('KSW_EXTERIOR195_COMPLETE',len(report['addedObjects']),len(replacements),component,flush=True)


if __name__ == '__main__':
    main()
