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
import re
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from public_interior_objects import public_interior_objects, public_interior_display_group
from web_geometry_budget import budget_web_bevels, restore_web_bevels
from integrate_exterior_round194 import accepted_fingerprints, object_fingerprint
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
AUTHORING = json.loads((ROOT / 'web/tools/building-metadata.json').read_text())
VERSION = int(AUTHORING['sourceVersion'])
MODEL = ROOT / f'result/blender/LSE_campus_detailed_v{VERSION}.blend'
OUTPUT = ROOT / 'web/public/models'
OUTPUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
# Review-only cameras need their owning view layer evaluated before matrix_world.
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
# Do not accept a newly loaded Blender snapshot merely because it is internally
# consistent. Compare it with the independently retained accepted native record
# before changing temporary modifier states or overwriting any browser assets.
expected_geometry = accepted_fingerprints(
    ROOT / f'result/blender/stage{VERSION}', hashlib.sha256(MODEL.read_bytes()).hexdigest())
actual_geometry = {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}
geometry_mismatches = sorted(name for name in set(expected_geometry) | set(actual_geometry)
                             if expected_geometry.get(name) != actual_geometry.get(name))
assert not geometry_mismatches, 'Loaded export source differs from accepted geometry: ' + str(geometry_mismatches[:20])
print('ACCEPTED_SOURCE_GEOMETRY', len(actual_geometry), flush=True)
source_scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.window.scene = source_scene
# Small bevels multiply the triangle count without changing the campus silhouette.
# Keep the archival model intact on disk; the browser uses a lighter derivative.
def source_geometry_name(obj):
    # A physical glazing replacement retains its source geometry policy.
    # Replacement naming must not change bevel/UV detail between views.
    name=obj.get('webGeometrySource', obj.name)
    if name.startswith('OLD_ENTRANCE192_'):
        # Optical-only replacement inherits the accepted door's UV/bevel policy.
        name=obj['originalObject']
    if name.startswith('MAR188_trim_'):
        name=name.removeprefix('MAR188_trim_')
        if not name.startswith('MAR'):name='MAR_'+name
    return name.removeprefix('SAL184_').removeprefix('SAL183_').removeprefix('GLASS181_')


