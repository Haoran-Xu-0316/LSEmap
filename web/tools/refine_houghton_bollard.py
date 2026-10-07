"""Correct one mapped Houghton bollard from the user's street photograph.

Call apply_houghton_bollard() in the open Blender scene. This changes only the
mapped post's disconnected parts and adds one inexpensive turned-profile mesh.
The location is retained from archived OSM; profile dimensions are estimates.
"""
from pathlib import Path
import hashlib
import math
import bpy

ROOT = Path(__file__).resolve().parents[2]
CENTER = (1.0343516393182428, -91.20939382992195)
TARGET = 'SITE_V47_Mapped_street_furniture'
OWNED = 'SITE165_Houghton_cast_iron_bollard'
REFERENCE = 'data/collections/public-realm-2026/user-references/reference-09.png'


def apply_houghton_bollard():
    """Retain the mapped center and non-owned furniture without duplication."""
    source = bpy.data.objects[TARGET]
    if bpy.data.objects.get(OWNED):
        assert source.get('houghtonBollard165'), 'Partial previous application'
        return {'alreadyApplied': True, 'addedObjects': [OWNED], 'changedObjects': [TARGET]}
    assert not source.get('houghtonBollard165'), 'Partial previous application'
    mesh = source.data
    removed = {
        v.index for v in mesh.vertices
        if math.hypot((source.matrix_world @ v.co).x-CENTER[0],
                      (source.matrix_world @ v.co).y-CENTER[1]) < .12
    }
    # Original stage47 post: three 16-sided cylinders and one 48-sided ring.
    assert len(removed) == 192, len(removed)
    retained = [v.index for v in mesh.vertices if v.index not in removed]
    remap = {old: new for new, old in enumerate(retained)}
    retained_faces = [p for p in mesh.polygons if not any(i in removed for i in p.vertices)]
    assert all(all(i in removed for i in p.vertices) or all(i not in removed for i in p.vertices)
               for p in mesh.polygons), 'Post must consist of disconnected solids'
    coords = [tuple(mesh.vertices[i].co) for i in retained]
    faces = [tuple(remap[i] for i in p.vertices) for p in retained_faces]
    replacement = bpy.data.meshes.new(mesh.name+'_Houghton165')
    replacement.from_pydata(coords, [], faces)
    for material in mesh.materials:
        replacement.materials.append(material)
    for polygon, original in zip(replacement.polygons, retained_faces):
        polygon.material_index = original.material_index
        polygon.use_smooth = original.use_smooth
    replacement.update()
    assert [tuple(v.co) for v in replacement.vertices] == coords
    source.data = replacement
    source['houghtonBollard165'] = True
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)

    material = bpy.data.materials['SITE_V47_iron'].copy()
    material.name = 'SITE165_Houghton_black_cast_iron'
    material.diffuse_color = (.035, .043, .041, 1)
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Metallic'].default_value = .12
    shader.inputs['Roughness'].default_value = .59
    # Continuous revolved surface avoids superposed ring seams and z-fighting.
    # Shoulder, narrow neck, broad cap and small dome follow visible silhouette.
    profile = [(.050,.077),(.065,.083),(.088,.083),(.105,.060),
               (.290,.060),(.306,.072),(.327,.072),(.340,.060),
               (.805,.057),(.825,.067),(.855,.067),(.867,.054),
               (.953,.052),(.968,.088),(.987,.088),(1.003,.071),
               (1.015,.046),(1.042,.040),(1.061,.025)]
    segments = 24
    vertices = [(CENTER[0]+radius*math.cos(i*math.tau/segments),
                 CENTER[1]+radius*math.sin(i*math.tau/segments), z)
                for z, radius in profile for i in range(segments)]
    polygons = [tuple(reversed(range(segments)))]
    polygons += [(j*segments+i,j*segments+(i+1)%segments,
                  (j+1)*segments+(i+1)%segments,(j+1)*segments+i)
                 for j in range(len(profile)-1) for i in range(segments)]
    apex = len(vertices)
    vertices.append((CENTER[0],CENTER[1],1.068))
    top = (len(profile)-1)*segments
    polygons += [(top+i,top+(i+1)%segments,apex) for i in range(segments)]
    new_mesh = bpy.data.meshes.new(OWNED)
    new_mesh.from_pydata(vertices, [], polygons)
    new_mesh.materials.append(material)
    new_mesh.update()
    assert all(p.area > 1e-10 for p in new_mesh.polygons), 'Degenerate profile faces'
    obj = bpy.data.objects.new(OWNED,new_mesh)
    bpy.data.collections['03_PUBLIC_REALM'].objects.link(obj)
    for polygon in new_mesh.polygons:
        polygon.use_smooth = len(polygon.vertices) <= 4
    obj['reference'] = REFERENCE
    obj['scope'] = 'One original archived OSM center; photo-estimated black cast-iron profile'
    obj['dimensionStatus'] = 'Height1.018m above paving; estimated, not measured'
    obj['sourcePhotoSha256'] = hashlib.sha256((ROOT/REFERENCE).read_bytes()).hexdigest()
    return {'alreadyApplied': False, 'addedObjects':[OWNED], 'changedObjects':[TARGET],
            'retainedFurnitureVertices':len(retained), 'removedPlainPostVertices':192,
            'newVertices':len(vertices), 'newFaces':len(polygons),
            'center':list(CENTER), 'photoReference':REFERENCE,
            'locationSource':'Archived OSM node/11867654067; retained stage47 position',
            'photoDate':'Unknown; user supplied reference',
            'limitations':['Photo identifies Houghton street post style, not this exact individual post',
                           'Profile dimensions, dark paint and cast-metal finish are estimates',
                           'No new post locations or current street survey claim']}
