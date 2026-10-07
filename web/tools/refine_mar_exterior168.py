"""Correct MAR glass families without changing native registered openings or concrete.

North-screen and courtyard photos support reflective dielectric glazing. Only
one retained ground-floor north pane and the two entry leaves receive alpha:
native rays establish existing hall structures behind these exact surfaces.
No new rooms, upper apertures or guessed rear transparency are authored.
"""
from pathlib import Path
import hashlib
import bpy,bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
SOURCES=[
    'MAR_NEXT_ENVELOPE_north_three_row_glass',
    'MAR_NEXT_PANEL_retained_00_V115_retained_D5_wings75_glass',
    'MAR_NEXT_LETTER165_retained_00_glass',
    'MAR_D5_entry_door_glass',
]
NAMES=[
    'MAR_EXTERIOR168_north_screen_dielectric_glass',
    'MAR_EXTERIOR168_wing_dielectric_glass',
    'MAR_EXTERIOR168_retained_glass_and_north_hall_pane',
    'MAR_EXTERIOR168_single_surface_entry_glass',
]
# Current north GIS registration. Face213 is inherited165's large north hall
# pane; the165 removed blank bay remains separate and completely untouched.
NORTH=Vector((-.37025192379951477,.9289313554763794,0))
NORTH_HALL_FACE=213
DOOR_FRONT_FACES=[3,9]
PHOTOS=[
 'data/建筑图片/MAR_Marshall Building/01_建筑实拍/exteriors_mar_archdaily_000.jpg',
 'data/建筑图片/MAR_Marshall Building/01_建筑实拍/exteriors_mar_archdaily_001.jpg',
 'data/collections/architecture_round5/images/MAR/MAR_mar_kane_01.jpg',
]

def glass_material(source,name,alpha=1):
    material=source.copy();material.name=name
    shader=next(node for node in material.node_tree.nodes if node.type=='BSDF_PRINCIPLED')
    # A glass surface is dielectric; photographic tint is inherited rather than
    # interpreted as calibrated RGB. Unknown rooms retain opaque reflections.
    shader.inputs['Metallic'].default_value=0
    shader.inputs['Transmission Weight'].default_value=.8 if alpha<1 else 0
    shader.inputs['Roughness'].default_value=.15
    shader.inputs['IOR'].default_value=1.5
    shader.inputs['Alpha'].default_value=alpha
    material.diffuse_color=(*material.diffuse_color[:3],alpha)
    material.use_backface_culling=False
    if alpha<1:
        material['webOpacity']=alpha
        material.surface_render_method='DITHERED'
        material.show_transparent_back=False
    return material

def apply_mar_exterior168():
    if all(bpy.data.objects.get(name)for name in NAMES):
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    assert not any(bpy.data.objects.get(name)for name in NAMES),'Partial MAR168 component'
    collection=bpy.data.collections['MAR_EXTERIOR']
    for name in SOURCES:assert bpy.data.objects[name].type=='MESH'and not bpy.data.objects[name].hide_render
    source=bpy.data.objects[SOURCES[2]]
    assert len(source.data.polygons)==250
    pane=source.data.polygons[NORTH_HALL_FACE]
    assert abs(pane.center.z-1.95)<.001 and abs(pane.area-44.8)<.05
    replacements=[];materials=[]
    for index,(source_name,name)in enumerate(zip(SOURCES,NAMES)):
        original=bpy.data.objects[source_name]
        replacement=original.copy();replacement.data=original.data.copy()
        replacement.name=name;replacement.data.name=name;collection.objects.link(replacement)
        for slot,material in enumerate(original.data.materials):
            new=glass_material(material,f'MAR168_{index:02d}_{slot:02d}_dielectric',alpha=.55 if index==3 else 1)
            replacement.data.materials[slot]=new;materials.append(new.name)
        if index==2:
            clear=glass_material(original.data.materials[pane.material_index],'MAR168_north_ground_hall_visible_glass',alpha=.55)
            replacement.data.materials.append(clear);replacement.data.polygons[NORTH_HALL_FACE].material_index=len(replacement.data.materials)-1;materials.append(clear.name)
        if index==3:
            assert len(original.data.vertices)==16 and len(original.data.polygons)==12
            bm=bmesh.new();bm.from_mesh(replacement.data);bm.faces.ensure_lookup_table()
            keep={bm.faces[i]for i in DOOR_FRONT_FACES}
            bmesh.ops.delete(bm,geom=[f for f in bm.faces if f not in keep],context='FACES_ONLY')
            bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
            bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
            for face in bm.faces:
                world_normal=(replacement.matrix_world.to_3x3().inverted().transposed()@face.normal).normalized()
                if world_normal.dot(NORTH)<0:bmesh.ops.reverse_faces(bm,faces=[face])
            bm.to_mesh(replacement.data);bm.free();replacement.data.update()
            assert len(replacement.data.vertices)==8 and len(replacement.data.polygons)==2
        replacement['scope']='MAR glass finish; fixed native aperture geometry. Only verified hall pane and two entry leaves transparent.'
        original.hide_render=True;original.hide_set(True);replacements.append(replacement)
    for layer in bpy.context.scene.view_layers:layer.update()
    return dict(alreadyApplied=False,addedObjects=NAMES,archivedObjects=SOURCES,changedObjects=[],
        hallPaneFace=NORTH_HALL_FACE,doorSourceFrontFaces=DOOR_FRONT_FACES,
        newMaterials=materials,alpha=.55,glassMetallic=0,
        references=[dict(file=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest())for p in PHOTOS],
        sourceURLs=['https://www.archdaily.com/977225/london-school-of-economics-marshall-building-grafton-architects','https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/'],
        photographDate='Capture date unknown; publication does not prove photographic capture date.',
        limitations=['Colour is not calibrated against a measured colour target; retained native tints and concrete unchanged.',
                    'Inherited native/GIS scales remain estimates, not a measured survey; opacity.55 is a visual approximation rather than tested optical transmittance.',
                    'Only existing public-hall-backed north glazing and two entry leaves express transparency; no fabricated rooms or backing panels.',
                    'The165 north blank ground bay/name, registered native envelope, upper fin distribution, wings and rear opening layout unchanged.'])
