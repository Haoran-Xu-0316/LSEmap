"""Photo-supported Houghton utility covers and CBG-side tree planters.

Apply to an already loaded scene. User reference09 shows rectangular iron covers
and dark raised tree boxes. Locations/dimensions/species are visual estimates on
the retained native/GIS street, not a surveyed inventory. Existing brick paving,
OLD steps/ramp/rails, the mapped165 bollard and all other buildings are retained.
"""
from pathlib import Path
import hashlib,math
import bpy,bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
SOURCE='SITE_V48_Houghton_Street'
NAMES=['SITE167_Houghton_paving_with_cover_openings','SITE167_Houghton_utility_covers_and_planters','SITE167_Houghton_tree_stems','SITE167_Houghton_tree_crowns']
PHOTO='data/collections/public-realm-2026/user-references/reference-09.png'
# GIS CBG west street edge, inherited native footprint. Outward points into street.
EDGE_START=Vector((4.401200019602698,-90.15244011123383,0))
EDGE_END=Vector((27.28164976633888,-46.04965774878046,0))
COVERS=[dict(center=(.9,-93.1),width=.55,length=.82),dict(center=(1.7,-88.1),width=.45,length=.62)]

class StreetBatch:
    """A small number of construction/material families, no per-leaf objects."""
    def __init__(self,name,materials,collection):self.name=name;self.materials=materials;self.collection=collection;self.vertices=[];self.faces=[];self.slots=[]
    def add(self,vertices,faces,slot=0):
        offset=len(self.vertices);self.vertices.extend(vertices);self.faces.extend(tuple(offset+i for i in f)for f in faces);self.slots.extend([slot]*len(faces))
    def box(self,center,size,u,n,slot=0):
        c=Vector(center);vertices=[c+u*(a*size[0]/2)+n*(b*size[1]/2)+Vector((0,0,z*size[2]/2))for a,b,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
        self.add(vertices,[tuple(reversed(f))for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]],slot)
    def cylinder(self,center,radius,z0,z1,slot=0,sides=12):
        x,y=center;vertices=[(x+radius*math.cos(i*math.tau/sides),y+radius*math.sin(i*math.tau/sides),z)for z in [z0,z1]for i in range(sides)]
        self.add(vertices,[tuple(reversed(range(sides))),tuple(range(sides,2*sides))]+[(i,(i+1)%sides,(i+1)%sides+sides,i+sides)for i in range(sides)],slot)
    def finish(self):
        mesh=bpy.data.meshes.new(self.name);mesh.from_pydata(self.vertices,[],self.faces);mesh.update()
        for mat in self.materials:mesh.materials.append(mat)
        uv=mesh.uv_layers.new(name='MetricUV')
        for p,slot in zip(mesh.polygons,self.slots):
            p.material_index=slot
            for i in p.loop_indices:
                v=mesh.vertices[mesh.loops[i].vertex_index].co;uv.data[i].uv=(v.x,v.y)
        obj=bpy.data.objects.new(self.name,mesh);self.collection.objects.link(obj);return obj

