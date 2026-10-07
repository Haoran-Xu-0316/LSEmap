"""Correct only the three photographed SHF dormer pane surfaces.

The LSE Estates image shows six-light glazing in the three unobscured right
roof windows. Native178 has inward thin boxes there, giving two alpha layers.
Keep the original street-facing outline and per-corner UV on one outward pane.
The scaffold-obscured left window and all other glazing remain unchanged.
Dimensions remain the inherited photographic estimate, not a measured survey.
"""
import bpy
import bmesh
from mathutils import Vector

SOURCE = 'SHF_NEXT_GLAZING149_V50_dormer_glass_glass'
OWNED = 'SHF_NEXT_EXTERIOR179_three_dormer_panes'
NORMAL = Vector((-.9496077299118042, .31344062089920044, 0))
SOURCE_URL = 'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/Sheffield-Street.jpg'


def apply_shf_exterior179():
    """Modify the loaded scene only; preserve the complete source as archive."""
    if OWNED in bpy.data.objects:
        return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[])
    source = bpy.data.objects[SOURCE]
    if source.hide_render:
        raise RuntimeError('Expected active SHF149 dormer glass')
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = OWNED
    obj.data.name = OWNED
    bpy.data.collections['SHF_EXTERIOR'].objects.link(obj)
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    normal = obj.matrix_world.to_3x3().transposed() @ NORMAL
    photographed = [face for face in mesh.faces if face.material_index == 1]
    assert len(photographed) == 18
    groups = []
    pending = set(photographed)
    while pending:
        seed = pending.pop()
        group = {seed}
        stack = [seed]
        while stack:
            face = stack.pop()
            for edge in face.edges:
                for neighbour in edge.link_faces:
                    if neighbour in pending:
                        pending.remove(neighbour)
                        group.add(neighbour)
                        stack.append(neighbour)
        groups.append(group)
    assert len(groups) == 3 and all(len(group) == 6 for group in groups)
    retained = set()
    for group in groups:
        # Choose the actual outer broad face, never a side or rear face.
        pane = max(group, key=lambda face: face.calc_center_median().dot(normal))
        assert pane.calc_area() > 1.0
        if pane.normal.dot(normal) < 0:
            pane.normal_flip()
        retained.add(pane)
    bmesh.ops.delete(mesh, geom=[face for face in photographed if face not in retained], context='FACES')
    bmesh.ops.delete(mesh, geom=[vertex for vertex in mesh.verts if not vertex.link_faces], context='VERTS')
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    assert len(obj.data.polygons) == 9
    glass = source.data.materials[1].copy()
    glass.name = 'SHF_NEXT_EXTERIOR179_photographed_glass'
    glass['surfaceEstimate'] = 'One outward pane per photographed dormer; inherited webOpacity .84 retained; capture date unknown'
    obj.data.materials[1] = glass
    obj['reviewScope'] = 'Three photographed right dormers only; original outlines, tint and optical estimates retained'
    obj['sourceURL'] = SOURCE_URL
    obj['captureDate'] = 'unknown'
    source.hide_render = True
    source.hide_set(True)
    return dict(alreadyApplied=False, addedObjects=[OWNED], archivedObjects=[SOURCE], changedObjects=[])
