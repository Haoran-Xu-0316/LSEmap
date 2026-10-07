"""Read-only CBG circulation/void audit on the retained complete campus.

Existing native tower stairs already lie outside the full floor-plate footprint.
Published2015 planning and historical individual-room plans cannot establish a
measured built whole-floor re-layout. Retain the current structure accordingly.
"""
from pathlib import Path
import bpy,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
COLLECTION='CBG_PUBLIC_INTERIOR_study'
FLOOR='CBG_D_tower_floor_plates'
STAIRS='CBG_D_tower_meandering_stair_treads'
PHOTOS=[
 'data/建筑图片/CBG_Centre Building/01_建筑实拍/exteriors_cbg_rshp_025.jpg',
 'data/建筑图片/CBG_Centre Building/01_建筑实拍/exteriors_cbg_rshp_023.jpg',
]

def review_cbg_structure170():
    collection=bpy.data.collections[COLLECTION]
    def descendants(parent):
        return [parent]+[item for child in parent.children for item in descendants(child)]
    assert collection in descendants(bpy.data.scenes['00_CAMPUS_COMPLETE'].collection)
    assert all('EXTERIOR'not in c.name for o in collection.all_objects for c in o.users_collection)
    floor=bpy.data.objects[FLOOR];stairs=bpy.data.objects[STAIRS]
    assert FLOOR in collection.all_objects and STAIRS in collection.all_objects
    assert len(floor.data.vertices)==12*8 and len(stairs.data.vertices)==216*8
    tree=BVHTree.FromPolygons([floor.matrix_world@v.co for v in floor.data.vertices],[tuple(p.vertices)for p in floor.data.polygons])
    probes=[]
    for i in range(216):
        points=[stairs.matrix_world@v.co for v in stairs.data.vertices[i*8:i*8+8]]
        center=sum(points,Vector())/8+Vector((0,0,.081))
        hit=tree.ray_cast(center,Vector((0,0,1)),60)
        assert hit[0]is None,'Existing tower floor obstructs stair opening'
        probes.append(dict(tread=i,point=list(center),towerSlabAbove=False))
    return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[],
        status='reviewed-no-evidence-supported-structure-change',productionInteriorCollection=COLLECTION,
        separateFromExterior=True,counts=dict(towerFloors=12,towerStairTreads=216,towerLandings=9,academicStairFlights=3),
        towerVoidProbes=probes,
        references=[dict(file=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),captureDate='unknown')for p in PHOTOS],
        sourceURL='https://rshp.com/projects/education/lse-centre-building/',
        planEvidence=['2015 planning material is design-stage rather than certified whole-floor as-built.',
                      'Archived LSE room plans identify individual historical teaching rooms, not registered whole-floor circulation.'],
        limitations=['The216 centerline upward probes establish no obstruction by the tower floor plates; they are not a complete headroom/safety certification.',
                     'Inherited stair dimensions, floor levels, bridges and registration remain estimates; hidden cores and current whole-floor room layouts unverified.',
                     'No new structure or duplicated exterior meshes authored; original geometry, UV and material bindings retained.'])

def apply_cbg_structure170():
    """Integration-compatible no-op; no new furniture or fabricated floor plates."""
    return review_cbg_structure170()
