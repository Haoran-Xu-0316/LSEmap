"""Review CON against its available, explicitly attributed exterior evidence.

No source is opened/saved and no component is authored from unresolved imagery.
The current official image is an entrance crop. It cannot establish all upper
window rows, corner profiles, roof, or a replacement inner-door subdivision.
"""
from pathlib import Path
import hashlib
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE_URL = 'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate'
PHOTO = 'data/建筑图片/CON_Connaught House/01_建筑实拍/exteriors_lse_estate_005.jpg'
ORIGIN = (-16.17835807800293, -130.22201538085938, 0)
RIGHT = (-0.9859890937805176, -0.16680996119976044, 0)
OUTWARD = (0.16680996119976044, -0.9859890937805176, 0)


def review_con_exterior167():
    """Return exact current exterior inventory and bounded photographic coverage."""
    origin,right,outward=map(Vector,[ORIGIN,RIGHT,OUTWARD]);inventory=[]
    for obj in bpy.data.collections['CON_EXTERIOR'].all_objects:
        if obj.type!='MESH' or obj.hide_render:continue
        points=[obj.matrix_world@v.co for v in obj.data.vertices]
        if not points:continue
        local=[Vector(((p-origin).dot(right),(p-origin).dot(outward),p.z))for p in points]
        inventory.append(dict(name=obj.name,vertices=len(obj.data.vertices),faces=len(obj.data.polygons),
                              localBounds=[[min(p[i]for p in local)for i in range(3)],[max(p[i]for p in local)for i in range(3)]],
                              materialSlots=[m.name if m else None for m in obj.data.materials]))
    assert inventory
    return dict(status='reviewed-no-photographically-proven-group-change',addedObjects=[],archivedObjects=[],changedObjects=[],
                sourcePhoto=PHOTO,sourcePhotoSha256=hashlib.sha256((ROOT/PHOTO).read_bytes()).hexdigest(),sourceURL=SOURCE_URL,
                photographDate='unknown',resolution=[300,400],registration=dict(origin=ORIGIN,right=RIGHT,outward=OUTWARD,basis='Existing native/GIS estimate, not surveyed'),
                visibleObjects=inventory,
                review=dict(entrance='Photo-supported open vestibule, lower granite/upper limestone division and compact four-light window already modelled.',
                            upperFacade='Full-height attributed facade photograph unavailable; current repeated upper windows cannot be certified or changed from this entrance crop.',
                            roof='No visible roof in attributed source; native roof/cornice estimate retained without claiming current-condition accuracy.',
                            innerDoor='Low-resolution reflections/interior background obscure subdivision; no guessed extra crossbar.',
                            glazing='Legacy metallic response already corrected166; no transparency increase without a verified enclosure.'),
                sourcesReviewed=[dict(url=SOURCE_URL,coverage='Official entrance-only image unchanged'),
                                 dict(url='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf',coverage='Official entry repeats the entrance crop; no full facade/roof'),
                                 dict(url='https://www.accessable.co.uk/london-school-of-economics/access-guides/connaught-house',coverage='403 inaccessible2026-10-07; no image inferred'),
                                 dict(url='https://prewett-bizley.squarespace.com/-lse-index',coverage='2010 feasibility proposal, not proof of completed current envelope')],
                limitations=['Native window/storey layout and roof remain estimates awaiting a clear registered complete exterior photograph.',
                             'Current photos are undated;2026 publication/access date does not prove2026 capture.',
                             'This review deliberately changes no geometry, colour, material, UV, transform or room.'])
