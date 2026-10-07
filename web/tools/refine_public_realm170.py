"""Read-only Portugal Street and John Watkins Plaza evidence audit.

No supported whole-surface replacement was established. Do not implement the
2026 design competition as a finished street, or extrapolate a historic oblique
plaza photograph into surveyed boundary geometry. This function never changes
objects, materials, UVs, visibility, scenes, or the native file.
"""
import math
import bpy

TARGETS=('00_SITE_Road_Portugal Street','00_SITE_Road_Portugal Street.001','SITE_V47_John_Watkins_Plaza')


def audit_public_realm170():
    surfaces=[]
    for name in TARGETS:
        obj=bpy.data.objects[name]
        points=[obj.matrix_world@v.co for v in obj.data.vertices]
        surfaces.append({'object':name,'vertices':len(points),'faces':len(obj.data.polygons),
                         'heights':sorted({round(p.z,5) for p in points}),
                         'materials':[m.name for m in obj.data.materials],
                         'uvLayers':len(obj.data.uv_layers),
                         'allExistingUVFinite':all(math.isfinite(v) for uv in obj.data.uv_layers for p in uv.data for v in p.uv)})
    return {'alreadyApplied':False,'status':'readOnlyAudit','addedObjects':[],
            'archivedObjects':[],'changedObjects':[],'surfaces':surfaces,
            'findings':['Portugal has asphalt carriageway and pale footway; no completed2026 pedestrianisation inferred.',
                        'John Watkins has a detailed slab surface;2021 photographs show low brick boundaries and level changes, but their full native registration and current condition remain unverified.'],
            'decision':'No geometry or material replacement; historical plaza boundary remains a documented follow-up requiring reliable registration.',
            'sources':[{'path':'data/collections/streets/raw/public_realm_strategy_2022.pdf','url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/2022-LSE-Public-Realm-Strategy.pdf','pages':[14,75],'photoDate':'Site Photography MCMA2021'},
                       {'path':'data/collections/streets/raw/portugal_street_2026.html','url':'https://www.lse.ac.uk/news/latest-news-from-lse/lse-portugal-street-landscaping','publicationDate':'2026-03-26','siteStartForecast':'2028; proposed work, not completed condition'}]}


def apply_public_realm170():
    """Compatibility entrypoint: an audit-only report, with zero mutations."""
    return audit_public_realm170()
