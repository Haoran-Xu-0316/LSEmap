"""Remove metallic response from existing LRB window glass batches.

Photographs support reflective dielectric panes. Opaque proxy panes remain opaque
where no registered room exists; this pass does not revive rejected transparency.
"""
import bpy

SOURCES = ('LRB_D5_roof109_glass', 'LRB_D5_portugal110_glass',
           'LRB_D5_portugal110_roof_glass', 'LRB_D5_carey117_glass')
PREFIX = 'LRB_EXTERIOR172_'


def apply_lrb_exterior172():
    """Clone four batches in the loaded scene; never open or save the campus."""
    names = [PREFIX + source.removeprefix('LRB_') for source in SOURCES]
    if all(name in bpy.data.objects for name in names):
        return dict(alreadyApplied=True, addedObjects=names,
                    archivedObjects=list(SOURCES), changedObjects=[])
    if any(name in bpy.data.objects for name in names):
        raise RuntimeError('Incomplete LRB172 component already present')
    sources = [bpy.data.objects[name] for name in SOURCES]
    replacements = {}
    for source, name in zip(sources, names):
        clone = source.copy()
        clone.data = source.data.copy()
        clone.name = name
        clone.data.name = name
        for collection in source.users_collection:
            collection.objects.link(clone)
        for index, material in enumerate(source.data.materials):
            if material is None:
                continue
            if material.name not in replacements:
                replacement = material.copy()
                replacement.name = PREFIX + material.name
                shader = next(n for n in replacement.node_tree.nodes
                              if n.type == 'BSDF_PRINCIPLED')
                shader.inputs['Metallic'].default_value = 0.0
                shader.inputs['Roughness'].default_value = 0.22
                shader.inputs['IOR'].default_value = 1.5
                replacement['opticalEstimate'] = 'Dielectric reflective proxy; no surveyed optical specification'
                replacements[material.name] = replacement
            clone.data.materials[index] = replacements[material.name]
        clone.hide_render = False
        clone.hide_viewport = False
        clone.hide_set(False)
        source.hide_render = True
        source.hide_set(True)
    return dict(alreadyApplied=False, addedObjects=names,
                archivedObjects=list(SOURCES), changedObjects=[])
