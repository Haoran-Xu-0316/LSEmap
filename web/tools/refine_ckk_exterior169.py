"""Read-only CKK principal-elevation review; no unsupported geometry revision.

The archived Grimshaw and Willebrand photographs already correspond to the
retained corrected wing apertures, mansard windows, curved hoods and154 fanlight.
No measured or dated evidence establishes a further exterior correction here.
"""
from pathlib import Path
import bpy,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
ORIGIN=Vector((-110.49102020263672,77.56015014648438,0))
NORMAL=Vector((.9271838665008545,.37460657954216003,0))
AXIS=Vector((-NORMAL.y,NORMAL.x,0))
PHOTOS=[
 'data/建筑图片/CKK_Cheng Kin Ku Building/01_建筑实拍/exteriors_ckk_grimshaw_010.jpg',
 'data/建筑图片/CKK_Cheng Kin Ku Building/01_建筑实拍/library_round5_library_round5_CKK_8f06506667f1.jpg',
]

def review_ckk_exterior169():
    collection=bpy.data.collections['CKK_EXTERIOR']
    visible=[o for o in collection.all_objects if o.type=='MESH'and not o.hide_render]
    assert all(bpy.data.objects[name]in visible for name in [
        'CKK_NEXT_ENVELOPE_recessed_glass','CKK_NEXT_PEDIMENT_curved_stone',
        'CKK_NEXT_FRONTAGE154_semicircular_glass','CKK_V32_dormer_glazing',
        'CKK_RAINWATER159_downpipes'])
    dormers=bpy.data.objects['CKK_V32_dormer_glazing']
    assert len(dormers.data.vertices)==18*8 and len(dormers.data.polygons)==18*6
    fan=bpy.data.objects['CKK_NEXT_FRONTAGE154_semicircular_glass']
    points=[fan.matrix_world@v.co for v in fan.data.vertices]
    assert abs(min(v.z for v in points)-5.3)<1e-4
    assert abs(max(v.z for v in points)-6.65)<1e-4
    trees=[]
    for o in visible:
        if o.data.polygons:
            trees.append((o.name,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(p.vertices)for p in o.data.polygons])))
    probes=[]
    for lateral,height in [(0,5.8),(-.55,5.7),(.55,5.7)]:
        start=ORIGIN+NORMAL*24.5+AXIS*lateral+Vector((0,0,height));hits=[]
        for name,tree in trees:
            hit=tree.ray_cast(start,-NORMAL,4)
            if hit[0]is not None:hits.append(dict(object=name,distance=hit[3]))
        hits.sort(key=lambda h:h['distance'])
        assert hits and hits[0]['object']==fan.name
        probes.append(dict(lateral=lateral,height=height,firstSurface=hits[0]))
    return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[],
        status='reviewed-no-evidence-supported-change',visibleExteriorMeshCount=len(visible),
        dormerCount=18,fanlightSpringEstimate=5.3,fanlightRadiusEstimate=1.35,fanlightProbes=probes,
        references=[dict(file=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest())for p in PHOTOS],
        sourceURLs=['https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/',
                    'https://www.willebrand.com/en/projects/lse-london-school-of-economics-grimshaw-architects.398'],
        photographDate='unknown',limitations=[
            'Principal-elevation geometry corresponds to two archived built photographs; this is not a claim of measured whole-building fidelity.',
            'Retained sizes and registrations are photographic/native estimates, not a survey.',
            'No measured current colour target, new dated glazing/door specifications or rear-elevation survey supports further changes.',
            'No new geometry means no new box normals, UVs, alpha layers or collision surfaces. Original topology, UV and materials remain untouched.'])

def apply_ckk_exterior169():
    """Integration-compatible no-op: current photo-supported exterior retained."""
    return review_ckk_exterior169()
