"""Export the local Blender campus as compact, named web assets.

Run this file in Blender's Text Editor. It reads the model without saving changes.
Blender exports evaluated meshes, so curves and architectural lettering survive.
The overview uses simple PBR colors; on-demand models retain evaluated bevels,
metric UVs and source-derived procedural parameters for browser shading.
"""
from pathlib import Path
import hashlib
import json
import struct
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v17.blend'
OUTPUT = ROOT / 'web/public/models'
OUTPUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
# Review-only cameras need their owning view layer evaluated before matrix_world.
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
source_scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.window.scene = source_scene
# Small bevels multiply the triangle count without changing the campus silhouette.
# Keep the archival model intact on disk; the browser uses a lighter derivative.
modifier_states = []
curve_resolutions = []
full_detail = False
for original in source_scene.objects:
    for modifier in original.modifiers:
        if modifier.type == 'BEVEL':
            modifier_states.append((modifier, modifier.show_viewport, modifier.show_render))
            modifier.show_viewport = False
            modifier.show_render = False
    if original.type in {'FONT', 'CURVE'}:
        curve_resolutions.append((original.data, original.data.resolution_u))
        original.data.resolution_u = min(original.data.resolution_u, 4)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
records = json.loads((ROOT / 'data/buildings.json').read_text())['buildings']
DETAIL_CODES = {'MAR', 'SAW', 'CBG', 'LRB', 'CKK', 'OLD', 'SAL', 'CLM', 'KSW', 'OCS', 'PAN', 'FAW', 'COL', 'CON'}
FACADE_RECORDS = {b['code']: b for b in json.loads((ROOT / 'result/blender/stage05/infill-manifest.json').read_text())['buildings']}
FACADE_RECORDS['5LF'] = json.loads((ROOT / 'result/blender/stage06/attribution.json').read_text())
FACADE_RECORDS['61A'] = json.loads((ROOT / 'result/blender/stage07/aldwych-manifest.json').read_text())
FACADE_RECORDS.update({b['code']: b for b in json.loads((ROOT / 'result/blender/stage08/coopers-manifest.json').read_text())['buildings']})
FACADE_RECORDS.update({b['code']: b for b in json.loads((ROOT / 'result/blender/stage09/heritage/heritage-manifest.json').read_text())['buildings']})
FACADE_RECORDS.update({b['code']: b for b in json.loads((ROOT / 'result/blender/stage10/parish/parish-manifest.json').read_text())['buildings']})
FACADE_RECORDS.update({b['code']: b for b in json.loads((ROOT / 'result/blender/stage11/stc/stc-manifest.json').read_text())['buildings']})
FACADE_RECORDS.update({b['code']: b for b in json.loads((ROOT / 'result/blender/stage12/lincoln/lincoln-manifest.json').read_text())['buildings']})
FACADE_RECORDS.update({b['code']: b for b in json.loads((ROOT / 'result/blender/stage13/lakatos/lakatos-manifest.json').read_text())['buildings']})
FACADE_RECORDS.update({b['code']: b for b in json.loads((ROOT / 'result/blender/stage15/mar/mar-manifest.json').read_text())['buildings']})
FACADE_RECORDS.update({b['code']: b for b in json.loads((ROOT / 'result/blender/stage16/portsmouth/portsmouth-manifest.json').read_text())['buildings']})
FINISH_RECORDS = {b['code']: b for b in json.loads((ROOT / 'result/blender/stage17/all-buildings-manifest.json').read_text())['buildings']}
material_cache = {}


