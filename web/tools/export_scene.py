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
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v111.blend'
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
ROOM_RECORDS = {r['code']: r for r in json.loads((ROOT / 'result/blender/stage111-old/room-studies.json').read_text())['buildings']}
REVIEW_RECORDS = {r['code']: r for r in json.loads((ROOT / 'result/blender/stage111-old/building-review.json').read_text())['buildings']}
FACADE_RECORDS['MAR']['exteriorDirection'] = [-.37460657954216003, .02, -.9271838665008545]
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
FINISH_RECORDS['COL']['description'] += '; independent Garrick corner glazing, dark metal joinery, paired pull handles and a mounted red LSE badge beside lowercase lettering'
FINISH_RECORDS['COL']['newComponents'] += 9
FINISH_RECORDS['COL']['scope'] += ' Garrick corner character guided by undated official LSE Estate photograph, currently attributed to Columbia House in the official campus directory. Original aperture vertices and every other window preserved through owned component copies. Existing native LSE lettering reused. Dimensions, handle form and optical finish estimated; no photo textures or reconstructed cafe interior published.'


FINISH_RECORDS['PAR'] = {'description': 'Pointed blind window heads, hierarchical four-column sashes, twin roof cowls, round chimney pots and slate dormer caps', 'newComponents': 15, 'scope': 'Photographed built character corroborated by the LSE 2015 refurbishment and 2025/26 property handbook. Exact capture dates, dimensions and roof equipment positions unverified; unseen elevations and complete interior remain unresolved.'}
FINISH_RECORDS['COW'] = {'description': 'Three-column six-row upper sashes, layered projecting corner-window casing and sill consoles, dark slate roof finish and finer six-row attic sash subdivisions on the photographed street sides', 'newComponents': 6, 'scope': 'Cowdray contractor project photograph guides upper window subdivisions and first upper corner stone profiles. 2019 project, exact capture date unknown; dimensions and profiles estimated. Eleven street-side attic windows retain their vertical muntins and central meeting rails; two quarter rails replaced by four fine subdivisions. Original mesh archived, other sash vertices unchanged. Window centres, floor heights, roof geometry and interiors retained. Unseen elevations, roof arrangement and complete interior remain under review.'}
FINISH_RECORDS['MAR'] = {'description': 'Five academic-wing elevations with larger recessed glazed apertures, bronze joinery and projecting concrete window grids; pale warm precast exterior finish', 'newComponents': 3, 'scope': 'Nick Kane completed-building photos guide academic-wing windows and pale concrete. Previous GIS footprint, floor heights and window centres retained; aperture proportions and grid profiles estimated. Hidden elevations, rear massing, current roof works and complete interiors remain under review.'}
FINISH_RECORDS['SAW'] = {'description': 'Two roof terraces, lower green roof, timber curtain glazing, fixed guardrails, fitted photovoltaic modules and twin high brick flues; four clipped Jatoba curtain-wall fields retained', 'newComponents': 38, 'scope': 'LSE roof photograph guides the terrace, glazing and flue relationships; official historical areas are 115 square metres for the terrace and 254 square metres for photovoltaics. Capture date and 2026 condition unverified. Terrace boundaries, chimney placement, 159 module count and framing are estimates, not a survey or installed equipment inventory. Brick folds and complete interiors remain under review.'}
FINISH_RECORDS['OCS'] = {'description': 'Restored cream lime render and cornice, near-black deep-green shopfront, ochre upper sash surrounds and red-brown upper sash details', 'newComponents': 0, 'scope': 'Ayesa restoration completed June 2023; exterior images published in 2023/2024, precise capture date and 2026 paint condition unverified. Photo-estimated colour palette, not measured colour standards. Existing geometry, roof tiles, inscription and interiors retained. Roof silhouette, unseen elevations and full current interior still require review.'}
FINISH_RECORDS['CKK'] = {'description': 'Glazed rooftop meeting pavilion with pale V braces, dark metal joinery, fourteen silver sun-shading louvres and a low terrace parapet, replacing the previous opaque rooftop block', 'newComponents': 13, 'scope': 'Fixed roof architecture guided by Grimshaw and Jens Willebrand project photographs. Precise capture date and 2026 furniture arrangement unverified. Pavilion footprint, placement and height retained as estimates; terrace depth photo-estimated. Historic frontage, mansard, atrium and all other buildings retained. Full meeting-room interiors and remaining elevations require review.'}
FINISH_RECORDS['OLD'] = {'description': 'Eight four-column Clare Market casements, preserved two-column doorway upper window and five raised central transoms; neutral limestone finish and Houghton four-column windows retained', 'newComponents': 2, 'scope': 'Supplied frontal photograph confirms ordinary four-column windows and heavier upper central transoms. Eight ordinary windows corrected on retained estimated openings; lower five-row divisions retained where the photograph is obscured. All original meshes preserved, other blue frame parts unchanged. Frith figurative panels, roof massing, unseen elevations and full interiors still require review.'}
FINISH_RECORDS['KSW'] = {'description': 'Lower red block faces with seven true shallow horizontal recesses; retained curved central oriel, upper fine brick and pale surrounds', 'newComponents': 4, 'scope': 'LSE Estate exterior photograph and 2025/26 property handbook guide the block finish; capture dates unknown, colors and groove dimensions estimated. Occluded flat joint strips replaced by shallow grooves in owned copies of four lower red mesh families. Original objects preserved, other buildings and interior references unchanged. Roof and unseen elevations remain unverified.'}
FINISH_RECORDS['5LF'] = {'description': 'Yellow stock-brick frontage, shallow segmental ground openings, darker weathered chimney stacks and two black facade-edge rainwater pipes', 'newComponents': 3, 'scope': 'Undated LSE Estate photo guides contrasting dark chimney brick and two edge rainwater pipes. Color, pipe diameter and offsets estimated; original main wall, glazing, openings, terracotta pots, roof and interiors preserved. Source photograph is not proof of 2026 condition. Unseen elevations and roof layout remain unverified.'}
FINISH_RECORDS['51L'] = {'description': 'Three-bay Lincoln frontage with finer upper sashes, three ground arches, right timber entry and a dark front roof band with three pale pedimented dormers, slim edge rail and continuously curved corner masonry and window framing', 'newComponents': 37, 'scope': 'LSE Global School of Sustainability image published 31 July 2025 supports the three-bay frontage and front roof character. Capture date unknown; dimensions, roof material specification, hidden dormer depth, attic grids and partly obscured left triangular pediment estimated. Central triangular and right segmental silhouettes distinguished. Original objects, other faces and interiors preserved; A photo-guided cubic curve replaces the GIS corner chamfer in owned mesh copies, joining adjacent wall tangents while preserving their endpoints. Corner masonry, glazing, frames and stone bands follow the curve; entry joinery remains flat. Curve depth, radius and portal placement are estimates; rear roof layout, unseen elevations and complete interiors remain unverified.'}
for code in ['PAN', 'FAW']:
    FINISH_RECORDS[code] = {'description': 'Warm aggregate bands, pale aluminium joinery, reflective glazing and matte interior curtains', 'newComponents': 0, 'scope': 'Shared facade finish guided by an undated PAN entrance photograph; color is estimated, not calibrated. Independent FAW elevations, upper massing, roof and full interiors remain unverified.'}
