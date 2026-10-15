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
    maximum = record.get('interiorDisplayMaxZ')
    if maximum is not None:
        objects = [obj for obj in objects if obj.type != 'MESH' or
                   min((obj.matrix_world @ Vector(corner)).z for corner in obj.bound_box) < maximum]
    if code == 'MAR':
        objects += [obj for obj in bpy.data.collections['MAR_EXTERIOR'].all_objects
                    if 'ground_glass_panes' in obj.name]
    elif code == 'SAW':
        objects = [obj for obj in objects if '_floor_' not in obj.name or 'landing' in obj.name]
    elif code == 'LRB':
        objects += [obj for obj in bpy.data.collections['LRB_EXTERIOR'].all_objects
                    if 'roof_' in obj.name or obj.get('sharedInteriorRoof')]
    return list(dict.fromkeys(objects))