def surface_descriptor(source):
    """Transfer authored procedural parameters, never archive image textures.

    Browser noise approximates the Blender shader; it is not a texture bake.
    UV brick dimensions and color endpoints come directly from the source nodes.
    """
    if not source or not source.use_nodes:
        return None
    nodes = source.node_tree.nodes
    if any(n.type == 'TEX_IMAGE' for n in nodes):
        return None
    texture = next((n for n in nodes if n.type == 'TEX_BRICK'), None)
    if not texture:
        texture = next((n for n in nodes if n.type == 'TEX_NOISE'), None)
    if not texture:
        return None
    bump = next((n for n in nodes if n.type == 'BUMP'), None)
    result = {
        'kind': 'brick' if texture.type == 'TEX_BRICK' else 'noise',
        'scale': float(texture.inputs['Scale'].default_value),
        'bump': float(bump.inputs['Distance'].default_value * bump.inputs['Strength'].default_value) if bump else 0,
        'approximation': 'Source-derived browser procedural shader, not a Blender bake',
    }
    if texture.type == 'TEX_BRICK':
        for key, socket in [('colorA', 'Color1'), ('colorB', 'Color2'), ('mortarColor', 'Mortar')]:
            result[key] = list(texture.inputs[socket].default_value)[:3]
        result['brickWidth'] = float(texture.inputs['Brick Width'].default_value)
        result['rowHeight'] = float(texture.inputs['Row Height'].default_value)
        result['mortarSize'] = float(texture.inputs['Mortar Size'].default_value)
    else:
        ramp = next((n for n in nodes if n.type == 'VALTORGB'), None)
        principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if ramp and principled and principled.inputs['Base Color'].is_linked:
            result['colorA'] = list(ramp.color_ramp.elements[0].color)[:3]
            result['colorB'] = list(ramp.color_ramp.elements[-1].color)[:3]
    return result


def web_material(source):
    """Use bounded PBR properties; avoid expensive screen-space transmission."""
    key = ('DETAIL_' if full_detail else '') + (source.name if source else 'unassigned')
    if key in material_cache:
        return material_cache[key]
    material = bpy.data.materials.new('WEB_' + key)
    material.use_nodes = True
    node = material.node_tree.nodes.get('Principled BSDF')
    color = tuple(source.diffuse_color) if source else (0.6, 0.6, 0.6, 1)
    roughness, metallic, transmission = 0.7, 0.0, 0.0
    if source and source.use_nodes:
        principled = next((n for n in source.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if principled:
            if not principled.inputs['Base Color'].is_linked:
                color = tuple(principled.inputs['Base Color'].default_value)
            roughness = principled.inputs['Roughness'].default_value
            metallic = principled.inputs['Metallic'].default_value
            transmission = principled.inputs['Transmission Weight'].default_value
    node.inputs['Base Color'].default_value = color[:3] + (1,)
    node.inputs['Roughness'].default_value = max(0.12 if full_detail else 0.35, roughness)
    node.inputs['Metallic'].default_value = min(1.0 if full_detail else 0.35, metallic)
    if transmission > 0.1:
        node.inputs['Alpha'].default_value = 0.30
        material.surface_render_method = 'DITHERED'
    material.diffuse_color = color
    if full_detail:
        descriptor = surface_descriptor(source)
        if descriptor:
            material['surfaceDetail'] = descriptor
    material_cache[key] = material
    return material


def clone_group(objects, name, target_scene):
    """Merge each semantic building into one object with its material primitives."""
    copies = []
    points = []
    for original in objects:
        # Sub-centimetre finish belongs to on-demand views, not the initial campus download.
        if not full_detail and any(tag in original.name for tag in ['_V16_', '_V17_']) and not original.name.startswith('35L_'):
            continue
        if original.type not in {'MESH', 'CURVE', 'FONT', 'SURFACE'} or original.hide_render:
            continue
        evaluated = original.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        if not mesh or not mesh.vertices:
            continue
        # Joining differently named UV layers would put some facades in UV1 while
        # the browser samples UV0. Normalize only these temporary export meshes.
        if full_detail and mesh.uv_layers:
            active = next((layer for layer in mesh.uv_layers if layer.active_render), mesh.uv_layers.active)
            for layer in list(mesh.uv_layers):
                if layer != active:
                    mesh.uv_layers.remove(layer)
            active.name = 'SurfaceUV'
            active.active_render = True
        mesh.transform(original.matrix_world)
        points.extend(v.co.copy() for v in mesh.vertices)
        # Keep explicit primitive material indices but never ship archived photographs.
        materials = [web_material(m) for m in mesh.materials]
        mesh.materials.clear()
        for material in materials or [web_material(None)]:
            mesh.materials.append(material)
        clone = bpy.data.objects.new(name + '_part', mesh)
        target_scene.collection.objects.link(clone)
        copies.append(clone)
    if not copies:
        return None, None
    bpy.context.window.scene = target_scene
    bpy.ops.object.select_all(action='DESELECT')
    for clone in copies:
        clone.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name
    joined['buildingCode'] = name
    bounds = [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]]
    # glTF exports Blender Z-up as Y-up: x,y,z -> x,z,-y.
    lo, hi = bounds
    return joined, {'min': [lo[0], lo[2], -hi[1]], 'max': [hi[0], hi[2], -lo[1]]}


def export_scene(scene, filename):
    bpy.context.window.scene = scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath=str(OUTPUT / filename), export_format='GLB', use_selection=True, use_active_scene=True,
        export_cameras=False, export_lights=False, export_extras=True,
        export_animations=False, export_texcoords=full_detail, export_normals=True,
        export_materials='EXPORT', export_yup=True,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=6,
        export_draco_position_quantization=20,
    )
    print('EXPORTED', filename, (OUTPUT / filename).stat().st_size, flush=True)


