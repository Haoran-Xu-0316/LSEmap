"""Unify OLD dielectric glazing and remove duplicate entrance-pane depth.

Only source glass bindings and an archived copy of the existing door panes are
changed. Photographs support clear entrance glass; optical values remain estimates.
The callable never opens or saves the whole campus.
"""
from pathlib import Path
import json,hashlib
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
DOOR='OLD_NEXT_EXTERIOR154_door_glass'
OWN='OLD_NEXT_GLAZING172_single_door_panes'
GLASS_MATERIALS={'OLD_V78_glass','OLD_V112_glass','OLD_V113_glass','OLD_NEXT_OLD_NEXT_GLAZING152_neutral_glass'}
PHOTO='data/collections/old-user-reference/houghton-entrance.png'


def apply_old_glass172():
    if OWN in bpy.data.objects:
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    collection=bpy.data.collections['OLD_EXTERIOR']
    source=bpy.data.objects[DOOR]
    assert not source.hide_render and len(source.data.vertices)==64 and len(source.data.polygons)==48
    outward=Vector(json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text())['outward'])
    faces=[]
    for first in range(0,48,6):
        face=max(source.data.polygons[first:first+6],key=lambda p:(source.matrix_world.to_3x3()@p.normal).dot(outward))
        assert (source.matrix_world.to_3x3()@face.normal).normalized().dot(outward)>.95
        faces.append(face)
    mesh=bpy.data.meshes.new(OWN+'_mesh')
    used=sorted({index for face in faces for index in face.vertices});mapping={old:new for new,old in enumerate(used)}
    mesh.from_pydata([tuple(source.data.vertices[i].co) for i in used],[],[tuple(mapping[i] for i in p.vertices) for p in faces]);mesh.update()
    for old_layer in source.data.uv_layers:
        layer=mesh.uv_layers.new(name=old_layer.name)
        for polygon,old in zip(mesh.polygons,faces):
            for new_index,old_index in zip(polygon.loop_indices,old.loop_indices):layer.data[new_index].uv=old_layer.data[old_index].uv
    material=source.data.materials[0].copy();material.name='OLD172_clear_dielectric_door_glass'
    shader=material.node_tree.nodes['Principled BSDF'];shader.inputs['Metallic'].default_value=0
    material['scope']='Existing tint/roughness/transmission retained; one entrance pane surface, not two closed faces'
    mesh.materials.append(material)
    clone=source.copy();clone.data=mesh;clone.name=OWN;collection.objects.link(clone)
    clone['originalObject']=DOOR;clone['sourcePhoto']=PHOTO
    source.hide_render=True;source.hide_set(True)
    mats={};changed=[]
    for obj in collection.all_objects:
        if obj.type!='MESH' or obj.hide_render or obj==clone:continue
        did_change=False
        for index,old in enumerate(obj.data.materials):
            if not old or old.name not in GLASS_MATERIALS:continue
            if old.name not in mats:
                new=old.copy();new.name='OLD172_dielectric_'+old.name
                new.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=0
                new['scope']='Dielectric response only; original colour, roughness and alpha preserved'
                mats[old.name]=new
            obj.data.materials[index]=mats[old.name];did_change=True
        if did_change:changed.append(obj.name)
    assert len(mesh.polygons)==8 and sum(len(p.vertices)-2 for p in mesh.polygons)==16
    return dict(alreadyApplied=False,addedObjects=[clone.name],archivedObjects=[source.name],changedObjects=changed,
        singlePaneCount=8,retainedDoorAlpha=float(material.get('webOpacity',.3)),doorTintPreserved=True,
        glassBindingsCorrected=len(changed),copiedMaterials=[m.name for m in mats.values()]+[material.name],
        reference=dict(path=PHOTO,sha256=hashlib.sha256((ROOT/PHOTO).read_bytes()).hexdigest(),captureDate='unknown'),
        limitations=['Glass optics are visual estimates, not measured specifications.','No opening, joinery, unseen interior or building dimensions changed.','Original closed door object remains archived.'])
