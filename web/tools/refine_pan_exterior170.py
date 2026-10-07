"""Restore the photographed yellow PAN/FAW entrance canopy soffit.

Use on an already loaded scene. Clone the existing portal beam, retain every
vertex/corner UV, and copy PAN's existing yellow onto its lower face only.
The completed-project photo establishes the yellow underside, not new roof,
facade dimensions or current2026condition. No campus load or save occurs here.
"""
import bpy
import bmesh

SOURCE = 'PAN_D3_portal_upper_beam'
OWNED = 'PAN_EXTERIOR170_yellow_canopy_soffit'


def apply_pan_exterior170():
    if bpy.data.objects.get(OWNED):
        return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[])
    source = bpy.data.objects[SOURCE]
    assert not source.hide_render and source.type == 'MESH'
    assert len(source.data.vertices) == 8 and len(source.data.polygons) == 6
    bm = bmesh.new()
    bm.from_mesh(source.data)
    assert all(e.is_manifold for e in bm.edges)
    volume = bm.calc_volume(signed=True)
    assert abs(volume) > .01
    bm.free()
    world = [source.matrix_world @ v.co for v in source.data.vertices]
    lower = min(v.z for v in world)
    indices = [p.index for p in source.data.polygons if all(abs(world[i].z - lower) < .001 for i in p.vertices)]
    assert len(indices) == 1
    replacement = source.copy()
    replacement.data = source.data.copy()
    replacement.name = OWNED
    bpy.data.collections['PAN_EXTERIOR'].objects.link(replacement)
    yellow = bpy.data.objects['PAN_D3_yellow_entrance_reveal'].data.materials[0].copy()
    yellow.name = 'PAN_EXTERIOR170_yellow_canopy_finish'
    replacement.data.materials.append(yellow)
    if volume < 0:
        mesh = bmesh.new()
        mesh.from_mesh(replacement.data)
        for face in mesh.faces:
            face.normal_flip()
        mesh.to_mesh(replacement.data)
        mesh.free()
    for i in indices:
        replacement.data.polygons[i].material_index = len(replacement.data.materials) - 1
    replacement.data.update()
    source.hide_render = True
    source.hide_set(True)
    return dict(alreadyApplied=False, addedObjects=[OWNED], archivedObjects=[SOURCE], changedObjects=[],
                affectedFaceIndices=indices, originalSignedVolume=volume, correctedNormals=volume < 0,
                sourceURL='https://www.architectureplb.com/sectors/universities-and-colleges/lse-towers',
                sourceFile='result/blender/faw_exterior156/sources/plb-entrance.jpg',
                projectCompletion='August2018', photographCaptureDate='unknown', photographUploadDate='unknown',
                limitations=['Full existing beam underside adopts the photographed yellow; unchanged dimensions are estimates',
                             'Yellow matches the copied native reveal finish, without calibrated reflectance or colour claims',
                             'All front/sides/top dark beam faces, silver fascia, letters and door glazing remain retained',
                             'No fixtures, seams, light fittings, rear/crown detail or new glass layers added'])
