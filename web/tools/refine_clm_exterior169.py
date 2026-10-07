"""Finite CLM exterior audit, with no unsupported model changes.

The available estate photograph registers the side portal only; older whole
building photos survive as provenance records but their image files are absent.
No additional photo-supported geometric error was established in this review.
"""


def apply_clm_exterior169():
    """Return an idempotent no-op; never load, save or mutate a Blender scene."""
    return {
        'alreadyApplied': True,
        'addedObjects': [],
        'archivedObjects': [],
        'changedObjects': [],
        'auditOnly': True,
        'reason': 'No additional exterior error established from available local photographs',
        'sourceFile': 'data/建筑图片/CLM_Clement House/01_建筑实拍/exteriors_lse_estate_003.jpg',
        'photographCaptureDate': 'unknown',
        'limitations': [
            'Estate photograph covers a side entrance, not the complete convex street facade',
            '2018-04-24 and2023-11-15 whole-building image files are absent; their indices are not new visual proof',
            'Rotunda photograph is an interior taken2016-10-13 and uploaded2016-10-20',
            'No latest2026 facade, calibrated colour, sculptural scan or complete roof claim',
        ],
    }