campus_scene = bpy.data.scenes.new('WEB_CAMPUS')
campus_root = bpy.data.collections['02_LSE_BUILDINGS']
metadata = []
for record in records:
    code = record['code']
    root_collection = next(c for c in campus_root.children if c.name.startswith(code + '_'))
    exterior = [o for c in root_collection.children if 'INTERIOR' not in c.name and 'UNRESOLVED' not in c.name for o in c.all_objects]
    obj, bounds = clone_group(exterior, code, campus_scene)
    state = 'detailed' if code in DETAIL_CODES else 'facade' if code in FACADE_RECORDS else 'massing'
    if code == '61A':
        state = 'provisional'
    elif code == '35L':
        state = 'construction'
    interior = bpy.data.collections.get(code + '_PUBLIC_INTERIOR_study')
    has_interior = bool(interior and any(o.type == 'MESH' for o in interior.all_objects))
    metadata.append({'code': code, 'name': record['name'], 'address': record['address'], 'status': state, 'bounds': bounds, 'interior': has_interior})

# Street-facing orientation from the reviewed Blender cameras; preserve an elevated
# orbit angle so roofs and the selected facade remain visible together.
exterior_cameras = {
    'MAR': '02_MAR_Lincolns_Inn_Fields', 'SAW': 'SAW_folded_facade_detail',
    'CBG': 'CBG_QA_01_facade', 'OLD': 'OLD_DETAIL_Houghton_entry',
    'SAL': 'SAL_DETAIL_north_facade', 'CLM': 'CLM_D3_front_camera',
    'KSW': 'KSW_D3_front_camera', 'OCS': 'OCS_D3_front_street_camera',
    'COL': 'COL_D4_facade', 'CON': 'CON_D4_facade',
    'PAN': 'PAN_FAW_D3_frontage', 'FAW': 'PAN_FAW_D3_frontage',
}
for record in metadata:
    if record['code'] in exterior_cameras:
        camera = bpy.data.objects[exterior_cameras[record['code']]]
        outward = camera.matrix_world.to_quaternion() @ Vector((0, 0, 1))
        direction = Vector((outward.x, max(0.55, outward.z), -outward.y)).normalized()
        record['exteriorDirection'] = list(direction)

