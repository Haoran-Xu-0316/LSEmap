"""SAW: use one finite exterior pane per photographed timber-curtain light.

Apply to a loaded campus without opening/saving it. Four existing curtain fields
were closed transparent boxes, causing both large faces to stack alpha in the
browser. Keep the outward large faces and their UVs; remove back/edge faces.
Source dimensions and optical values are authored estimates, not a glazing survey.
"""
from pathlib import Path
import hashlib
import bpy, bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ['north_fold', 'central_return', 'south_fold', 'glazed_notch_return']
SOURCES = ['SAW_NEXT_glazing_'+family+'_panes' for family in FAMILIES]
NAMES = ['SAW_EXTERIOR166_'+family+'_single_panes' for family in FAMILIES]
# Accepted native stage82 curtain registration, verified against source165.
# These constants are local authoring evidence, not a dependency on a deleted backup.
NORMALS = {
    'north_fold': (0.9595568180084229, 0.28151512145996094, -0.0),
    'central_return': (0.71757972240448, -0.696476399898529, -0.0),
    'south_fold': (0.9808940291404724, -0.19454242289066315, -0.0),
    'glazed_notch_return': (-0.3519330322742462, -0.9360251426696777, 0.0),
}


def apply_saw_exterior166():
    if all(bpy.data.objects.get(name) for name in NAMES):
        return dict(addedObjects=[], archivedObjects=[], alreadyApplied=True)
    assert not any(bpy.data.objects.get(name) for name in NAMES)
    collection = bpy.data.collections['SAW_EXTERIOR']
    material = bpy.data.objects[SOURCES[0]].data.materials[0].copy()
    material.name = 'SAW_EXTERIOR166_dielectric_curtain_glass'
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Metallic'].default_value = 0
    shader.inputs['IOR'].default_value = 1.5
    material['webOpacity'] = .55
    material['opticsBasis'] = 'Estimated one-sheet alpha approximation; daylight photographs show reflected sky and visible reception/stair structure.'
    changes = []
    for family, name, owned in zip(FAMILIES, SOURCES, NAMES):
        normal = Vector(NORMALS[family]); src = bpy.data.objects[name]
        clone = src.copy(); clone.data = src.data.copy(); clone.name = owned
        clone.data.name = owned; collection.objects.link(clone)
        bm = bmesh.new(); bm.from_mesh(clone.data)
        groups=[]; unseen=set(bm.verts)
        while unseen:
            v=unseen.pop(); group={v}; queue=[v]
            while queue:
                for edge in queue.pop().link_edges:
                    for other in edge.verts:
                        if other in unseen:
                            unseen.remove(other);group.add(other);queue.append(other)
            groups.append(group)
        selected=[]
        for group in groups:
            faces={f for v in group for f in v.link_faces}
            # A positive outward normal and largest area isolate the source box's
            # single front face, including triangular lights at the sloping head.
            candidates=[f for f in faces if (clone.matrix_world.to_3x3()@f.normal).normalized().dot(normal)>.99]
            assert len(candidates)==1, (family,len(candidates))
            selected.extend(candidates)
        removed=[f for f in bm.faces if f not in selected]
        old_vertices=len(bm.verts);old_faces=len(bm.faces)
        bmesh.ops.delete(bm,geom=removed,context='FACES_ONLY')
        dangling=[v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm,geom=dangling,context='VERTS')
        bm.to_mesh(clone.data);bm.free();clone.data.update()
        clone.data.materials[0]=material
        # No bevel or shell may recreate a rear transparent sheet.
        for modifier in list(clone.modifiers):clone.modifiers.remove(modifier)
        clone['surfaceScope']='One finite original outward pane and original UV per timber light; source profile/transforms retained.'
        src.hide_render=True;src.hide_set(True)
        changes.append(dict(source=name,owned=owned,family=family,sourceVertices=old_vertices,sourceFaces=old_faces,lights=len(groups),singleFaces=len(clone.data.polygons),frontNormals=list(normal)))
    for layer in bpy.context.scene.view_layers:layer.update()
    photo=ROOT/'data/建筑图片/SAW_Saw Swee Hock Student Centre/01_建筑实拍/architecture_round5_SAW_saw_909_01.jpg'
    return dict(addedObjects=NAMES,archivedObjects=SOURCES,changes=changes,
                sourcePhoto=str(photo.relative_to(ROOT)),sourcePhotoSha256=hashlib.sha256(photo.read_bytes()).hexdigest(),
                sourceURL='https://www.photography909.co.uk/saw-swee-hocklse-gallery',
                registrationProvenance='Accepted stage82/saw-curtain-audit.json facade normals; fixed constants verified against native165 front face normals',
                photographDate='Unknown; archive upload path2017 is not a current-condition survey',
                material=dict(name=material.name,webOpacity=.55,metallic=0,IOR=1.5,baseColor=list(shader.inputs['Base Color'].default_value),roughness=float(shader.inputs['Roughness'].default_value),nativeTransmission=float(shader.inputs['Transmission Weight'].default_value)),
                limitations=['Current native curtain outline/registration, timber frames, shading groups and pierced bricks retained; dimensions not surveyed.',
                            'Opacity and optics are visual estimates; finite single sheets approximate glazing without measured laminated/thick glass.',
                            'Existing internal staircase/back walls can be seen; full as-built floor enclosure and all rooms remain incomplete.'])
