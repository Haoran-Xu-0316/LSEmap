"""Bounded FAW/PAN attribution review; no unsupported facade replacement.
Call on an already loaded scene. This function does not open/save a blend.
"""
import bpy

SOURCE_URL = 'https://www.architectureplb.com/sectors/universities-and-colleges/lse-towers'

def apply_faw_exterior176():
    """Return the accurate no-change review outcome and source limitations."""
    assert bpy.data.collections.get('FAW_EXTERIOR'), 'Load campus175 before review'
    assert bpy.data.collections.get('PAN_EXTERIOR'), 'PAN attribution context required'
    return {
        'alreadyApplied': True,
        'addedObjects': [], 'archivedObjects': [], 'changedObjects': [],
        'status': 'review-only-no-photo-supported-whole-elevation-correction',
        'sourceURL': SOURCE_URL,
        'sourcePhotos': ['result/blender/faw_exterior156/sources/plb-entrance.jpg',
                         'data/建筑图片/FAW_Fawcett House/01_建筑实拍/tower_photos_round4_tower_round4_realm_p67_1.jpg'],
        'reviewScope': 'FAW full envelope, upper ribbon bands, materials, roof and PAN shared-entry ownership',
        'limitations': [
            'Architect project completion August2018 is not photograph capture date',
            'Official architect project describes shared Tower1/2 entrance and Tower3 ground-floor work; its full project photos do not register the complete FAW tower facade',
            'Existing FAW upper facade remains provisional; no2026survey or whole-building completion claim',
            'No shared PAN entrance or166glass parameters repeated on FAW',
        ],
    }
