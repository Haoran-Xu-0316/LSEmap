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
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v73.blend'
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
ROOM_RECORDS = {r['code']: r for r in json.loads((ROOT / 'result/blender/stage73/room-studies.json').read_text())['buildings']}
REVIEW_RECORDS = {r['code']: r for r in json.loads((ROOT / 'result/blender/stage73/building-review.json').read_text())['buildings']}
FACADE_RECORDS['SHF'] = json.loads((ROOT / 'result/blender/stage50/shf-manifest.json').read_text())
FACADE_RECORDS['POR'] = json.loads((ROOT / 'result/blender/stage51/por-manifest.json').read_text())
FINISH_RECORDS['POR'] = {'description': 'Neutral pale joinery, horizontal mixed-brick courses and two photographed chimney stacks', 'newComponents': FACADE_RECORDS['POR']['components'], 'scope': FACADE_RECORDS['POR']['scope']}
FINISH_RECORDS['SHF'] = {'description': 'Four-bay stock-brick facade, pale base, white joinery and four roof dormers', 'newComponents': FACADE_RECORDS['SHF']['components'], 'scope': FACADE_RECORDS['SHF']['scope']}
old_houghton = json.loads((ROOT / 'result/blender/stage52/old-houghton-audit.json').read_text())
fifty_portal = json.loads((ROOT / 'result/blender/stage72/fifty-lincoln-portal-audit.json').read_text())
FINISH_RECORDS['50L'] = {'description': 'Broad panelled sandstone portal, dark unbarred semicircular fanlight, six timber panels, distinct door knobs, letterbox and two low metal-nosed steps', 'newComponents': len(fifty_portal['addedObjects']), 'scope': 'No.50 entrance guided by the LSE 2025/26 property handbook photograph. Neighboring round windows excluded; dimensions and carved profiles estimated, capture date unknown. Upper elevations, roof and complete interior still require review.'}
FINISH_RECORDS['SAL'] = {'description': 'Four-storey main window body, blue painted sashes and eighteen glazed oblique oriel side panes', 'newComponents': 3, 'scope': 'September 2023 front photography and architect project photos guide floor count, sash colour and projecting bays. Absolute heights, bay dimensions, roof arrangement, rear elevations, carving and complete interior remain unverified.'}
FINISH_RECORDS['CLM'] = {'description': 'Five dark curved-cap dormers, four stone chimney stacks, shallow setback attic glazing and continuous iron railing; stone capital scrolls retained', 'newComponents': 12, 'scope': 'Front roof silhouette guided by dated 2018 and November 2023 photographs. Attic proportions, heights and chimney positions estimated; rear roof plan, recent plant installation and complete interior remain unverified.'}
FINISH_RECORDS['CON'] = {'description': 'Open street portal with warm recessed vestibule, inner glazed doors and split granite-limestone casing', 'newComponents': 8, 'scope': 'Entrance guided by an undated LSE estate photograph; hallway depth, heights, materials and lighting estimated. Crest remains a simplified reserve. Upper elevations, roof and complete interior remain unresolved.'}
FINISH_RECORDS['COL'] = {'description': 'Dark brown paired door leaves with four upper rectangular panels, two lower oval mouldings and an inset stone name tablet', 'newComponents': 5, 'scope': 'Entrance joinery guided by the 2025/26 LSE property handbook photograph. Exact capture date, dimensions and ornamental profiles unverified; upper elevations, roof, unseen sides and complete interior remain unresolved.'}
FINISH_RECORDS['PAR'] = {'description': 'Pointed blind window heads, hierarchical four-column sashes, twin roof cowls, round chimney pots and slate dormer caps', 'newComponents': 15, 'scope': 'Photographed built character corroborated by the LSE 2015 refurbishment and 2025/26 property handbook. Exact capture dates, dimensions and roof equipment positions unverified; unseen elevations and complete interior remain unresolved.'}
FINISH_RECORDS['OLD'] = {'description': 'Five-figure relief with fuller folded robes, profiled heads, blended elbows and taller carved book spines; radial stone arch and four-leaf entry retained', 'newComponents': 4, 'scope': 'User entrance photograph guides shallow sculptural silhouettes and drapery; capture date and dimensions unknown. Authored interpretation, not an exact carving or scan. Central heraldic device, other elevations, roof and complete interiors remain unresolved.'}
FINISH_RECORDS['KSW'] = {'description': 'Curved central oriel sills, bowed glazing and pale stone upper surrounds', 'newComponents': 60, 'scope': 'Central street oriel guided by an undated estate photograph; radius and dimensions estimated. Roof and unseen elevations remain unverified; interiors unchanged.'}
FINISH_RECORDS['5LF'] = {'description': 'Three shallow segmental ground openings and yellow stock-brick facade', 'newComponents': 3, 'scope': 'Street frontage guided by undated estate imagery; arch shape and vertical dimensions estimated. Steps and railings retained. Roof and unseen elevations remain unverified; interiors unchanged.'}
FINISH_RECORDS['51L'] = {'description': 'Filled segmental corner pediment, entrance board and three-column first upper sash with stone surround', 'newComponents': 3, 'scope': 'Tree-obscured estate photograph guides the GIS chamfer entrance; dimensions and decorative profiles estimated. Upper quoins, unseen elevations, roof and interior remain unverified.'}
for code in ['PAN', 'FAW']:
    FINISH_RECORDS[code] = {'description': 'Warm aggregate bands, pale aluminium joinery, reflective glazing and matte interior curtains', 'newComponents': 0, 'scope': 'Shared facade finish guided by an undated PAN entrance photograph; color is estimated, not calibrated. Independent FAW elevations, upper massing, roof and full interiors remain unverified.'}
