"""Reduce the photographed OLD entrance glass veil without altering joinery.

Apply to the loaded campus. Existing public-foyer geometry and all original
materials remain. Optical values are visual estimates from a private reference.
"""
from pathlib import Path
import hashlib
import bpy
ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'OLD_NEXT_GLAZING172_single_door_panes'
TARGET = 'OLD_ENTRANCE192_single_glass'
COLOUR = (.15, .18, .18, 1)
OPACITY = .28


def apply_old_entrance_optics():
    if bpy.data.objects.get(TARGET):
        return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[])
    source = bpy.data.objects[SOURCE]
    assert not source.hide_render and len(source.data.vertices) == 32 and len(source.data.polygons) == 8
    assert len(source.data.materials) == 1
    material = source.data.materials[0].copy()
    material.name = 'OLD_ENTRANCE192_clear_glass'
    material.diffuse_color = COLOUR
    material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = COLOUR
    material['webOpacity'] = OPACITY
    material['webClosedGlazing'] = False
    material['opticalScope'] = 'Eight existing entrance panes; estimated neutral tint and face-on opacity; no measured specification'
    target = source.copy()
    target.data = source.data.copy()
    target.name = TARGET
    target.data.name = TARGET
    target.data.materials[0] = material
    for collection in source.users_collection:
        collection.objects.link(target)
    target.hide_render = False
    target.hide_set(False)
    source.hide_render = True
    source.hide_set(True)
    photo = ROOT / 'data/collections/old-user-reference/houghton-entrance-user-20261002.png'
    return dict(alreadyApplied=False, addedObjects=[TARGET], archivedObjects=[SOURCE], changedObjects=[],
                paneCount=8, colour=list(COLOUR), browserOpacity=OPACITY,
                priorOpacity=float(source.data.materials[0]['webOpacity']),
                reference=dict(path=str(photo.relative_to(ROOT)), sha256=hashlib.sha256(photo.read_bytes()).hexdigest(), captureDate='unknown'),
                scope='Neutral clearer Houghton Street door panes; geometry, corner UVs, roughness, transmission, frames and existing foyer retained',
                audit='result/blender/old-exterior-colour-review/door-rays.json',
                limitations=['Optics are visual estimates, not calibrated measurements',
                             'Foyer representation uses historical photographs; complete current interior remains unverified',
                             'Relief anatomy, upper and unseen elevations remain unfinished'])