for record in metadata:
    if record['code'] in FACADE_RECORDS:
        study = FACADE_RECORDS[record['code']]
        record['exteriorDirection'] = list(Vector(study['exteriorDirection']).normalized())
        record['facadeScope'] = study['scope']
        if 'detailView' in study:
            view = study['detailView']
            record['detailView'] = {**view, **{key: [view[key][0], view[key][2], -view[key][1]] for key in ['position', 'target']}}
        if 'sourceDrawing' in study:
            record['footprintSource'] = {'drawing': study['sourceDrawing'], 'sourcePage': study['sourcePage'], 'registration': 'Approximate registration to five OCS outline corners; not surveyed coordinates'}
        if 'sourcePoint' in study:
            record['footprintSource'] = {key: study[key] for key in ['osmId', 'sourcePoint', 'sourcePage', 'sourceMap']}

for record in metadata:
    finish = FINISH_RECORDS[record['code']]
    record['localRefinement'] = {key: finish[key] for key in ['description', 'newComponents', 'scope']}

# Entrance presets use the reviewed cameras and their street plane as orbit targets.
# Intersect the optical axis with the facade instead of orbiting around a guessed depth.
site_records = {b['code']: b for b in json.loads((ROOT / 'result/blender/site_geometry.json').read_text())['buildings'] if b['code']}
for record in metadata:
    code = record['code']
    if code not in {'COL', 'CON'}:
        continue
    camera = bpy.data.objects[code + '_D4_entrance']
    ring = site_records[code]['rings'][0]
    edge = 10 if code == 'COL' else 4
    p, q = Vector((*ring[edge], 0)), Vector((*ring[edge + 1], 0))
    normal = Vector((q.y - p.y, p.x - q.x, 0)).normalized()
    position = camera.matrix_world.translation
    direction = camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))
    distance = (p - position).dot(normal) / direction.dot(normal)
    assert 0 < distance < 30, f'Invalid entrance camera for {code}'
    target = position + direction * distance
    record['detailView'] = {
        'label': '入口细节',
        'position': [position.x, position.z, -position.y],
        'target': [target.x, target.z, -target.y],
        'fov': 46,
    }

for collection_name, name in [('00_SITE', 'SITE'), ('01_CITY_CONTEXT_estimated_heights', 'CONTEXT'), ('03_PUBLIC_REALM', 'LANDSCAPE')]:
    collection = bpy.data.collections.get(collection_name)
    if collection:
        clone_group(collection.all_objects, name, campus_scene)
export_scene(campus_scene, 'campus.glb')

for record in metadata:
    if not record['interior']:
        continue
    code = record['code']
    interior_scene = bpy.data.scenes.new('WEB_INTERIOR_' + code)
    collection = bpy.data.collections[code + '_PUBLIC_INTERIOR_study']
    interior_objects = list(collection.all_objects)
    if code == 'MAR':
        interior_objects = [o for o in interior_objects if '_floor_way/' not in o.name or max((o.matrix_world @ Vector(c)).z for c in o.bound_box) <= 13]
        interior_objects += [o for o in bpy.data.collections['MAR_EXTERIOR'].all_objects if 'ground_glass_panes' in o.name]
    if code == 'SAW':
        interior_objects = [o for o in interior_objects if '_floor_' not in o.name]
    if code == 'LRB':
        interior_objects += [o for o in bpy.data.collections['LRB_EXTERIOR'].all_objects if 'roof_' in o.name]
    _, bounds = clone_group(interior_objects, code + '_INTERIOR', interior_scene)
    assert bounds, f'No public-interior geometry exported for {code}'
    camera_names = {'MAR': 'MAR_D3_hall', 'LRB': 'ATRIA_LRB_spiral_and_lifts', 'CKK': 'ATRIA_CKK_timber_landscape', 'CBG': 'CBG_QA_03_academic_stair'}
    if code in camera_names:
        camera = bpy.data.objects[camera_names[code]]
        position = camera.matrix_world.translation
        direction = camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))
        target = position + direction * 20
        record['interiorView'] = {
            'position': [position.x, position.z, -position.y],
            'target': [target.x, target.z, -target.y],
            'fov': 65,
        }
    record['interiorBounds'] = bounds
    export_scene(interior_scene, code.lower() + '-interior.glb')