FINISH_RECORDS['LAK'] = {'description': 'Three-column sashes with six-row first-storey and four-row upper windows, pale joinery and warm red brick', 'newComponents': 140, 'scope': 'Window subdivisions and palette guided by undated estate photographs. Existing bay positions, roof, dormers and historical pediment assignment remain estimates; complete interiors unverified.'}
FINISH_RECORDS['LRB'] = {'description': 'Perimeter mansard, estimated dormers, connected lightwell deck and triangular skylight framing', 'newComponents': 24, 'scope': 'Perimeter roof character guided by structural-engineer project imagery completed in 2001. Roof rise, setback and dormer counts estimated; not a survey. Present roof plant, other facade details and complete interiors remain unverified.'}
FINISH_RECORDS['PEL'] = {'description': 'Projecting silver entrance fascia, yellow reveals, first-floor window box and revolving glazing', 'newComponents': 20, 'scope': 'Entrance guided by undated estate and 2021 public-realm photos; dimensions and colors estimated. Upper windows, massing, roof and complete interior remain unverified.'}
FINISH_RECORDS['PEA'] = {'description': 'Lower blue-black podium with brass starbursts, three-column upper wing, exposed brick side and right roof louvres', 'newComponents': 19, 'scope': 'Street mass division and facade based on venue photography currently published by Sadlers Wells; upload paths are 2023, exact capture date unverified. Heights and hidden elevations estimated, adjacent SAW chimney excluded. Existing interior retained.'}
FINISH_RECORDS['61A'] = {'description': 'Continuous three-storey stone piers and dark metal window belts, with chamfered roof pavilion', 'newComponents': 8, 'scope': 'Undated built photography guides middle-storey window belts and roof pavilion; bay counts, dimensions and pavilion position remain estimates. Corner portal, dormers, unseen elevations and current LSE interior conversion remain unresolved.'}
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
        node.inputs['Alpha'].default_value = float(source.get('webOpacity', 0.30))
        material.surface_render_method = 'DITHERED'
    material.diffuse_color = color
    if full_detail or (source and source.get('siteDetail')):
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
        if not full_detail and any(tag in original.name for tag in ['_V16_', '_V17_']) and not original.name.startswith('35L_'):
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
        if full_detail and is_exterior and has_brick and not mesh.uv_layers:
            raise ValueError(f"Exterior brick requires metric UVs: {original.name}")
        # Joining differently named UV layers would put some facades in UV1 while
        # the browser samples UV0. Normalize only these temporary export meshes.
        needs_uv = full_detail or any(m and m.get('globeMap') for m in mesh.materials)
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
    state = 'detailed' if code in DETAIL_CODES else 'facade' if code in FACADE_RECORDS else 'massing'
    if code == '61A':
        state = 'provisional'
    elif code == '35L':
        state = 'construction'
    interior = bpy.data.collections.get(code + '_PUBLIC_INTERIOR_study')
    has_interior = bool(interior and any(o.type == 'MESH' for o in interior.all_objects))
    metadata.append({'code': code, 'name': record['name'], 'address': record['address'], 'status': state, 'bounds': bounds, 'interior': has_interior})
    if has_interior and interior.get('roomSample'):
        metadata[-1]['interiorStudy'] = {'kind': 'room-sample', 'label': interior['roomLabel'], 'scope': ROOM_RECORDS[code]['scope']}

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
    if record['code'] == 'CKK':
        record['exteriorDirection'] = list(Vector((0.927, 0.65, -0.375)).normalized())
        record['detailView'] = {'label': '入口细节', 'position': [-73, 8, -93], 'target': [-89, 4, -86], 'fov': 38}