FINISH_RECORDS['OLD']['newComponents'] = 5
FINISH_RECORDS['OLD']['description'] += '; five Clare Market reclining figure relief profiles and distinct flowing backgrounds'
FINISH_RECORDS['OLD']['scope'] = FINISH_RECORDS['OLD']['scope'].replace('Frith figurative panels, roof massing, unseen elevations and full interiors still require review.', 'Roof massing, unseen elevations and full interiors still require review.') + ' Five main frontage relief panels interpreted from the supplied frontal photograph and Jeremy Haslam architectural sculpture study photos C-H, publication 2010-01, image capture dates unknown. Photo C establishes frontage order G,E,F,D,H. Contours and shallow depth are authored estimates, not scans; sixth side panel remains unillustrated and unresolved. Original architecture and finishes preserved; no source photo textures exported.'
FINISH_RECORDS['OLD']['description'] += '; shallow dressed entrance stone courses, mounted plaques and neutral reflective semi-transparent door glazing'
FINISH_RECORDS['OLD']['newComponents'] += 9
FINISH_RECORDS['OLD']['scope'] += ' User entrance photograph received 1 October 2026 guides reduced stone projections and door finish; capture date unknown. Stone depth and glazing optical values estimated, not surveyed or calibrated. Closed stone backing fills the formerly concealed support gaps; entry plaques and lettering moved with their support. Original objects and all other buildings preserved; no photo textures or speculative interior layout exported. Final Sale mesh anatomy remains coarse and unresolved.'
FINISH_RECORDS['OLD']['description'] += '; denser open plastic strands in the Houghton entrance artwork'
FINISH_RECORDS['OLD']['newComponents'] += 2
FINISH_RECORDS['OLD']['scope'] += ' User entrance photograph received 2 October 2026 guides a photographic strand-density estimate. Two owned mesh copies widen existing figure ribbons and product strands without adding faces; poses, materials, open mesh and all original objects retained. This is not an artwork scan or measured weave specification.'
FINISH_RECORDS['PAN'] = {'description': 'Independent automatic entrance leaf with 980mm clear width, low push pad and fixed side glazing; dark revolving-door metal distinct from pale upper aluminium joinery', 'newComponents': 11, 'scope': 'Shared PAN/FAW entrance guided by the AccessAble provider survey and exterior photograph. Clear width and 780mm push-pad height are documented; door registration, height and plate sizes remain estimates. The provider mentions August 2020 survey context; precise image capture and 2026 access condition unverified. Original revolving-door geometry and other facade components retained. Roof, unseen elevations and full interiors remain under review.'}
FINISH_RECORDS['LAK'] = {'description': 'Three-column sashes with six-row first-storey and four-row upper windows, pale joinery and warm red brick', 'newComponents': 140, 'scope': 'Window subdivisions and palette guided by undated estate photographs. Existing bay positions, roof, dormers and historical pediment assignment remain estimates; complete interiors unverified.'}
FINISH_RECORDS['LRB'] = {'description': 'Portugal Street three historic window storeys, seven triple-light bays, distinct ground entrances, eighteen mansard dormers and terrace balustrade; stepped roof and surveyed skylight retained', 'newComponents': 9, 'scope': 'April 2025 Fulkers Bailey Russell existing northwest elevation 4556-FBR-LR-ZZ-DR-A-114 P01 guides the window rhythm and labelled cornice/mansard heights. Existing GIS street length retained with proportional drawing registration; unlabelled window edges, dormer depth, ornament sizes and colour are estimates. Archived originals retained. The northeast rounded corner, other historical elevations, complete interior floor levels and remaining plant details still require reconstruction.'}
FINISH_RECORDS['PEL'] = {'description': 'Projecting silver entrance fascia, yellow reveals, first-floor window box and revolving glazing', 'newComponents': 20, 'scope': 'Entrance guided by undated estate and 2021 public-realm photos; dimensions and colors estimated. Upper windows, massing, roof and complete interior remain unverified.'}
FINISH_RECORDS['PEA'] = {'description': 'Lower blue-black podium with brass starbursts, three-column upper wing, exposed brick side and right roof louvres', 'newComponents': 19, 'scope': 'Street mass division and facade based on venue photography currently published by Sadlers Wells; upload paths are 2023, exact capture date unverified. Heights and hidden elevations estimated, adjacent SAW chimney excluded. Existing interior retained.'}
FINISH_RECORDS['61A'] = {'description': 'Continuous three-storey stone piers and dark metal window belts, with chamfered roof pavilion', 'newComponents': 8, 'scope': 'Undated built photography guides middle-storey window belts and roof pavilion; bay counts, dimensions and pavilion position remain estimates. Corner portal, dormers, unseen elevations and current LSE interior conversion remain unresolved.'}
FINISH_RECORDS['OLD']['description'] += '; finer open plastic figure lattice with continuous pose-specific robe silhouettes'
FINISH_RECORDS['OLD']['newComponents'] += 1
FINISH_RECORDS['OLD']['scope'] += ' Figure silhouettes guided by artist front photograph and supplied entrance photograph; strand cross sections approximated by double-sided ribbons. Anatomy, cloth, lattice spacing and unseen artwork depth remain estimates.'

