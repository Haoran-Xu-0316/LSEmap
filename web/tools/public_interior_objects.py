"""Select the same supported public structure for fallback and detail exports.

The complete campus/exterior retains every geographic upper-floor component.
Dedicated public studies may have an authored level ceiling; detached patches
above that range must not leak in merely because their object names changed.
"""
import bpy
from mathutils import Vector


def public_interior_objects(record):
    code = record['code']
    collection = bpy.data.collections[record.get('interiorCollection', code + '_PUBLIC_INTERIOR_study')]
    objects = list(collection.all_objects)
    # A source-verified upper component can be added without reopening every
    # inherited detached floor above the public study's authored ceiling.
    additions = record.get('interiorAdditionalObjects', [])
    assert len(additions) == len(set(additions)), 'Duplicate public component identity'
    by_name = {obj.name: obj for obj in objects}
    assert set(additions) <= set(by_name), 'Additional public component is outside its authored collection'
    assert all(not by_name[name].hide_render for name in additions), 'Cannot publish an archived component'
    maximum = record.get('interiorDisplayMaxZ')
    if maximum is not None:
        objects = [obj for obj in objects if obj.name in additions or obj.type != 'MESH' or
                   min((obj.matrix_world @ Vector(corner)).z for corner in obj.bound_box) < maximum]
    if code == 'MAR':
        objects += [obj for obj in bpy.data.collections['MAR_EXTERIOR'].all_objects
                    if not obj.hide_render and (obj.get('publicInteriorComponent') or 'ground_glass_panes' in obj.name)]
    elif code == 'LRB':
        objects += [obj for obj in bpy.data.collections['LRB_EXTERIOR'].all_objects
                    if 'roof_' in obj.name or obj.get('sharedInteriorRoof')]
    return list(dict.fromkeys(objects))


def public_interior_display_group(code, obj):
    """Keep complete stair assemblies selectable without changing source geometry.

    SAW's height-only slices cut through adjacent flights and leave floating rail
    fragments. Public GLBs retain a few coherent nodes; campus/exterior exports
    remain merged. Other buildings keep their existing export structure.
    """
    if code != 'SAW':
        return None
    name = obj.name
    if name.startswith('SAW242_Flight3_'):
        return 'stair-3-4'
    if name.startswith('SAW242_Flight4_'):
        return 'stair-4-5'
    if name.startswith('SAW223_ST04_'):
        return 'stair-5-6'
    if name.startswith((
        'SAW242_Retained_', 'SAW233_Flight1_', 'SAW233_Flight2_', 'SAW233_Supported_stair_',
    )):
        return 'lower-stairs'
    if any(tag in name.lower() for tag in (
        'coordinated_floor', 'registered_floor', 'coordinated_shared_floor_landings',
    )) or name.startswith('SAW_SAW_floor_'):
        return 'floors'
    return 'public'
