"""Export the local Blender campus as compact, named web assets.

Run this file in Blender's Text Editor. It reads the model without saving changes.
Blender exports evaluated meshes, so curves and architectural lettering survive.
The overview and on-demand models share PBR finishes and surface descriptors.
On-demand models retain evaluated bevels,
metric UVs and source-derived procedural parameters for browser shading.
"""
from pathlib import Path
import hashlib
import json
import struct
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v133.blend'
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
        if modifier.type == 'BEVEL' and not original.name.startswith(('KGS_NEXT_', 'PAR_NEXT_', 'LAK_NEXT_', 'SHF_NEXT_', '50L_NEXT_', '51L_NEXT_', 'POR_NEXT_', 'LCH_NEXT_', 'STC_NEXT_', 'PEL_NEXT_', 'CKK_NEXT_', 'CON_NEXT_', 'COL_NEXT_', 'SAL_NEXT_', 'OLD_NEXT_', 'SAW_NEXT_', 'MAR_NEXT_', 'LRB_NEXT_', 'CBG_NEXT_', 'OLD_GLAZING_NEXT_')):
            modifier_states.append((modifier, modifier.show_viewport, modifier.show_render))
            modifier.show_viewport = False
            modifier.show_render = False
    if original.type in {'FONT', 'CURVE'}:
        curve_resolutions.append((original.data, original.data.resolution_u))
        original.data.resolution_u = min(original.data.resolution_u, 4)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
# Camera presets and evidence are authored inputs, separate from generated assets.
# A single snapshot replaces the old chain of historical stage manifests.
AUTHORING = json.loads((ROOT / 'web/tools/building-metadata.json').read_text())
records = AUTHORING['buildings']
ROOM_SPACES = AUTHORING['spaces']
assert len(records) == 31 and len({r['code'] for r in records}) == 31
assert len(ROOM_SPACES) == len({room['id'] for room in ROOM_SPACES}), 'Duplicate room identity'
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
    node.inputs['Roughness'].default_value = max(0.12, roughness)
    node.inputs['Metallic'].default_value = min(1.0, metallic)
    if transmission > 0.1:
        node.inputs['Alpha'].default_value = float(source.get('webOpacity', 0.30))
        material.surface_render_method = 'DITHERED'
    material.diffuse_color = color
    descriptor = surface_descriptor(source)
    if descriptor:
        material['surfaceDetail'] = descriptor
    if source and source.get('globeMap'):
        image_node = next(n for n in source.node_tree.nodes if n.type == 'TEX_IMAGE')
        texture = material.node_tree.nodes.new('ShaderNodeTexImage')
        texture.image = image_node.image
        node.inputs['Base Color'].default_value = (1, 1, 1, 1)
        material.node_tree.links.new(texture.outputs['Color'], node.inputs['Base Color'])
    material_cache[key] = material
    return material


def clip_below_ground(mesh):
    """Trim temporary world-space meshes; retain native underground geometry."""
    if not any(vertex.co.z < -1e-6 for vertex in mesh.vertices):
        return
    editable = bmesh.new()
    editable.from_mesh(mesh)
    bmesh.ops.bisect_plane(
        editable, geom=list(editable.verts) + list(editable.edges) + list(editable.faces),
        dist=1e-6, plane_co=(0, 0, 0), plane_no=(0, 0, 1),
        clear_inner=True, clear_outer=False,
    )
    editable.to_mesh(mesh)
    editable.free()
    mesh.update()
    assert all(vertex.co.z >= -1e-5 for vertex in mesh.vertices)