for code, count in [('OLD', 2), ('COL', 1)]:
    FINISH_RECORDS[code]['description'] += '; existing LSE vector mark replaces generic plaque lettering'
    FINISH_RECORDS[code]['newComponents'] += count
    FINISH_RECORDS[code]['scope'] += ' Project logo SVG contours used for three closed extruded letters on retained supports, with original emblem padding. Plaque dimensions and locations remain photo estimates; facade geometry and interiors unchanged.'
FINISH_RECORDS['SAL']['description'] += '; bell-curved front tower roofs, arched lantern glazing and layered dark cornices'
FINISH_RECORDS['SAL']['newComponents'] += 3
FINISH_RECORDS['SAL']['scope'] += ' Jestico + Whiles built-project photograph guides two front tower roof profiles and lantern joinery. Existing tower centers and primary roof endpoints retained; curvature, pane and frame dimensions and optical finish are photo estimates. Original objects archived, other facades and all interiors unchanged; full roof arrangement and rear elevations unresolved.'
FINISH_RECORDS['SAR']['description'] += '; dressed upper window surrounds, segmental hoods, school-name fascia, four-column three-row first-floor sashes and local red-brick finish'
FINISH_RECORDS['SAR']['newComponents'] += 10
FINISH_RECORDS['SAR']['scope'] += ' Undated LSE Estate photograph and archived 2018 street photograph guide stonework and fascia. Three central upper rows receive estimated surrounds; tree-obscured bays repeat the visible profile, so exact hood order and fine carving are unresolved. Existing opening vertices, footprint, floor count, roof and all interiors retained; red-brick colour is a photographic estimate.'
FINISH_RECORDS['OLD']['description'] += '; continuously shaded curved entry reveal with five restrained limestone tones'
FINISH_RECORDS['OLD']['newComponents'] += 1
FINISH_RECORDS['OLD']['scope'] += ' October 2026 user-supplied entrance photograph guides finish only; capture date unknown. Existing vertices, joints and openings retained. Analytic curve normals remove faceted shading without extra triangles; exact stone weathering, artwork, roof and full interiors remain unresolved.'
FINISH_RECORDS['MAR']['description'] += '; three north podium windows with a clear single glass column and one central transom'
FINISH_RECORDS['MAR']['newComponents'] += 7
FINISH_RECORDS['MAR']['scope'] += ' Nick Kane built photographs 02 and 03 guide north podium joinery. Original aperture and pane vertices retained; only twenty generic frame rails replaced with fifteen measured replacement rails. Obsolete rear-wing sill and trim overlaps and the overhanging mezzanine slab edge cut out of the three retained north podium apertures; retained floor height and stair aperture preserved. Glass finish estimated; photo capture date unknown, whole roof and full interior structure remain unresolved.'
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
        if is_exterior and has_brick and not mesh.uv_layers:
            raise ValueError(f"Exterior brick requires metric UVs: {original.name}")
        # Joining differently named UV layers would put some facades in UV1 while
        # the browser samples UV0. Normalize only these temporary export meshes.
        needs_uv = full_detail or has_brick or any(m and m.get('globeMap') for m in mesh.materials)
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
        if record['code'] == 'KSW':
            # Present the photographed street facade instead of the unverified roof.
            record['exteriorDirection'] = list(Vector((-23.23192499745369, 1.0, 15.89237744683553)).normalized())

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

# These photographed street-facing directions also drive gallery bounds fitting.
lincolns_front_directions = {'5LF': [0.4290930077994338, 0.008769146891963566, 0.9032177438029118], '51L': [0.2224913213734008, 0.00587605328513892, -0.9749169625723559]}
for record in metadata:
    if record['code'] in lincolns_front_directions:
        record['exteriorDirection'] = lincolns_front_directions[record['code']]

# The newly reviewed three-bay frontage is the primary 51L exterior view.
for record in metadata:
    if record['code'] == '51L':
        record['exteriorDirection'] = list(Vector((-.4050395844, .10, -.9142991497)).normalized())

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
    'version': '111', 'sourceModelSha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
    'coordinateSystem': 'Local metres; X east, Y up, Z south',
    'origin': [-0.1167, 51.5146], 'buildings': metadata,
    'limitations': 'Photo-informed architectural study. Most dimensions are estimates, not an as-built survey.',
    'footprintAttribution': '© OpenStreetMap contributors, ODbL 1.0',
}
(OUTPUT / 'catalogue.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print('WEB_EXPORT_COMPLETE', flush=True)
