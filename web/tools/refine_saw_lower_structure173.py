"""Re-register SAW's whole public stair study against its2014 floor diagrams.

The previous continuous helix and its171/172 extensions used the Venue/faith
centre side of the plan. This replacement places changing folded flights on the
back/main circulation side above the lift zone, fills the old repeated void,
and cuts one coherent estimated main-stair opening. Archive all replaced source
objects intact. This is historical topology with estimated dimensions, not a
surveyed2026 reconstruction or a complete room/escape-core model.
"""
from pathlib import Path
import math,hashlib
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
PARENT='SAW_PUBLIC_INTERIOR_study'
COLLECTION='SAW_STRUCTURE173_registered_main_circulation'
ARCHIVE='SAW_STRUCTURE173_retained_source_archive'
GUIDE='data/documents/saw_occupants_guide_2014.pdf'
SOURCE_URL='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/SAW/Final-Web-version-of-Occupants-Guide.pdf'
# Three identifiable outer-plan corners. Registration is affine/estimated:
# rear-left, rear-right and front-right; same G-floor outer boundary is retained.
PLAN_ANCHORS=[(145.,400.),(1345.,400.),(1345.,1185.)]
WORLD_ANCHORS=[(-65.223399,-15.905616),(-84.252182,28.425),( -55.301,36.609104)]
LEVELS=[0.,3.45,8.1,11.1,14.1,18.,21.9]
OLD_STAIR_NAMES=['SAW_spiral_stair_treads','SAW_spiral_anti_slip_nosings','SAW_spiral_concrete_guards','SAW_V19_MOD_spiral_wall_handrails','SAW_V19_MOD_spiral_handrail_brackets',
 'SAW171_fifth_to_sixth_curved_treads','SAW171_upper_stair_landings','SAW171_upper_stair_guards','SAW172_fourth_to_fifth_curved_treads','SAW172_fourth_floor_landing','SAW172_fourth_fifth_guards']
OLD_FLOORS=['SAW_SAW_floor_'+str(z)for z in LEVELS[1:]]
# Picked relative positions from pages32->26. Centre lines and exact bends are
# estimated within the readable main stair/circulation zone, not traced risers.
PATHS=[[(590,590),(640,535),(730,480)],[(730,480),(760,535),(670,605)],[(670,605),(800,595),(775,470)],[(775,470),(665,445),(595,555)],[(595,555),(695,590),(805,510)],[(805,510),(850,585),(670,570)]]
STEP_COUNTS=[23,31,20,20,26,26]
CORE_PLAN=[(500,420),(890,420),(930,610),(580,650)]
WIDTH=1.40;SLAB_THICKNESS=.18
NAMES=['SAW173_registered_main_treads','SAW173_shared_floor_landings','SAW173_main_stair_rails','SAW173_flat_anti_slip_nosings']
FLOOR_NAMES=['SAW173_registered_floor_'+str(z)for z in LEVELS[1:]]


def plan_world(point):
    x,y=point;a,b,c=map(Vector,WORLD_ANCHORS)
    return a+(b-a)*((x-145)/1200)+(c-b)*((y-400)/785)


def area(poly):return sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(poly,poly[1:]+poly[:1]))/2


def ccw(poly):
    q=[tuple(p)for p in poly]
    return q if area(q)>0 else list(reversed(q))


