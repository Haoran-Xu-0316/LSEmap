"""Correct photographed PAR street glazing surface orientation and dielectric finish.

Archived LSE photographs cover the main frontage, two entrance fields and four
front roof dormers. Their178/179 thin boxes have inward winding. Keep all box
coordinates and corner UVs, reverse only those photographed closed components.
Unseen side/rear panes retain their geometry, winding and original material.
Opaque alpha is retained because complete interior volumes are not registered.
Photo capture dates and exact glass specifications remain unknown.
"""
import bpy
import bmesh
from mathutils import Vector

SOURCES = ('PAR_D5_recessed_glass_glass', 'PAR_D5_portal_fanlight_glass',
           'PAR_D5_portal_lower_glass_glass', 'PAR_D5_dormer_glass_glass')
PREFIX = 'PAR_NEXT_EXTERIOR180_'
# Accepted historical frontage registration, not a measured current survey.
ORIGIN = Vector((-45.64951705932617, -2.6588637828826904, 0.0))
NORMAL = Vector((0.24640773236751556, 0.9691662192344666, 0.0))
SOURCE_URL = 'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Cap-Dev/2015-Parish-Hall.pdf'

def apply_par_exterior180():
    """Operate on loaded native only; never open or save a full campus."""
    names = [PREFIX + name.removeprefix('PAR_') for name in SOURCES]
    if all(name in bpy.data.objects for name in names):
        return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[])
    if any(name in bpy.data.objects for name in names):
        raise RuntimeError('Partial PAR180 component')
    sources = [bpy.data.objects[name] for name in SOURCES]
    if any(source.hide_render for source in sources):
        raise RuntimeError('Expected active PAR source glazing')
    original_glass = sources[0].data.materials[0]
    glass = original_glass.copy()
    glass.name = PREFIX + 'dielectric_street_glass'
    shader = next(node for node in glass.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
    shader.inputs['Metallic'].default_value = 0.0
    glass['surfaceEstimate'] = 'Dielectric nonmetal; inherited tint/roughness/opaque alpha retained. Capture date unknown; not optical measurement.'
    for source, name in zip(sources, names):
        clone = source.copy(); clone.data = source.data.copy()
        clone.name = name; clone.data.name = name
        bpy.data.collections['PAR_EXTERIOR'].objects.link(clone)
        clone.data.materials.append(glass)
        mesh = bmesh.new(); mesh.from_mesh(clone.data)
        pending = set(mesh.verts); count = 0; retained = 0
        while pending:
            seed = pending.pop(); group = {seed}; stack = [seed]
            while stack:
                vertex = stack.pop()
                for edge in vertex.link_edges:
                    other = edge.other_vert(vertex)
                    if other in pending:
                        pending.remove(other); group.add(other); stack.append(other)
            faces = {face for vertex in group for face in vertex.link_faces}
            assert len(group) == 8 and len(faces) == 6
            coords = [clone.matrix_world @ vertex.co for vertex in group]
            centre = sum(coords, Vector()) / 8
            depth = (centre - ORIGIN).dot(NORMAL)
            known = source.name != SOURCES[0] or -.30 < depth < -.10
            if known:
                bmesh.ops.recalc_face_normals(mesh, faces=list(faces))
                for face in faces: face.material_index = 1
                count += 1
            else:
                retained += 1
        mesh.to_mesh(clone.data); mesh.free(); clone.data.update()
        clone['photographedPaneCount'] = count
        clone['retainedUnseenPaneCount'] = retained
        clone['sourceURL'] = SOURCE_URL
        clone['captureDate'] = 'unknown; 2015 project record is not capture date'
        source.hide_render = True; source.hide_set(True)
    return dict(alreadyApplied=False, addedObjects=names, archivedObjects=list(SOURCES), changedObjects=[])
