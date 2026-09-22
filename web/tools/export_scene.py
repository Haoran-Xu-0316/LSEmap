"""Export the local Blender campus as compact, named web assets.

Run this file in Blender's Text Editor. It reads the model without saving changes.
Blender exports evaluated meshes, so curves and architectural lettering survive.
Procedural materials become simple PBR colors; original renders retain finer finishes.
"""
from pathlib import Path
import hashlib
import json
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v04.blend'
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
for original in source_scene.objects:
    for modifier in original.modifiers:
        if modifier.type == 'BEVEL':
            modifier.show_viewport = False
            modifier.show_render = False
    if original.type in {'FONT', 'CURVE'}:
        original.data.resolution_u = min(original.data.resolution_u, 4)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
records = json.loads((ROOT / 'data/buildings.json').read_text())['buildings']
DETAIL_CODES = {'MAR', 'SAW', 'CBG', 'LRB', 'CKK', 'OLD', 'SAL', 'CLM', 'KSW', 'OCS', 'PAN', 'FAW', 'COL', 'CON'}
material_cache = {}


def web_material(source):
    """Use bounded PBR properties; avoid expensive screen-space transmission."""
    key = source.name if source else 'unassigned'
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
    node.inputs['Roughness'].default_value = max(0.35, roughness)
    node.inputs['Metallic'].default_value = min(0.35, metallic)
    if transmission > 0.1:
        node.inputs['Alpha'].default_value = 0.30
        material.surface_render_method = 'DITHERED'
    material.diffuse_color = color
    material_cache[key] = material
    return material


def clone_group(objects, name, target_scene):
    """Merge each semantic building into one object with its material primitives."""
    copies = []
    points = []
    for original in objects:
        if original.type not in {'MESH', 'CURVE', 'FONT', 'SURFACE'} or original.hide_render:
            continue
        evaluated = original.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        if not mesh or not mesh.vertices:
            continue
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
        export_animations=False, export_texcoords=False, export_normals=True,
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
    state = 'detailed' if code in DETAIL_CODES else 'massing'
    if code in {'5LF', '49L'}:
        state = 'unlocated'
    elif code == '61A':
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

payload = {
    'version': '04', 'sourceModelSha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
    'coordinateSystem': 'Local metres; X east, Y up, Z south',
    'origin': [-0.1167, 51.5146], 'buildings': metadata,
    'limitations': 'Photo-informed architectural study. Most dimensions are estimates, not an as-built survey.',
    'footprintAttribution': '© OpenStreetMap contributors, ODbL 1.0',
}
(OUTPUT / 'catalogue.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print('WEB_EXPORT_COMPLETE', flush=True)
