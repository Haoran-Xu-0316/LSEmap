"""Close the documented lower-ground atrium floor in a separate LRB study.

Callable from Blender. Does not open or save the campus, alter original objects,
recreate the stair, or certify a current whole-building survey. The existing
public roof remains supplied by the production exporter.
"""
import math
import bpy
from mathutils import Vector

COLLECTION = 'LRB_PUBLIC_INTERIOR168_study'
CENTRE = (75.593385, 13.262314)
SOURCE_COLLECTION = 'LRB_PUBLIC_INTERIOR_study'


def _signed_volume(mesh):
    mesh.calc_loop_triangles()
    return sum(mesh.vertices[t.vertices[0]].co.dot(mesh.vertices[t.vertices[1]].co.cross(mesh.vertices[t.vertices[2]].co))/6 for t in mesh.loop_triangles)


def _base_slab(collection):
    # The current 6-floor slab leaves the same 9.8m void at LG. Only LG closes.
    n = 96
    radius, bottom, top = 9.8, -4.0, -3.68
    vertices = [(CENTRE[0]+radius*math.cos(2*math.pi*i/n), CENTRE[1]+radius*math.sin(2*math.pi*i/n), z) for z in (bottom,top) for i in range(n)]
    faces = [tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh = bpy.data.meshes.new('LRB168_LG_atrium_foundation_mesh')
    mesh.from_pydata(vertices,[],faces); mesh.update()
    assert _signed_volume(mesh)>0, 'New base slab must have outward winding'
    uv = mesh.uv_layers.new(name='SurfaceUV')
    for face in mesh.polygons:
        for index in face.loop_indices:
            p=mesh.vertices[mesh.loops[index].vertex_index].co
            uv.data[index].uv=(p.x,p.y) if abs(face.normal.z)>.5 else (p.x+p.y,p.z)
    mesh.materials.append(bpy.data.materials['ATRIA_white'])
    obj = bpy.data.objects.new('LRB168_LG_atrium_foundation',mesh)
    obj['floorId']='LG'; obj['structuralRole']='Lower-ground terminal floor, not an upper-storey atrium infill'
    obj['dimensionsEstimated']=True; obj['sourcePlanPage']=2
    collection.objects.link(obj)
    return obj


def apply_lrb_interior168():
    existing = bpy.data.collections.get(COLLECTION)
    if existing:
        return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[], 'interiorCollection':COLLECTION}
    source = bpy.data.collections[SOURCE_COLLECTION]
    target = bpy.data.collections.new(COLLECTION)
    target['baselineCollection']=SOURCE_COLLECTION
    target['sourcePlan']='data/documents/library_floor_plans.pdf page 2, lower ground'
    target['sourcePhoto']='data/collections/library_round5/photos/LRB_9cf4d6340481.jpg'
    target['photoDate']='2001 project; photograph date unknown'
    target['scope']='Existing six-floor study retained; lower-ground atrium supporting slab corrected. Estimated dimensions, not a 2026 survey.'
    clones=[]; originals={}
    for old in source.all_objects:
        new=old.copy()
        if old.data: new.data=old.data.copy()
        new.name='LRB168__'+old.name
        new['originalObject']=old.name
        target.objects.link(new); clones.append(new); originals[old]=new
    for old,new in originals.items():
        if old.parent in originals:new.parent=originals[old.parent]
    # Carpet starts below the LG circulation floor in the baseline. Raise only
    # this independent cloned surface to match the existing gallery carpet datum.
    carpet=next(o for o in clones if o.get('originalObject')=='LRB_central_blue_carpet')
    carpet.location.z+=.022
    carpet['correctedSurfaceZ']=-3.668
    base=_base_slab(target)
    return {'alreadyApplied':False,'addedObjects':[o.name for o in clones]+[base.name],
            'archivedObjects':[], 'changedObjects':[carpet.name],
            'interiorCollection':COLLECTION,'replacesInteriorCollection':SOURCE_COLLECTION,
            'archivePolicy':'Retain original collection for campus and source archive; use replacement collection only for LRB independent interior export. Existing external roof must still be added once.',
            'interiorView':{'position':[83.5,5.3,2.1],'target':[75.59,13.26,3.2]},
            'sourcePlanUrl':'https://www.lse.ac.uk/asset-library/information/library-floor-plans-pdf.pdf',
            'sourcePhotoUrl':'https://tyrensakt.com/wp-content/uploads/2020/09/1328-LSE-Library-04.jpg'}