for record in metadata:
    if record['code'] == 'LRB':
        record['exteriorDirection'] = list(Vector((-0.648, 0.55, 0.761)).normalized())

for record in metadata:
    finish = FINISH_RECORDS[record['code']]
    record['localRefinement'] = {key: finish[key] for key in ['description', 'newComponents', 'scope']}
    review = REVIEW_RECORDS[record['code']]
    record['latestReview'] = {'version': 43, 'status': review['status'], 'addedObjects': len(review['addedObjects'])}
    for key in ['interiorSections', 'interiorSectionScope']:
        if key in review:
            record[key] = [{field: section[field] for field in ['id', 'label', 'minHeight', 'maxHeight', 'scope']} for section in review[key]] if key == 'interiorSections' else review[key]
    if review.get('detailView'):
        view = review['detailView']
        record['detailView'] = {**view, **{key: [view[key][0], view[key][2], -view[key][1]] for key in ['position', 'target']}}
        record['closeupImage'] = record['code'].lower() + ('-windows' if '窗' in view['label'] else '-entrance')

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
for room in json.loads((ROOT / 'result/blender/stage51/room-spaces.json').read_text())['spaces']:
    source_scene.collection.children.link(bpy.data.collections[room['collection']])
for code in ROOM_RECORDS:
    source_scene.collection.children.link(bpy.data.collections[code + '_PUBLIC_INTERIOR_study'])
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
    camera_names = {'MAR': 'MAR_D3_hall', 'LRB': 'ATRIA_LRB_spiral_and_lifts', 'CKK': 'ATRIA_CKK_timber_landscape', 'CBG': 'CBG_QA_03_academic_stair'}
    if code in ROOM_RECORDS:
        room = ROOM_RECORDS[code]
        record['interiorView'] = {'position': [room['camera'][0], room['camera'][2], -room['camera'][1]],
                                  'target': [room['target'][0], room['target'][2], -room['target'][1]],
                                  'fov': room.get('fov', 50)}
    elif code in camera_names:
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
    if code not in DETAIL_CODES and code not in FACADE_RECORDS:
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
for room in json.loads((ROOT / 'result/blender/stage51/room-spaces.json').read_text())['spaces']:
    record = next(item for item in metadata if item['code'] == room['code'])
    descriptor = export_detail(list(bpy.data.collections[room['collection']].all_objects), room['id'], 'interior')
    study = {'kind':'room-sample', 'label':room['label'], 'scope':room['scope']}
    record.setdefault('interiorSpaces', []).append({
        'id':room['id'], 'label':room['label'], 'scope':room['scope'],
        'interiorAsset':descriptor['url'], 'detailedInterior':descriptor,
        'interiorStudy':study, 'interiorBounds':descriptor['bounds'],
        'interiorView':{'position':[room['camera'][0],room['camera'][2],-room['camera'][1]],
                        'target':[room['target'][0],room['target'][2],-room['target'][1]], 'fov':50},
        'gallery':room['id']+'-interior',
    })

report_path = ROOT / 'result/web/all-buildings/export-manifest.json'
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(detail_report, indent=2) + '\n')

payload = {
    'generatedTextures': [{'name': 'globe-map', 'sha256': hashlib.sha256((ROOT / 'result/blender/stage48/globe-map.png').read_bytes()).hexdigest(), 'source': 'Natural Earth public-domain cartography', 'scope': 'Original reconstructed map, not a source photograph'}],
    'version': '73', 'sourceModelSha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
    'coordinateSystem': 'Local metres; X east, Y up, Z south',
    'origin': [-0.1167, 51.5146], 'buildings': metadata,
    'limitations': 'Photo-informed architectural study. Most dimensions are estimates, not an as-built survey.',
    'footprintAttribution': '© OpenStreetMap contributors, ODbL 1.0',
}
(OUTPUT / 'catalogue.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print('WEB_EXPORT_COMPLETE', flush=True)