web_bevel_states = budget_web_bevels(source_scene.objects)
modifier_states = []
curve_resolutions = []
full_detail = False
for original in source_scene.objects:
    for modifier in original.modifiers:
        if modifier.type == 'BEVEL' and not source_geometry_name(original).startswith(('5LF_NEXT_', 'PEA_NEXT_', '49L_NEXT_', 'COW_NEXT_', 'PAN_NEXT_', 'STC_NEXT_ENVELOPE_', 'KSW_NEXT_', 'CLM_NEXT_', '61A_NEXT_', 'KGS_NEXT_', 'PAR_NEXT_', 'LAK_NEXT_', 'SHF_NEXT_', '50L_NEXT_', '51L_NEXT_', 'POR_NEXT_', 'LCH_NEXT_', 'STC_NEXT_', 'PEL_NEXT_', 'CKK_NEXT_', 'CON_NEXT_', 'COL_NEXT_', 'SAL_NEXT_', 'OLD_NEXT_', 'SAW_NEXT_', 'MAR_NEXT_', 'LRB_NEXT_', 'CBG_NEXT_', 'OLD_GLAZING_NEXT_')):
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
    principled = None
    if source and source.use_nodes:
        principled = next((n for n in source.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if principled:
            if not principled.inputs['Base Color'].is_linked:
                color = tuple(principled.inputs['Base Color'].default_value)
            roughness = principled.inputs['Roughness'].default_value
            metallic = principled.inputs['Metallic'].default_value
            transmission = principled.inputs['Transmission Weight'].default_value
    # The renderer must read material identity, not a collection's GLAZING prefix.
    # Opaque legacy window proxies keep their optical role and their opacity.
    name = source.name if source else ''
    physical_glazing = transmission > 0.1 or bool(source and source.get('webClosedGlazing'))
    named_glazing = bool(re.search(r'(?:^|_)glass(?:_|\.|$)', name, re.I) or
                         re.search(r'(?:^|_)glazing(?:\.\d+)?$', name, re.I) or
                         re.search(r'(?:^|_)glazing_(?:clear|optical|neutral|reflective|tinted)(?:_|$)', name, re.I) or
                         re.fullmatch(r'MAR168_0[0-3]_0[01]_dielectric', name))
    material['webSurfaceRole'] = 'glazing' if physical_glazing or named_glazing else 'opaque'
    node.inputs['Base Color'].default_value = color[:3] + (1,)
    node.inputs['Roughness'].default_value = max(0.12, roughness)
    node.inputs['Metallic'].default_value = min(1.0, metallic)
    # Only explicitly authored artwork emits light; ordinary finishes remain unchanged.
    if source and source.get('webEmission') and principled:
        node.inputs['Emission Color'].default_value = principled.inputs['Emission Color'].default_value
        node.inputs['Emission Strength'].default_value = principled.inputs['Emission Strength'].default_value
        material['webEmission'] = True
    if transmission > 0.1:
        node.inputs['Alpha'].default_value = float(source.get('webOpacity', 0.30))
        material.surface_render_method = 'DITHERED'
    if source and source.get('webClosedGlazing'):
        material['webClosedGlazing'] = True
    material.diffuse_color = color
    descriptor = surface_descriptor(source)
    if descriptor:
        material['surfaceDetail'] = descriptor
    if source and (source.get('globeMap') or source.get('webBaseColorMap')):
        # Only explicitly authored, packed maps enter the release. Reference
        # photographs elsewhere in the native file are never exported by inference.
        image_node = next(n for n in source.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image)
        texture = material.node_tree.nodes.new('ShaderNodeTexImage')
        texture.image = image_node.image
        texture.interpolation = image_node.interpolation
        tint = tuple(source.get('webBaseColorTint', (1, 1, 1, 1)))
        if tint != (1, 1, 1, 1):
            # A linked socket's default value is ignored. Express the tint with
            # the same multiply node that the glTF exporter recognizes as a factor.
            multiply = material.node_tree.nodes.new('ShaderNodeMixRGB')
            multiply.blend_type = 'MULTIPLY'
            multiply.inputs[0].default_value = 1
            multiply.inputs[2].default_value = tint
            material.node_tree.links.new(texture.outputs['Color'], multiply.inputs[1])
            material.node_tree.links.new(multiply.outputs['Color'], node.inputs['Base Color'])
        else:
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
        if not full_detail and any(tag in source_geometry_name(original) for tag in ['_V16_', '_V17_']) and not source_geometry_name(original).startswith(('35L_', '5LF_NEXT_', 'PEA_NEXT_', '49L_NEXT_', 'COW_NEXT_', 'PAN_NEXT_', 'KSW_NEXT_', 'CLM_NEXT_', '61A_NEXT_', 'KGS_NEXT_', 'PAR_NEXT_', 'LAK_NEXT_', 'SHF_NEXT_', '50L_NEXT_', '51L_NEXT_', 'POR_NEXT_', 'LCH_NEXT_', 'STC_NEXT_', 'PEL_NEXT_', 'CKK_NEXT_', 'CON_NEXT_', 'COL_NEXT_', 'SAL_NEXT_', 'OLD_NEXT_', 'SAW_NEXT_', 'MAR_NEXT_', 'LRB_NEXT_', 'CBG_NEXT_', 'OLD_GLAZING_NEXT_', 'SAL_FRAME_NEXT_')):
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
        needs_uv = full_detail or original.name.startswith('MAR188_') or has_brick or '_NEXT_' in source_geometry_name(original) or any(m and (m.get('globeMap') or m.get('webBaseColorMap')) for m in mesh.materials)
        # Accepted glass may have no native UVs. Without a canonical layer,
        # joining it with detailed trim introduces UV0 only in the close-up.
        # Create the same metric face coordinates in both temporary exports.
        if source_geometry_name(original).startswith(('5LF_NEXT_', '50L_NEXT_', 'PEA_NEXT_', '49L_NEXT_', 'COW_NEXT_', 'PAN_NEXT_', 'STC_NEXT_ENVELOPE_', 'STC_NEXT_ARTWORK_', 'OLD_NEXT_APPROACH_', 'OLD_NEXT_EXTERIOR154_', 'OLD_NEXT_EXTERIOR156_', 'OLD_NEXT_STUDENT_', 'OLD_NEXT_SSC_', 'SITE_NEXT_PORTSMOUTH_', 'KSW_NEXT_', 'MAR_NEXT_', 'CLM_NEXT_', '61A_NEXT_', 'OLD_NEXT_CLARE_sealed_', 'OLD_NEXT_ACCESS_', 'OLD_NEXT_GLAZING', 'LRB_NEXT_', 'CKK_NEXT_', 'SAW_NEXT_', 'CON_NEXT_', 'COL_NEXT_', 'CBG_NEXT_', 'OLD_GLAZING_NEXT_', 'SAL_NEXT_', 'SAL_FRAME_NEXT_')) and not mesh.uv_layers:
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



def clone_public_interior(objects, code, target_scene):
    """Preserve coherent SAW stair nodes; keep all other interiors unchanged."""
    if code != 'SAW':
        return clone_group(objects, code + '_INTERIOR', target_scene)
    groups = {}
    for obj in objects:
        if obj.hide_render:
            continue
        key = public_interior_display_group(code, obj)
        groups.setdefault(key, []).append(obj)
    combined = None
    for key, members in groups.items():
        clone, bounds = clone_group(members, code + '_INTERIOR_' + key, target_scene)
        if clone is None:
            continue
        clone['buildingCode'] = code
        clone['interiorDisplayGroup'] = key
        if combined is None:
            combined = bounds
        else:
            combined = {'min': [min(a, b) for a, b in zip(combined['min'], bounds['min'])],
                        'max': [max(a, b) for a, b in zip(combined['max'], bounds['max'])]}
    assert combined, 'Missing SAW public assembly'
    return True, combined


def exterior_framing_corners(mesh):
    """Bound the evaluated shell in its tightest horizontal rectangle.

    Camera metadata only: mesh geometry and its ordinary world AABB stay intact.
    Eight corners avoid scanning thousands of vertices on each browser selection.
    """
    positions = [vertex.co for vertex in mesh.vertices]
    points = sorted({(float(p.x), float(p.y)) for p in positions})
    def cross(origin, a, b):
        return (a[0]-origin[0])*(b[1]-origin[1])-(a[1]-origin[1])*(b[0]-origin[0])
    lower, upper = [], []
    for point in points:
        while len(lower)>1 and cross(lower[-2],lower[-1],point)<=0:
            lower.pop()
        lower.append(point)
    for point in reversed(points):
        while len(upper)>1 and cross(upper[-2],upper[-1],point)<=0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1]+upper[:-1]
    assert len(hull)>=3, 'Exterior requires a nondegenerate plan'
    best = None
    for first, second in zip(hull,hull[1:]+hull[:1]):
        dx,dy = second[0]-first[0],second[1]-first[1]
        length = (dx*dx+dy*dy)**.5
        ux,uy = dx/length,dy/length
        vx,vy = -uy,ux
        a = [x*ux+y*uy for x,y in hull]
        b = [x*vx+y*vy for x,y in hull]
        bounds = (min(a),max(a),min(b),max(b))
        area = (bounds[1]-bounds[0])*(bounds[3]-bounds[2])
        if best is None or area<best[0]:
            best = (area,ux,uy,vx,vy,bounds)
    _,ux,uy,vx,vy,(amin,amax,bmin,bmax) = best
    zmin,zmax = min(p.z for p in positions),max(p.z for p in positions)
    # Match Blender Z-up to the web's Y-up axes.
    return [[ux*a+vx*b,z,-(uy*a+vy*b)]
            for a in (amin,amax) for z in (zmin,zmax) for b in (bmin,bmax)]


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


def exterior_objects(record):
    """Share the complete authored shell between the first overview and selection.

    Public floors, roofs, stairs and visible furnishings already belong to the
    selected exterior. Include them in the overview too, so transparent facades
    do not change into an empty shell while background detail downloads.
    """
    code = record['code']
    collection = bpy.data.collections.get(code + '_EXTERIOR')
    if collection:
        objects = list(collection.all_objects)
    else:
        root = next(c for c in bpy.data.collections['02_LSE_BUILDINGS'].children if c.name.startswith(code + '_'))
        objects = [obj for child in root.children if 'INTERIOR' not in child.name and 'UNRESOLVED' not in child.name
                   for obj in child.all_objects]
    if record['interior'] and not record.get('interiorStudy'):
        objects += list(bpy.data.collections[record.get('interiorCollection', code + '_PUBLIC_INTERIOR_study')].all_objects)
    return list(dict.fromkeys(objects))


campus_scene = bpy.data.scenes.new('WEB_CAMPUS')
campus_root = bpy.data.collections['02_LSE_BUILDINGS']
metadata = []
for record in records:
    code = record['code']
    exterior = exterior_objects(record)
    obj, bounds = clone_group(exterior, code, campus_scene, hide_basement=code == 'LRB')
    interior = bpy.data.collections.get(record.get('interiorCollection', code + '_PUBLIC_INTERIOR_study'))
    has_interior = bool(interior and any(o.type == 'MESH' for o in interior.all_objects))
    assert has_interior == record['interior'], f'Interior collection missing: {code}'
    metadata.append({key: value for key, value in record.items() if key != 'exportExterior'})
    metadata[-1].update(bounds=bounds, interior=has_interior)
    metadata[-1]['exteriorFramingCorners'] = exterior_framing_corners(obj.data)

for collection_name, name in [('00_SITE', 'SITE'), ('01_CITY_CONTEXT_estimated_heights', 'CONTEXT'), ('03_PUBLIC_REALM', 'LANDSCAPE')]:
    collection = bpy.data.collections.get(collection_name)
    if collection:
        clone_group(collection.all_objects, name, campus_scene)
# Approve only maps actually requested by the temporary campus materials.
# A shared stone map is recorded once even when several facade materials use it.
approved_maps = {}
for source_name in material_cache:
    source = bpy.data.materials.get(source_name)
    if not source or not (source.get('globeMap') or source.get('webBaseColorMap')):
        continue
    node = next(n for n in source.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image)
    assert node.image.packed_file, 'Authored image maps must be packed in the native model'
    data = bytes(node.image.packed_file.data)
    digest = hashlib.sha256(data).hexdigest()
    globe = bool(source.get('globeMap'))
    approved_maps[digest] = {'name': node.image.name, 'sha256': digest, 'bytes': len(data),
        'kind': 'cartography' if globe else 'material-finish',
        'source': 'Natural Earth public-domain cartography' if globe else 'Original generated material finish',
        'scope': ('Authored political map with photo-estimated Australia and India fills; no source photograph'
                  if globe else source.get('finishScope', 'Estimated architectural material finish'))}
assert sum(record['kind'] == 'cartography' for record in approved_maps.values()) == 1
export_scene(campus_scene, 'campus.glb')
# glTF uses file basenames. Match every embedded image to its approved native
# bytes; this also prevents an unrelated archive photograph entering a release.
campus_bytes = (OUTPUT / 'campus.glb').read_bytes()
json_length = struct.unpack_from('<I', campus_bytes, 12)[0]
campus_document = json.loads(campus_bytes[20:20+json_length])
embedded_images = campus_document.get('images', [])
assert len(embedded_images) == len(approved_maps), 'Unexpected or missing campus image map'
generated_textures = []
for image in embedded_images:
    assert 'bufferView' in image and not image.get('uri'), 'Campus maps must be self-contained'
    view = campus_document['bufferViews'][image['bufferView']]
    start = 28 + json_length + view.get('byteOffset', 0)
    digest = hashlib.sha256(campus_bytes[start:start+view['byteLength']]).hexdigest()
    assert digest in approved_maps, 'Export altered an approved native image map'
    record = dict(approved_maps[digest])
    record['nativeImage'] = record['name']
    record['name'] = image['name']
    generated_textures.append(record)
for room in ROOM_SPACES:
    collection = bpy.data.collections[room['collection']]
    if collection.name not in source_scene.collection.children:
        source_scene.collection.children.link(collection)
for record in records:
    if record['interior']:
        collection = bpy.data.collections[record.get('interiorCollection', record['code'] + '_PUBLIC_INTERIOR_study')]
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
    interior_objects = public_interior_objects(record)
    _, bounds = clone_public_interior(interior_objects, code, interior_scene)
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
    if modifier.type == 'BEVEL' and source_geometry_name(modifier.id_data).startswith('SAL_FRAME_NEXT_'):
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
    if code == 'SAW' and kind == 'interior':
        obj, bounds = clone_public_interior(objects, code, scene)
    else:
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
    objects = exterior_objects(record)
    record['detailedExterior'] = export_detail(objects, code, 'exterior')
    if record['interior']:
        objects = public_interior_objects(record)
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
    'version': str(VERSION), 'sourceModelSha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
    'coordinateSystem': 'Local metres; X east, Y up, Z south',
    'origin': [-0.1167, 51.5146], 'buildings': metadata,
    'limitations': 'Photo-informed architectural study. Most dimensions are estimates, not an as-built survey.',
    'footprintAttribution': '© OpenStreetMap contributors, ODbL 1.0',
}
(OUTPUT / 'catalogue.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print('WEB_EXPORT_COMPLETE', flush=True)

# These adjustments belong only to generated assets, never the archival model.
restore_web_bevels(web_bevel_states)
