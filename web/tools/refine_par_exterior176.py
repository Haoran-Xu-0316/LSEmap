"""Read-only full PAR frontage review against archived official built imagery.
Operates on an already loaded campus; never opens or saves a complete blend.
"""
import bpy

SOURCE_URL='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Cap-Dev/2015-Parish-Hall.pdf'
PHOTO='data/建筑图片/PAR_Parish Hall/01_建筑实拍/small_round5_PAR-001.jpg'

def apply_par_exterior176():
    assert bpy.data.collections.get('PAR_EXTERIOR'), 'Load campus175 first'
    return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[],
        status='review-only-no-confirmed-group-facade-error',sourceURL=SOURCE_URL,
        sourcePhotos=[PHOTO,'data/建筑图片/PAR_Parish Hall/01_建筑实拍/exteriors_lse_estate_021.jpg'],
        reviewScope='Whole photographed street frontage, brick arches, window groups, entrance and visible roof slope',
        correspondence={'upperWindowGroups':4,'lowerBrickArches':4,'dormers':4,'roofCowls':2,'entranceDoorFields':2},
        limitations=['2015project record is not a2026survey; photograph capture date unspecified',
        'Photo-supported elements already represented by66and120components',
        'Rear roof and side/back window layout not fully attributable from the main-frontage image',
        'Existing dimensions, exact masonry pigment and detailed joinery remain estimates'])
