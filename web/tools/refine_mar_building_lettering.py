"""Restore the photographed two-line north-front Marshall Building lettering.

Callable in a loaded Blender scene. The built Nick Kane photograph supports
wording, two lines, dark individual letters and the far-left ground-floor pier.
Typeface, dimensions, letter extrusion and placement are photographic estimates.
No scene opening or saving. Only the photographed left ground bay is corrected;
original mesh datablocks and all other elevations remain preserved.
"""
from pathlib import Path
import math
import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OWNED = 'MAR_NEXT_LETTER165_north_building_name'
ORIGIN = Vector((-8.696325894899289, 49.33154396120258, 0))
U = Vector((math.cos(math.radians(22)), math.sin(math.radians(22)), 0))
N = Vector((-U.y, U.x, 0))


def apply_mar_building_lettering():
    if bpy.data.objects.get(OWNED):
        return {'alreadyApplied': True, 'changedObjects': [], 'addedObjects': []}
    collection = bpy.data.collections['MAR_EXTERIOR']
    retained_names = []
    removed = {}
    sources = ['MAR_V115_retained_V104_recessed_window_glass',
               'MAR_V115_retained_V104_window_frames',
               'MAR_V115_retained_V104_window_sills',
               'MAR_D5_V17_sill_expansion_joint',
               'MAR_V115_retained_V104_D5_V16_metal_sill_channel',
               'MAR_V115_retained_V104_D5_V17_sill_front_fascia',
               'MAR_V115_retained_D5_V16_sill_drain_slot',
               'MAR_NEXT_PANEL_retained_04_NEXT_retained_V16_reveal_bead',
               'MAR_NEXT_PANEL_retained_05_etained_V17_folded_jamb_return',
               'MAR_NEXT_PANEL_retained_06_NEXT_retained_V16_glazing_seal',
               'MAR_NEXT_PANEL_retained_07_etained_V17_flashing_downstand',
               'MAR_NEXT_PANEL_retained_08_EXT_retained_V17_head_flashing',
               'MAR_NEXT_PANEL_retained_09__retained_V17_cap_shadow_joint']
    for index, name in enumerate(sources):
        source = bpy.data.objects[name]
        assert not source.hide_render
        replacement = source.copy(); replacement.data = source.data.copy()
        replacement.name = 'MAR_NEXT_LETTER165_retained_%02d_' % index + name.split('_')[-1]
        collection.objects.link(replacement)
        bm = bmesh.new(); bm.from_mesh(replacement.data)
        seen, erase, count = set(), [], 0
        erased_bounds = []
        bm.verts.ensure_lookup_table(); bm.verts.index_update()
        for vertex in bm.verts:
            if vertex in seen: continue
            stack, component = [vertex], []; seen.add(vertex)
            while stack:
                v = stack.pop(); component.append(v)
                for edge in v.link_edges:
                    other = edge.other_vert(v)
                    if other not in seen: seen.add(other); stack.append(other)
            coordinates = [(replacement.matrix_world @ v.co-ORIGIN) for v in component]
            if all(16.3 < p.dot(U) < 23 and 20.3 < p.dot(N) < 21.3 and (p+ORIGIN).z < 4.61 for p in coordinates):
                erase.extend(component); count += 1
                erased_bounds.append([[min(p.dot(axis) for p in coordinates), max(p.dot(axis) for p in coordinates)] for axis in [U, N, Vector((0,0,1))]])
        assert count > 0, name
        erased_indices = [v.index for v in erase]
        bmesh.ops.delete(bm, geom=erase, context='VERTS'); bm.to_mesh(replacement.data); bm.free()
        replacement.data.update(); source.hide_render = True; source.hide_set(True)
        retained_names.append(replacement.name); removed[name] = {'components': count, 'vertices': len(erased_indices), 'removedVertexIndices': erased_indices, 'componentLocalBounds': erased_bounds}
    wall = bpy.data.objects['MAR_MAR_north_ground_pierced_wall']
    tree = BVHTree.FromPolygons([wall.matrix_world @ v.co for v in wall.data.vertices],
                               [list(p.vertices) for p in wall.data.polygons])
    def world(x, y, z):
        return ORIGIN + U*x + N*y + Vector((0, 0, z))
    hit, normal, _, _ = tree.ray_cast(world(21, 23, 3.85), -N, 4)
    assert hit is not None and normal.dot(N) > .99
    wall_depth = (hit-ORIGIN).dot(N)
    assert abs(wall_depth-20.8) < .001
    vertices, faces = [], []
    font = bpy.data.fonts.load(str(ROOT/'web/src/fonts/Roboto-variable.ttf'), check_existing=True)
    for line, baseline in [('The Marshall', 3.95), ('Building', 3.51)]:
        curve = bpy.data.curves.new('MAR_letter165_temporary', 'FONT')
        curve.body, curve.size, curve.font = line, .42, font
        curve.extrude, curve.resolution_u = .006, 2
        temporary = bpy.data.objects.new('MAR_letter165_temporary', curve)
        collection.objects.link(temporary)
        bpy.context.view_layer.update()
        evaluated = temporary.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        start = len(vertices)
        vertices.extend(world(22.35-v.co.x, wall_depth+.010+v.co.z, baseline+v.co.y)
                        for v in mesh.vertices)
        faces.extend(tuple(start+i for i in p.vertices) for p in mesh.polygons)
        evaluated.to_mesh_clear()
        bpy.data.objects.remove(temporary, do_unlink=True)
        bpy.data.curves.remove(curve)
    mesh = bpy.data.meshes.new(OWNED)
    mesh.from_pydata(vertices, [], faces); mesh.update()
    material = bpy.data.materials.new('MAR_LETTER165_dark_bronze')
    material.use_nodes = True; material.diffuse_color = (.042, .039, .034, 1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Metallic'].default_value = .25
    shader.inputs['Roughness'].default_value = .48
    mesh.materials.append(material)
    obj = bpy.data.objects.new(OWNED, mesh); collection.objects.link(obj)
    obj['evidence'] = 'Nick Kane MAR photograph02,2022upload,capturedateunknown'
    obj['scope'] = 'Photographed two-line north ground-floor individual letters; font, size, depth and placement estimated'
    from facade_geometry import Geometry, materials
    materials['mar_letter165_concrete'] = wall.data.materials[0]
    wall_patch = Geometry('MAR', 'ground165_blank_wall', 'mar_letter165_concrete')
    wall_patch.name = 'MAR_NEXT_LETTER165_left_ground_blank_wall'
    wall_patch.box(world(19.65, 20.66, 1.95), (6.3, .28, 3.5), math.radians(22))
    panel = wall_patch.finish()
    for modifier in list(panel.modifiers): panel.modifiers.remove(modifier)
    panel['scope'] = 'Photographed solid north-left ground-floor bay, registered to existing aperture; dims inherited'
    local = [((p-ORIGIN).dot(U), (p-ORIGIN).dot(N), p.z) for p in vertices]
    assert min(p[0] for p in local) > 16.5 and max(p[0] for p in local) < 22.8
    assert min(p[2] for p in local) > 3.3 and max(p[2] for p in local) < 4.5
    return {'addedObjects': retained_names + [panel.name, OWNED], 'changedObjects': [],
            'archivedObjects': list(removed), 'removedApertureComponents': removed,
            'destinationCollection': 'MAR_EXTERIOR', 'wallOwner': wall.name,
            'wallPlaneDepthM': wall_depth, 'correctedApertureLocalBounds': [[16.5,22.8],[20.52,20.8],[.2,3.7]],
            'source': 'data/collections/architecture_round5/images/MAR/MAR_mar_kane_02.jpg',
            'sourceUrl': 'https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/',
            'sourceDate': '2022 upload; capture date unknown',
            'lettering': ['The Marshall', 'Building'],
            'vertices': len(vertices), 'faces': len(faces),
            'localBounds': [[min(p[i] for p in local), max(p[i] for p in local)] for i in range(3)],
            'limitations': ['Roboto is an approximate sans-serif match, not a verified original signage typeface',
                            'Letter dimensions, spacing, extrusion and facade position photo-estimated',
                            'Only photographed north-left ground-floor bay sealed; unrelated glazing and interiors retained']}
