"""Correct the complete north-facing library dome aperture winding.

The original dome slice plane removes the north/upward shell. Its retained
transparent fan was wound south/downward; fix that complete glass region only.
"""
import bpy
import bmesh
from mathutils import Vector
SOURCE = 'LRB_V109_survey_aperture_glass'
OWNED = 'LRB_FACADE174_outward_north_aperture_glass'


def apply_lrb_facade174():
    """Operate on the loaded scene; preserve original geometry and materials."""
    if OWNED in bpy.data.objects:
        return dict(alreadyApplied=True, addedObjects=[OWNED],
                    archivedObjects=[SOURCE], changedObjects=[])
    original = bpy.data.objects[SOURCE]
    replacement = original.copy()
    replacement.data = original.data.copy()
    replacement.name = OWNED
    replacement.data.name = OWNED
    for collection in original.users_collection:
        collection.objects.link(replacement)
    mesh = bmesh.new()
    mesh.from_mesh(replacement.data)
    outward = replacement.matrix_world.to_3x3().inverted() @ Vector((0, 1, 1))
    flipped = 0
    for face in mesh.faces:
        if face.normal.dot(outward) < 0:
            face.normal_flip()
            flipped += 1
    if flipped != 178:
        mesh.free()
        raise RuntimeError('Expected the complete178-face inward aperture')
    mesh.to_mesh(replacement.data)
    mesh.free()
    replacement.data.update()
    replacement.hide_render = False
    replacement.hide_set(False)
    original.hide_render = True
    original.hide_set(True)
    return dict(alreadyApplied=False, addedObjects=[OWNED],
                archivedObjects=[SOURCE], changedObjects=[])
