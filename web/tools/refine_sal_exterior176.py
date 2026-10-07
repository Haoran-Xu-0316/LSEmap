"""SAL176 read-only exterior review: no justified grouped replacement found.

The existing principal elevation has eighteen corrected four-light windows,
six two-light small gable windows, three projected oriels, and the two revised
front tower roofs. The apparent third gable light in a distant render was fine
blue joinery: connected native parts confirm one stone central mullion.

Evidence is the archived LSE Estates image and Jestico + Whiles built photo.
Photo capture dates are unknown; project-era photos do not establish 2026
conditions. Dimensions and unobserved elevations remain estimates. No geometry,
UV, material, matrix, collection or visibility is mutated by this review.
"""
import bpy

REVIEW_SCOPE = ('SAL principal street elevation: brick/stone hierarchy, 18 four-light '
                'upper main windows, 6 two-light small gable windows, projected '
                'oriels, front twin tower roofs and historic central entrance. '
                'No replacement warranted by reviewed photographs; unobserved rear excluded.')
SOURCE_URLS = [
    'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/32L-300x400.jpg',
    'https://www.jesticowhiles.com/project/lincolns-inn-fields-london-school-of-economics/',
    'https://www.jesticowhiles.com/wp-content/uploads/2024/01/Lincolns-Inn-Fields-LSE-Project-Images-008-2048x1768.jpg',
]

def apply_sal_exterior176():
    """Validate loaded collection and return a truthful, repeatable no-op."""
    if not bpy.data.collections.get('SAL_EXTERIOR'):
        raise ValueError('Load the campus containing SAL_EXTERIOR before this review.')
    return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[])