def clip(poly,a,b,inside):
    def signed(p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
    result=[]
    for p,q in zip(poly,poly[1:]+poly[:1]):
        dp,dq=signed(p),signed(q);ip=dp>=0 if inside else dp<=0;iq=dq>=0 if inside else dq<=0
        if ip:result.append(p)
        if ip!=iq:
            t=dp/(dp-dq);result.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
    # Suppress exact or near-exact duplicates created at an existing triangle edge.
    clean=[]
    for p in result:
        if not clean or math.dist(clean[-1],p)>1e-7:clean.append(p)
    if len(clean)>1 and math.dist(clean[0],clean[-1])<1e-7:clean.pop()
    return clean if len(clean)>=3 and abs(area(clean))>1e-10 else []


def subtract(poly,hole):
    remaining=ccw(poly);parts=[];hole=ccw(hole)
    for a,b in zip(hole,hole[1:]+hole[:1]):
        if not remaining:break
        outside=clip(remaining,a,b,False)
        if outside:parts.append(ccw(outside))
        remaining=clip(remaining,a,b,True)
    return parts


def smooth_route(points,landing_start=False):
    p=[plan_world(x)for x in points];a,k,b=p
    if landing_start:a=a+(k-a).normalized()*1.2
    b=b-(b-k).normalized()*1.2
    u=(k-a).normalized();v=(b-k).normalized();cut=min(2.,(k-a).length*.85,(b-k).length*.85);before=k-u*cut;after=k+v*cut
    # Circular fillet preserves enough inner radius for the tread width;
    # a quadratic bend can fold the inside edge and leave a strip outside it.
    turn=math.atan2(u.x*v.y-u.y*v.x,u.dot(v))
    radius=cut/math.tan(abs(turn)/2)
    assert radius>WIDTH/2+.08,'Rounded flight is too tight for its width'
    normal=Vector((-u.y,u.x))*(1 if turn>0 else-1)
    center=before+normal*radius;radial=before-center
    samples=[a,before]
    for i in range(1,33):
        angle=turn*i/32;c,s=math.cos(angle),math.sin(angle)
        samples.append(center+Vector((radial.x*c-radial.y*s,radial.x*s+radial.y*c)))
    samples.append(b);lengths=[0.]
    for x,y in zip(samples,samples[1:]):lengths.append(lengths[-1]+(y-x).length)
    def sample(distance):
        d=min(max(distance,0.),lengths[-1])
        for i in range(len(lengths)-1):
            if d<=lengths[i+1]+1e-9:
                t=(d-lengths[i])/(lengths[i+1]-lengths[i]);return samples[i].lerp(samples[i+1],t)
        return samples[-1]
    def section(distance):
        pos=sample(distance);tangent=(sample(distance+.04)-sample(distance-.04)).normalized();normal=Vector((-tangent.y,tangent.x))
        return pos-normal*WIDTH/2,pos+normal*WIDTH/2,pos,tangent
    return lengths[-1],sample,section


def apply_saw_lower_structure173():
    """Replace the whole active stair/floor relation while retaining originals."""
    if COLLECTION in bpy.data.collections:
        assert all(n in bpy.data.objects for n in NAMES+FLOOR_NAMES)
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    parent=bpy.data.collections[PARENT];collection=bpy.data.collections.new(COLLECTION);parent.children.link(collection)
    archive=bpy.data.collections.new(ARCHIVE);parent.children.link(archive);archive.hide_render=True
    sources=[bpy.data.objects[n]for n in OLD_FLOORS+OLD_STAIR_NAMES]
    ground=bpy.data.objects['SAW_SAW_floor_0'];core=ccw([plan_world(p)for p in CORE_PLAN]);ground_triangles=[ccw([(ground.matrix_world@ground.data.vertices[i].co).xy for i in p.vertices])for p in ground.data.polygons]
    ground_tree=BVHTree.FromPolygons([ground.matrix_world@v.co for v in ground.data.vertices],[tuple(p.vertices)for p in ground.data.polygons])
    for p in core:
        assert ground_tree.ray_cast(Vector((p[0],p[1],.1)),Vector((0,0,-1)),.2)[0]is not None,'Registered core outside retained building footprint'
    groups=[([],[]),([],[]),([],[]),([],[])]
    def solid(group,poly,bottom,top):
        poly=ccw(poly);verts,faces=groups[group];start=len(verts);n=len(poly)
        verts.extend((x,y,z)for z in(bottom,top)for x,y in poly)
        faces.extend([tuple(start+i for i in reversed(range(n))),tuple(start+n+i for i in range(n))])
        faces.extend((start+i,start+(i+1)%n,start+n+(i+1)%n,start+n+i)for i in range(n))
    def tube(group,a,b,radius=.023):
        a,b=Vector(a),Vector(b);direction=(b-a).normalized();axis=direction.cross(Vector((0,0,1)))
        if axis.length<.01:axis=direction.cross(Vector((0,1,0)))
        axis.normalize();second=direction.cross(axis);verts,faces=groups[group];off=len(verts)
        for p in (a,b):
            for i in range(8):verts.append(tuple(p+radius*(math.cos(i*math.tau/8)*axis+math.sin(i*math.tau/8)*second)))
        faces.extend([tuple(off+i for i in reversed(range(8))),tuple(off+8+i for i in range(8))])
        faces.extend((off+i,off+(i+1)%8,off+8+(i+1)%8,off+8+i)for i in range(8))
    tread_records=[];flight_records=[];rail_records=[]
    for flight,(path,count,z0,z1)in enumerate(zip(PATHS,STEP_COUNTS,LEVELS,LEVELS[1:])):
        length,sample,section=smooth_route(path,landing_start=flight>0)
        for i in range(count):
            d0,d1=length*i/count,length*(i+1)/count;left0,right0,p0,t0=section(d0);left1,right1,p1,t1=section(d1);z=z0+(z1-z0)*(i+1)/count
            poly=ccw([left0,right0,right1,left1]);riser=(z1-z0)/count
            # Full riser blocks avoid the prior floating0.10m slabs. The2mm
            # assembly seam prevents coincident neighbouring tread faces.
            solid(0,poly,z-riser+.002,z)
            # The strip is an independent inset finish, never overlaid on the riser.
            pc=sum((Vector(p)for p in poly),Vector((0,0)))/len(poly)
            # Interpolate from this tread's own front edge into its interior.
            # End insets leave the narrow winder corners free of extra finish.
            edge_a=left1.lerp(right1,.14);edge_b=right1.lerp(left1,.14)
            strip=ccw([edge_a.lerp(pc,.10),edge_b.lerp(pc,.10),edge_b.lerp(pc,.24),edge_a.lerp(pc,.24)])
            # The first-to-second final tread meets the shared landing and
            # next riser: omit its independent finish to avoid a crossing face.
            if not (flight==1 and i==count-1):
                solid(3,strip,z+.001,z+.003)
            tread_records.append(dict(flight=flight,index=i,top=z,bottom=z-riser+.002,footprint=poly))
            # Omit the short landing transition; no rail obstructs the shared route.
            if d0>1. and d1<length-1.:
                for side in (-1,1):
                    normal0=Vector((-t0.y,t0.x));normal1=Vector((-t1.y,t1.x));aa=p0+normal0*side*(WIDTH/2+.07);bb=p1+normal1*side*(WIDTH/2+.07)
                    rail_records.append(dict(flight=flight,step=i,side=side,kind='rail',faceStart=len(groups[2][1])))
                    tube(2,(aa.x,aa.y,z+1.00),(bb.x,bb.y,z+1.00+(z1-z0)/count))
                    if i%3==0:
                        rail_records.append(dict(flight=flight,step=i,side=side,kind='post',faceStart=len(groups[2][1])))
                        tube(2,(aa.x,aa.y,z+.008),(aa.x,aa.y,z+.985),.018)
        flight_records.append(dict(fromLevel=flight,toLevel=flight+1,fromDatum=z0,toDatum=z1,estimatedTreads=count,planPath=path,estimatedPathLength=length,pattern='folded straight runs with rounded/winder turn'))
    landing_records=[]
    for level,(z,endpoint)in enumerate(zip(LEVELS[1:],[p[-1]for p in PATHS]),1):
        x,y=endpoint
        # Back-side floor connection crosses the new aperture boundary with a3mm
        # seam. Cutting near-level treads out prevents double top faces/solid overlap.
        platform=ccw([plan_world(q)for q in [(x-40,420+.08),(x+40,420+.08),(x+40,y+40),(x-40,y+40)]])
        core_center=sum((Vector(p)for p in core),Vector((0,0)))/len(core)
        inset_core=[tuple(core_center+(Vector(p)-core_center)*.9998)for p in core]
        for a,b in zip(inset_core,inset_core[1:]+inset_core[:1]):
            platform=clip(platform,a,b,True)
            assert platform
        parts=[platform]
        for tread in tread_records:
            # Keep the incoming stair volume open for headroom, rather than
            # covering it with a landing plate just because it is below datum.
            if tread['top']>z-2.25 and tread['bottom']<z+.00001:
                center=sum((Vector(p)for p in tread['footprint']),Vector((0,0)))/len(tread['footprint'])
                expanded=[tuple(center+(Vector(p)-center)*1.17)for p in tread['footprint']]
                parts=[piece for part in parts for piece in subtract(part,expanded)]
        for part in parts:solid(1,part,z-SLAB_THICKNESS,z)
        landing_records.append(dict(level=level,datum=z,planEndpoint=endpoint,parts=len(parts),floorSeamEstimate=.003))
    materials=[]
    for name,color in [('SAW173_public_concrete',(.58,.58,.54,1)),('SAW173_dark_metal',(.055,.06,.057,1))]:
        m=bpy.data.materials.new(name);m.diffuse_color=color;m.use_nodes=True;s=m.node_tree.nodes.get('Principled BSDF');s.inputs['Base Color'].default_value=color;s.inputs['Roughness'].default_value=.66;materials.append(m)
    def mesh_object(name,verts,faces,material):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
        uv=mesh.uv_layers.new(name='MetricUV')
        for loop in mesh.loops:
            v=mesh.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(v.x,v.y)
        mesh.materials.append(material);o=bpy.data.objects.new(name,mesh);collection.objects.link(o);o['componentKey']=name;o['evidenceYear']=2014;o['sourceURL']=SOURCE_URL;o['dimensions']='Estimated plan registration/topology, not surveyed';return o
    for i,(name,(verts,faces))in enumerate(zip(NAMES,groups)):mesh_object(name,verts,faces,materials[0 if i<2 else 1])
    floor_parts=[piece for triangle in ground_triangles for piece in subtract(triangle,core)]
    for z,source_name,name in zip(LEVELS[1:],OLD_FLOORS,FLOOR_NAMES):
        verts=[];faces=[]
        for poly in floor_parts:
            off=len(verts);verts.extend((x,y,z)for x,y in poly);faces.extend((off,off+i,off+i+1)for i in range(1,len(poly)-1))
        source=bpy.data.objects[source_name];o=mesh_object(name,verts,faces,source.data.materials[0]);o['retainedSource']=source_name;o['surfaceStudy']='Retained slab datum/boundary; original source UV and geometry kept intact in archive'
        for p in o.data.polygons:
            if p.normal.z<0:p.flip()
    for o in sources:
        archive.objects.link(o);o.hide_render=True;o.hide_set(True)
    collection['registration']='2014 plan rear-left/rear-right/front-right to retained outer footprint, affine estimate'
    return dict(alreadyApplied=False,addedObjects=NAMES+FLOOR_NAMES,archivedObjects=OLD_FLOORS+OLD_STAIR_NAMES,changedObjects=[],
        productionCollection=COLLECTION,scope='G to sixth main stair: six changing folded flights, six landings, six re-registered floor apertures; Venue-side repeated helix retired.',
        source=dict(file=GUIDE,sha256=hashlib.sha256((ROOT/GUIDE).read_bytes()).hexdigest(),sourceURL=SOURCE_URL,pages=[26,27,28,29,30,31,32],publicationYear=2014),
        registration=dict(planAnchors=PLAN_ANCHORS,worldAnchors=WORLD_ANCHORS,corePlan=CORE_PLAN,coreWorld=core),flights=flight_records,landings=landing_records,railRecords=rail_records,
        limitations=['Readable2014 main stair/lift-zone relationships inform this historical study. Flight centerlines, winder shapes, counts, guards and heights are estimated, not exact floor-plan traces.',
                    'The inherited common exterior footprint and upper-floor setbacks remain approximate; full room layouts, side escape stairs/lifts and basement-to-Venue connection are not reconstructed.',
                    'No current2026 condition/safety certification. Archived source geometry/UV/materials retained; active replacement floor UV is newly metric, not a copy of source texture mapping.'])