def clone_group(objects, name, target_scene, hide_basement=False):
    """Merge each semantic building into one object with its material primitives."""
    copies = []
    points = []
    for original in objects:
        # Sub-centimetre finish belongs to on-demand views, not the initial campus download.
        if not full_detail and any(tag in original.name for tag in ['_V16_', '_V17_']) and not original.name.startswith(('35L_', 'KGS_NEXT_', 'PAR_NEXT_', 'LAK_NEXT_', 'SHF_NEXT_', '50L_NEXT_', '51L_NEXT_', 'POR_NEXT_', 'LCH_NEXT_', 'STC_NEXT_', 'PEL_NEXT_', 'CKK_NEXT_', 'CON_NEXT_', 'COL_NEXT_', 'SAL_NEXT_', 'OLD_NEXT_', 'SAW_NEXT_', 'MAR_NEXT_', 'LRB_NEXT_', 'CBG_NEXT_', 'OLD_GLAZING_NEXT_', 'SAL_FRAME_NEXT_')):
            continue
        if original.type not in {'MESH', 'CURVE', 'FONT', 'SURFACE'} or original.hide_render:
            continue
        evaluated = original.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        if not mesh or not mesh.vertices:
            continue
        # A missing UV layer silently turns procedural brick into solid mortar
        # after meshes are joined. Reject that source error before publishing.
        is_exterior = any(collection.name.endswith('_EXTERIOR') for collection in original.users_collection)
        has_brick = any((surface_descriptor(material) or {}).get('kind') == 'brick' for material in mesh.materials)
        if is_exterior and has_brick and not mesh.uv_layers:
            raise ValueError(f"Exterior brick requires metric UVs: {original.name}")
        # Joining differently named UV layers would put some facades in UV1 while
        # the browser samples UV0. Normalize only these temporary export meshes.
        # Accepted components retain their metric UVs at both viewing scales.
        needs_uv = full_detail or has_brick or '_NEXT_' in original.name or any(m and m.get('globeMap') for m in mesh.materials)
        # Accepted glass may have no native UVs. Without a canonical layer,
        # joining it with detailed trim introduces UV0 only in the close-up.
        # Create the same metric face coordinates in both temporary exports.
        if original.name.startswith(('CON_NEXT_', 'COL_NEXT_', 'CBG_NEXT_', 'OLD_GLAZING_NEXT_', 'SAL_NEXT_', 'SAL_FRAME_NEXT_')) and not mesh.uv_layers:
            layer = mesh.uv_layers.new(name='SurfaceUV')
            for face in mesh.polygons:
                vertices = [original.matrix_world @ mesh.vertices[index].co for index in face.vertices]
                origin = vertices[0]
                horizontal = (vertices[1] - origin).normalized()
                normal = (vertices[1] - origin).cross(vertices[-1] - origin).normalized()
                vertical = normal.cross(horizontal)
                for index, point in zip(face.loop_indices, vertices):
                    layer.data[index].uv = ((point - origin).dot(horizontal), (point - origin).dot(vertical))
        if not needs_uv:
            for layer in list(mesh.uv_layers):
                mesh.uv_layers.remove(layer)
        if needs_uv and mesh.uv_layers:
            active = next((layer for layer in mesh.uv_layers if layer.active_render), mesh.uv_layers.active)
            for layer in list(mesh.uv_layers):
                if layer != active:
                    mesh.uv_layers.remove(layer)
            active.name = 'SurfaceUV'
            active.active_render = True
        mesh.transform(original.matrix_world)
        if hide_basement and any(c.name == 'LRB_PUBLIC_INTERIOR_study' for c in original.users_collection):
            clip_below_ground(mesh)
            if not mesh.polygons:
                bpy.data.meshes.remove(mesh)
                continue
        points.extend(v.co.copy() for v in mesh.vertices)
        # Keep explicit primitive material indices but never ship archived photographs.
        materials = [web_material(m) for m in mesh.materials]
        # Clearing slots resets polygon indices in Blender. Preserve two-tone
        # assemblies instead of silently painting every face with the first slot.
        material_indices = [polygon.material_index for polygon in mesh.polygons]
        mesh.materials.clear()
        for material in materials or [web_material(None)]:
            mesh.materials.append(material)
        for polygon, material_index in zip(mesh.polygons, material_indices):
            polygon.material_index = material_index
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
        export_animations=False, export_texcoords=full_detail or filename == 'campus.glb', export_normals=True,
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
    interior = bpy.data.collections.get(code + '_PUBLIC_INTERIOR_study')
    has_interior = bool(interior and any(o.type == 'MESH' for o in interior.all_objects))
    assert has_interior == record['interior'], f'Interior collection missing: {code}'
    metadata.append({key: value for key, value in record.items() if key != 'exportExterior'})
    metadata[-1].update(bounds=bounds, interior=has_interior)

for collection_name, name in [('00_SITE', 'SITE'), ('01_CITY_CONTEXT_estimated_heights', 'CONTEXT'), ('03_PUBLIC_REALM', 'LANDSCAPE')]:
    collection = bpy.data.collections.get(collection_name)
    if collection:
        clone_group(collection.all_objects, name, campus_scene)
generated_textures = []
for material in bpy.data.materials:
    if not material.get('globeMap'):
        continue
    if not any(not obj.hide_render and obj.type == 'MESH' and material.name in obj.data.materials
               for obj in bpy.data.collections['00_SITE'].all_objects):
        continue
    node = next(n for n in material.node_tree.nodes if n.type == 'TEX_IMAGE')
    assert node.image.packed_file, 'Globe cartography must be packed in the native model'
    generated_textures.append({'name': node.image.name,
        'sha256': hashlib.sha256(bytes(node.image.packed_file.data)).hexdigest(),
        'source': 'Natural Earth public-domain cartography',
        'scope': 'Authored political map with photo-estimated Australia fill; no source photograph'})