def apply_streets167():
    if all(bpy.data.objects.get(n)for n in NAMES):return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    assert not any(bpy.data.objects.get(n)for n in NAMES)
    collection=bpy.data.collections['00_SITE'];assert collection.name in {c.name for c in bpy.data.scenes['00_CAMPUS_COMPLETE'].collection.children}
    u=(EDGE_END-EDGE_START).normalized();n=Vector((-u.y,u.x,0));planters=[EDGE_START+u*d+n*1.85 for d in [14.5,26.0]]
    # Verify the estimated placements lie on the actual native paving with no
    # existing raised furniture, building wall or tree at their ground center.
    scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];deps=bpy.context.evaluated_depsgraph_get();ground=[]
    for label,p in [(f'cover{i}',Vector((*r['center'],0)))for i,r in enumerate(COVERS)]+[(f'planter{i}',p)for i,p in enumerate(planters)]:
        hit=scene.ray_cast(deps,p+Vector((0,0,1.6)),Vector((0,0,-1)),distance=2)
        assert hit[0]and hit[4].name==SOURCE,(label,hit[4].name if hit[0]else None)
        ground.append(dict(kind=label,point=list(p),groundObject=hit[4].name,height=hit[1].z))
    source=bpy.data.objects[SOURCE];owned=source.copy();owned.data=source.data.copy();owned.name=NAMES[0];owned.data.name=owned.name;collection.objects.link(owned)
    bm=bmesh.new();bm.from_mesh(owned.data);cut_faces=0
    for rec in COVERS:
        center=Vector((*rec['center'],0));half_u=rec['length']/2;half_n=rec['width']/2
        def local(v):
            p=owned.matrix_world@v.co-center;return p.dot(u),p.dot(n)
        for axis,half in [(u,half_u),(n,half_n)]:
            for sign in [-1,1]:
                faces=[]
                for f in bm.faces:
                    projected=[local(v)for v in f.verts]
                    if (min(p[0]for p in projected)<half_u+.40 and max(p[0]for p in projected)>-half_u-.40
                            and min(p[1]for p in projected)<half_n+.40 and max(p[1]for p in projected)>-half_n-.40):faces.append(f)
                geom=set(faces)|{e for f in faces for e in f.edges}|{v for f in faces for v in f.verts}
                bmesh.ops.bisect_plane(bm,geom=list(geom),plane_co=owned.matrix_world.inverted()@(center+axis*half*sign),plane_no=owned.matrix_world.to_3x3().transposed()@axis,dist=1e-6)
        remove=[]
        for face in bm.faces:
            point=owned.matrix_world@face.calc_center_median()-center
            if abs(point.dot(u))<half_u-1e-6 and abs(point.dot(n))<half_n-1e-6:remove.append(face)
        assert remove;cut_faces+=len(remove);bmesh.ops.delete(bm,geom=remove,context='FACES_ONLY')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(owned.data);bm.free();owned.data.update();source.hide_render=True;source.hide_set(True)
    black=bpy.data.materials['SITE165_Houghton_black_cast_iron'].copy();black.name='SITE167_Houghton_charcoal_tree_boxes';black.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=.05;black.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.72
    iron=bpy.data.materials['SITE_V47_iron'];soil=bpy.data.materials['SITE_V47_soil'];bark=bpy.data.objects['03_PUBLIC_REALM_Plane_tree_trunk'].data.materials[0];leaf=bpy.data.objects['03_PUBLIC_REALM_Plane_tree_crown'].data.materials[0]
    fixtures=StreetBatch(NAMES[1],[iron,black,soil],collection);stems=StreetBatch(NAMES[2],[bark],collection);crowns=StreetBatch(NAMES[3],[leaf],collection)
    for rec in COVERS:
        c=Vector((*rec['center'],0));w,h=rec['length'],rec['width'];t=.018
        for side in [-1,1]:
            fixtures.box(c+n*side*(h/2-t/2)+Vector((0,0,.045)),(w,t,.01),u,n)
            fixtures.box(c+u*side*(w/2-t/2)+Vector((0,0,.045)),(t,h-2*t,.01),u,n)
        fixtures.box(c+Vector((0,0,.040)),(w-2*t-.004,h-2*t-.004,.012),u,n)
        # Closed cast lid with shallow raised grid; it is a utility cover, not an
        # invented open storm drain. Grid/handle geometry is an estimated pattern.
        for i in range(5):fixtures.box(c+u*((i-2)*(w-2*t)/6)+Vector((0,0,.0475)),(.007,h-2*t-.012,.003),u,n)
        for i in range(4):fixtures.box(c+n*((i-1.5)*(h-2*t)/5)+Vector((0,0,.0475)),(w-2*t-.012,.007,.003),u,n)
    for j,c in enumerate(planters):
        width=1.25;wall=.045;bottom=.05;top=.70
        for side in [-1,1]:
            fixtures.box(c+n*side*(width/2-wall/2)+Vector((0,0,(top+bottom)/2)),(width,wall,top-bottom),u,n,1)
            fixtures.box(c+u*side*(width/2-wall/2)+Vector((0,0,(top+bottom)/2)),(wall,width-2*wall,top-bottom),u,n,1)
        fixtures.box(c+Vector((0,0,.64)),(width-2*wall,width-2*wall,.06),u,n,2)
        stems.cylinder((c.x,c.y),.055,.65,3.3)
        for k in range(3):
            center=c+u*((k-1)*.25)+Vector((0,0,3.15+k*.32));verts=[];rings=7;segs=16
            for r in range(rings+1):
                theta=(r+.03)/(rings+.06)*math.pi
                for i in range(segs):
                    phi=i*math.tau/segs;variation=1+.10*math.sin(i*1.8+r*2.1+j)
                    verts.append(center+u*(math.sin(theta)*math.cos(phi)*.88*variation)+n*(math.sin(theta)*math.sin(phi)*.77*variation)+Vector((0,0,math.cos(theta)*1.08)))
            crowns.add(verts,[tuple(range(segs)),tuple(reversed(range(rings*segs,(rings+1)*segs)))]+[(r*segs+i,(r+1)*segs+i,(r+1)*segs+(i+1)%segs,r*segs+(i+1)%segs)for r in range(rings)for i in range(segs)])
    objects=[fixtures.finish(),stems.finish(),crowns.finish()]
    for o in objects:o['scope']='User photograph-supported Houghton details; sizes/locations/tree forms estimated, not surveyed.'
    for p in bpy.data.objects[NAMES[3]].data.polygons:p.use_smooth=True
    for layer in bpy.context.scene.view_layers:layer.update()
    return dict(alreadyApplied=False,addedObjects=NAMES,archivedObjects=[SOURCE],changedObjects=[],coverCutFaces=cut_faces,coverRecords=COVERS,planterCenters=[list(c)for c in planters],groundProbes=ground,
                sourcePhoto=PHOTO,sourcePhotoSha256=hashlib.sha256((ROOT/PHOTO).read_bytes()).hexdigest(),sourceURL='User supplied photograph024f64c4-e62b-4734-b7ba-6097bc690bb5',photographDate='unknown',
                dimensions=dict(planterWidth=1.25,planterHeight=.65,coverTop=.05,treeMaximumHeight=4.87),
                limitations=['Two utility cover patterns and placements estimated from the photo, not utility inventory or a drain plan.',
                             'Two CBG-side raised tree boxes and young-tree forms estimated from photographed grouping; positions derive retained native GIS west edge, not survey.',
                             'Existing OLD access geometry, stone/brick paving outside cover openings, mapped bollard, buildings and rooms preserved.'])
