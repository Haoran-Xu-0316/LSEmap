"""Complete the photographed Houghton entrance pair with one small bollard.

The additional position is estimated from the paired-post photograph and the
native street width, not a new OSM observation or accessibility survey. Existing
165 mapped post,167 covers/trees, all paving and OLD access geometry stay intact.
"""
from pathlib import Path
import math,hashlib
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OWNED='SITE169_Houghton_second_cast_iron_bollard'
SOURCE='SITE165_Houghton_cast_iron_bollard'
PHOTO='data/collections/public-realm-2026/user-references/reference-09.png'
FIRST=Vector((1.0343516393182428,-91.20939382992195,0))
# From the mapped first post toward the photographed CBG-side post. The gap is
# deliberately retained rather than introducing a solid cross-street barrier.
ACROSS=Vector((.887461,-.460884,0)).normalized()
CENTRE=FIRST+ACROSS*2.4


def apply_street_details169():
    if bpy.data.objects.get(OWNED):
        return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[]}
    scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
    for layer in scene.view_layers:layer.update()
    deps=bpy.context.evaluated_depsgraph_get()
    ground=scene.ray_cast(deps,CENTRE+Vector((0,0,1.6)),Vector((0,0,-1)),distance=2)
    assert ground[0] and ground[4].name in ('SITE167_Houghton_paving_with_cover_openings','SITE_V48_Houghton_Street'), ('Expected retained Houghton surface',ground[4].name if ground[0] else None)
    assert abs(ground[1].z-.05)<.001
    source=bpy.data.objects[SOURCE]
    obj=source.copy();obj.data=source.data.copy();obj.name=OWNED;obj.data.name=OWNED+'_mesh'
    obj.location+=CENTRE-FIRST+Vector((0,0,.001))
    # Source165 has no UV map. The owned copy receives a cylindrical metric map,
    # without changing a single source vertex, polygon or material binding.
    uv=obj.data.uv_layers.new(name='MetricUV')
    for face in obj.data.polygons:
        for index in face.loop_indices:
            p=obj.data.vertices[obj.data.loops[index].vertex_index].co
            uv.data[index].uv=(math.atan2(p.y-FIRST.y,p.x-FIRST.x)/math.tau,p.z)
    obj['reference']=PHOTO;obj['sourcePhotoSha256']=hashlib.sha256((ROOT/PHOTO).read_bytes()).hexdigest()
    obj['positionStatus']='Photo-estimated second post; mapped first post retained unchanged'
    obj['dimensionsEstimated']=True
    obj['scope']='One missing paired Houghton post; no street survey or accessibility compliance claim'
    bpy.data.collections['03_PUBLIC_REALM'].objects.link(obj)
    return {'alreadyApplied':False,'addedObjects':[OWNED],'archivedObjects':[],'changedObjects':[],
            'center':[CENTRE.x,CENTRE.y],'groundSurface':ground[4].name,'groundHeight':ground[1].z,
            'pairCenterSpacingEstimate':2.4,'pairClearGapEstimate':2.224,
            'photoReference':PHOTO,'photoDate':'Unknown; user-supplied photograph',
            'limitations':['Second-post location is estimated; only first location comes from archived OSM.',
                           'Pair width and cast-iron profile dimensions are estimates, not a measured access-width survey.',
                           'No existing road, cover, tree, bollard, railing or building is replaced.']}
