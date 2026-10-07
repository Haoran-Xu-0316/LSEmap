"""Repair the MAR north podium's open upper loggia and overlapping wall tiles.

Nick Kane's built north photograph02 supports an open left loggia rather than
an extra punched window. Registration and0.2m sill/slab are photographic
estimates; the model retains its existing GIS axes and overall height. Capture
date is unknown; the published built photograph is not a2026site survey.
Call apply_mar_exterior174() on an already loaded campus. No file operations.
"""
import math
import bpy,bmesh
from mathutils import Vector

COLLECTION='MAR_EXTERIOR174_north_open_loggia'
ARCHIVE='MAR_EXTERIOR174_retained_sources'
WALL='MAR_MAR_north_podium_pierced_wall'
HELPERS=[
 'MAR_D5_podium104_joinery',
 *[f'MAR_NEXT_LETTER165_retained_{i:02d}_{suffix}'for i,suffix in [(2,'sills'),(3,'joint'),(4,'channel'),(5,'fascia'),(6,'slot'),(7,'bead'),(8,'return'),(9,'seal'),(10,'downstand'),(11,'flashing'),(12,'joint')]],
 'MAR_EXTERIOR168_retained_glass_and_north_hall_pane',
]
SOURCES=[WALL]+HELPERS
NAMES=['MAR174_north_podium_nonoverlapping_walls']+[f'MAR174_retained_loggia_{i:02d}'for i in range(len(HELPERS))]
ORIGIN=Vector((-8.696325894899289,49.33154396120258,0))
U=Vector((math.cos(math.radians(22)),math.sin(math.radians(22)),0));N=Vector((-U.y,U.x,0))
PHOTOS=['data/collections/architecture_round5/images/MAR/MAR_mar_kane_02.jpg','data/collections/architecture_round5/images/MAR/MAR_mar_kane_04.jpg']
SOURCE_URLS=['https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/','https://www.archdaily.com/977225/london-school-of-economics-marshall-building-grafton-architects']

def local(p):return Vector(((p-ORIGIN).dot(U),(p-ORIGIN).dot(N),p.z))
def world(x,y,z):return ORIGIN+U*x+N*y+Vector((0,0,z))

def window_vertices(obj):
    """Only entire connected components of the false front punched window."""
    parent=list(range(len(obj.data.vertices)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for f in obj.data.polygons:
        for i in f.vertices[1:]:parent[root(i)]=root(f.vertices[0])
    groups={}
    for i in range(len(parent)):groups.setdefault(root(i),[]).append(i)
    removed=[]
    for ids in groups.values():
        ps=[local(obj.matrix_world@obj.data.vertices[i].co)for i in ids]
        if all(4.7<p.x<8.6 and 20.0<p.y<21.1 and 5.6<p.z<12.6 for p in ps):removed.extend(ids)
    return removed

def podium_mesh(name,material):
    # A non-overlapping occupancy grid provides two retained flank windows and
    # an open estimated loggia atX0.8to9.0. Boundaries have true0.55m returns.
    xs=[-30,-27.5,-24.3,-15,.8,9,18,21,24]
    zs=[4.6,4.8,6,12.2,12.8]
    def filled(x,z):
        if -30<x<-15:return not(-27.5<x<-24.3 and 6<z<12.2)
        if .8<x<24:
            if x<9:return z<4.8 or z>12.2
            return not(18<x<21 and 6<z<12.2)
        return False
    cells={(i,j)for i in range(len(xs)-1)for j in range(len(zs)-1)if filled((xs[i]+xs[i+1])/2,(zs[j]+zs[j+1])/2)}
    verts=[];faces=[]
    def face(points):
        start=len(verts);verts.extend(world(*p)for p in points);faces.append(tuple(range(start,start+len(points))))
    a,b=20.25,20.8
    for i,j in sorted(cells):
        x0,x1=xs[i:i+2];z0,z1=zs[j:j+2]
        face([(x1,b,z0),(x0,b,z0),(x0,b,z1),(x1,b,z1)])
        face([(x0,a,z0),(x1,a,z0),(x1,a,z1),(x0,a,z1)])
        if(i-1,j)not in cells:face([(x0,a,z0),(x0,a,z1),(x0,b,z1),(x0,b,z0)])
        if(i+1,j)not in cells:face([(x1,b,z0),(x1,b,z1),(x1,a,z1),(x1,a,z0)])
        if(i,j-1)not in cells:face([(x0,a,z0),(x0,b,z0),(x1,b,z0),(x1,a,z0)])
        if(i,j+1)not in cells:face([(x0,b,z1),(x0,a,z1),(x1,a,z1),(x1,b,z1)])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(material)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
    uv=mesh.uv_layers.new(name='MAR174_metric_projection')
    for f in mesh.polygons:
        for i in f.loop_indices:
            p=local(mesh.vertices[mesh.loops[i].vertex_index].co);uv.data[i].uv=(p.x,p.z)
    return mesh

def apply_mar_exterior174():
    if all(bpy.data.objects.get(name)for name in NAMES):return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    assert not any(bpy.data.objects.get(name)for name in NAMES),'Partial MAR174 component'
    for name in SOURCES:assert bpy.data.objects[name].type=='MESH'and not bpy.data.objects[name].hide_render,name
    parent=bpy.data.collections['MAR_EXTERIOR'];collection=bpy.data.collections.new(COLLECTION);parent.children.link(collection)
    archive=bpy.data.collections.new(ARCHIVE);parent.children.link(archive);archive.hide_render=True
    material=bpy.data.objects[WALL].data.materials[0].copy();material.name='MAR174_retained_warm_concrete'
    mesh=podium_mesh(NAMES[0],material);obj=bpy.data.objects.new(NAMES[0],mesh);collection.objects.link(obj)
    removed={};source=bpy.data.objects[WALL];archive.objects.link(source);source.hide_render=True;source.hide_set(True)
    for source_name,name in zip(HELPERS,NAMES[1:]):
        source=bpy.data.objects[source_name];ids=window_vertices(source);assert ids,source_name
        replacement=source.copy();replacement.data=source.data.copy();replacement.name=name;replacement.data.name=name;collection.objects.link(replacement)
        bm=bmesh.new();bm.from_mesh(replacement.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i]for i in ids],context='VERTS');bm.to_mesh(replacement.data);bm.free();replacement.data.update()
        removed[source_name]=dict(removedVertexIndices=ids,removedVertexCount=len(ids))
        archive.objects.link(source);source.hide_render=True;source.hide_set(True)
    for name in NAMES:bpy.data.objects[name]['componentKey']=name
    for layer in bpy.context.scene.view_layers:layer.update()
    return dict(alreadyApplied=False,addedObjects=NAMES,archivedObjects=SOURCES,changedObjects=[],removedFalseWindowComponents=removed,
        changes=['Reconstruct whole north podium wall without duplicate overlapping front/back tile faces.','Replace false upper podium punched window with open left loggia and preserve native flank windows.'],
        loggiaEstimatedLocalBounds=[[.8,9],[20.25,20.8],[4.8,12.2]],photographs=PHOTOS,sourceURLs=SOURCE_URLS,
        photographDate='Built2022publication; actual photograph capture date unknown. User MAR sign photo capture date unknown.',
        limitations=['Loggia boundary9m and slab top4.8m estimated from built north photo02, not measured.','Inherited total massing, terrace and highest-wing ambiguous back faces retained; no2026survey claim.','Existing165left ground blank bay/name and all interior geometry preserved.','Original wall/UV/materials/world matrices archived intact; new wall has new metric UV.','Remaining windows and finishes retain their original UVs and material bindings.'])