assert len(generated_textures) == 1, 'Expected one visible authored globe map'
export_scene(campus_scene, 'campus.glb')
# glTF names an image by its file basename, which can differ from Blender's ID.
# Match the embedded bytes to the approved packed map before recording that name.
campus_bytes = (OUTPUT / 'campus.glb').read_bytes()
json_length = struct.unpack_from('<I', campus_bytes, 12)[0]
campus_document = json.loads(campus_bytes[20:20+json_length])
embedded_images = campus_document.get('images', [])
assert len(embedded_images) == len(generated_textures) == 1
image = embedded_images[0]
assert 'bufferView' in image and not image.get('uri')
view = campus_document['bufferViews'][image['bufferView']]
start = 28 + json_length + view.get('byteOffset', 0)
image_sha256 = hashlib.sha256(campus_bytes[start:start+view['byteLength']]).hexdigest()
assert image_sha256 == generated_textures[0]['sha256'], 'Export changed authored globe map'
generated_textures[0]['nativeImage'] = generated_textures[0]['name']
generated_textures[0]['name'] = image['name']
for room in ROOM_SPACES:
    collection = bpy.data.collections[room['collection']]
    if collection.name not in source_scene.collection.children:
        source_scene.collection.children.link(collection)
for record in records:
    if record['interior']:
        collection = bpy.data.collections[record['code'] + '_PUBLIC_INTERIOR_study']
        if collection.name not in source_scene.collection.children:
            source_scene.collection.children.link(collection)
bpy.context.window.scene = source_scene
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()

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
        interior_objects += [o for o in bpy.data.collections['LRB_EXTERIOR'].all_objects if 'roof_' in o.name or o.get('sharedInteriorRoof')]
    _, bounds = clone_group(interior_objects, code + '_INTERIOR', interior_scene)
    assert bounds, f'No public-interior geometry exported for {code}'
    # Preserve approved presets; rooms without one use the viewer's bounds fit.
    record['interiorBounds'] = bounds
    export_scene(interior_scene, code.lower() + '-interior.glb')

# Restore the native evaluated geometry for individual building downloads.
# The campus overview stays light; high-detail files are loaded only on selection.
full_detail = True
for modifier, viewport, render in modifier_states:
    # Colour-only SAL sash replacements keep the lightweight frame geometry
    # at both scales. Restoring bevels here would multiply detail vertices ninefold.
    if modifier.type == 'BEVEL' and modifier.id_data.name.startswith('SAL_FRAME_NEXT_'):
        continue
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
    obj, bounds = clone_group(objects, code, scene, hide_basement=code == 'LRB' and kind == 'exterior')
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
    if not next(r['exportExterior'] for r in records if r['code'] == code):
        continue
    objects = list(bpy.data.collections[code + '_EXTERIOR'].all_objects)
    if record['interior'] and not record.get('interiorStudy'):
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
            objects += [o for o in bpy.data.collections['LRB_EXTERIOR'].all_objects if 'roof_' in o.name or o.get('sharedInteriorRoof')]
        record['detailedInterior'] = export_detail(objects, code, 'interior')

# Additional rooms retain their own identity instead of replacing the building's hall.
for room in ROOM_SPACES:
    record = next(item for item in metadata if item['code'] == room['code'])
    descriptor = export_detail(list(bpy.data.collections[room['collection']].all_objects), room['id'], 'interior')
    record.setdefault('interiorSpaces', []).append({
        key: room[key] for key in ['id', 'label', 'scope', 'interiorStudy', 'interiorView', 'gallery']
    } | {'interiorAsset': descriptor['url'], 'detailedInterior': descriptor,
         'interiorBounds': descriptor['bounds']})


report_path = ROOT / 'result/web/all-buildings/export-manifest.json'
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(detail_report, indent=2) + '\n')

payload = {
    'generatedTextures': generated_textures,
    'version': '133', 'sourceModelSha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
    'coordinateSystem': 'Local metres; X east, Y up, Z south',
    'origin': [-0.1167, 51.5146], 'buildings': metadata,
    'limitations': 'Photo-informed architectural study. Most dimensions are estimates, not an as-built survey.',
    'footprintAttribution': '© OpenStreetMap contributors, ODbL 1.0',
}
(OUTPUT / 'catalogue.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print('WEB_EXPORT_COMPLETE', flush=True)