# Restore the native evaluated geometry for individual building downloads.
# The campus overview stays light; high-detail files are loaded only on selection.
full_detail = True
for modifier, viewport, render in modifier_states:
    modifier.show_viewport, modifier.show_render = viewport, render
for curve, resolution in curve_resolutions:
    curve.resolution_u = resolution
bpy.context.window.scene = source_scene
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
(OUTPUT / 'details').mkdir(exist_ok=True)
detail_report = []


def export_detail(objects, code, kind):
    scene = bpy.data.scenes.new('WEB_DETAIL_' + code + '_' + kind)
    obj, bounds = clone_group(objects, code, scene)
    assert obj and bounds
    staging = f'details/{code.lower()}-{kind}.glb'
    export_scene(scene, staging)
    data = (OUTPUT / staging).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    filename = f'details/{code.lower()}-{kind}-{digest[:12]}.glb'
    (OUTPUT / staging).replace(OUTPUT / filename)
    size = struct.unpack_from('<I', data, 12)[0]
    document = json.loads(data[20:20+size])
    triangles = sum(document['accessors'][p['indices']]['count'] // 3
                    for mesh in document['meshes'] for p in mesh['primitives'])
    descriptor = {'url': '/models/' + filename, 'bytes': len(data), 'triangles': triangles,
                  'sha256': digest, 'bounds': bounds}
    assert len(data) < 25 * 1024 * 1024, f'Detail asset too large: {code}'
    detail_report.append({'code': code, 'kind': kind, **descriptor})
    for item in list(scene.objects):
        bpy.data.objects.remove(item, do_unlink=True)
    bpy.data.scenes.remove(scene)
    bpy.data.batch_remove(ids=[mesh for mesh in bpy.data.meshes if mesh.users == 0])
    return descriptor


for record in metadata:
    code = record['code']
    if code not in DETAIL_CODES and code not in FACADE_RECORDS:
        continue
    objects = list(bpy.data.collections[code + '_EXTERIOR'].all_objects)
    if record['interior']:
        # Floor plates, roof slabs and public stairs complete the visible shell.
        # The separate interior view below retains its deliberate cutaway scope.
        objects += list(bpy.data.collections[code + '_PUBLIC_INTERIOR_study'].all_objects)
    objects = list(dict.fromkeys(objects))
    record['detailedExterior'] = export_detail(objects, code, 'exterior')
    if record['interior']:
        objects = list(bpy.data.collections[code + '_PUBLIC_INTERIOR_study'].all_objects)
        if code == 'MAR':
            objects = [o for o in objects if '_floor_way/' not in o.name or max((o.matrix_world @ Vector(c)).z for c in o.bound_box) <= 13]
            objects += [o for o in bpy.data.collections['MAR_EXTERIOR'].all_objects if 'ground_glass_panes' in o.name]
        elif code == 'SAW':
            objects = [o for o in objects if '_floor_' not in o.name]
        elif code == 'LRB':
            objects += [o for o in bpy.data.collections['LRB_EXTERIOR'].all_objects if 'roof_' in o.name]
        record['detailedInterior'] = export_detail(objects, code, 'interior')

report_path = ROOT / 'result/web/all-buildings/export-manifest.json'
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(detail_report, indent=2) + '\n')

payload = {
    'version': '17', 'sourceModelSha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
    'coordinateSystem': 'Local metres; X east, Y up, Z south',
    'origin': [-0.1167, 51.5146], 'buildings': metadata,
    'limitations': 'Photo-informed architectural study. Most dimensions are estimates, not an as-built survey.',
    'footprintAttribution': '© OpenStreetMap contributors, ODbL 1.0',
}
(OUTPUT / 'catalogue.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print('WEB_EXPORT_COMPLETE', flush=True)
